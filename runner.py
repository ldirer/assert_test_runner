#!/home/laurent/miniconda3/envs/genetic/bin/python


# Grammar here: https://docs.python.org/3/library/ast.html
# A-mazing practical docs: http://greentreesnakes.readthedocs.io/en/latest/index.html

# Could use https://github.com/berkerpeksag/astor for debugging (ast -> string of code)

# LAter: 
# why not a with `any variable=test value` monkeypatching syntax?
# Separate print from the runner and from the original program.
# We might need isolated locals instead of mixing up all the variables.


import sys
import os
from typing import List
import ast


DEBUG = True
def run(code: str):
    # Exec fails with 'add is undefined' NameError if there's a __main__ in the code... WEIRD. 
    # That's because (docs):
    # > If exec gets two separate objects as globals and locals, the code will be executed as if it were embedded in a class definition.
    context = {}
    ast
    exec(code, context, context)


def main(files: List):
    """files: list of filenames relative to current directory."""
    for fname in files:
        run(read_file(fname))


def read_file(fname: str) -> str:
    with open(fname, 'r') as f:
        return f.read()


def is_test_function(f: ast.FunctionDef) -> bool:
    return f.name.startswith('test')

# Find all functions. 
# Add a function call after its definition if it starts with 'test_'
# Run the file.
src = read_file('tests_assert.py')
module = ast.parse(src)
functions = [(i, statement) for i, statement in enumerate(module.body) if isinstance(statement, ast.FunctionDef)]


test_functions = [(i, function_def) for i, function_def in functions if is_test_function(function_def)]



class MyNodeTransformer(ast.NodeTransformer):
    """Will recursively visit nodes and transform them based on visit_{node_type} methods."""

    def visit(self, node):
        if DEBUG:
            print(f'Visiting node {node}')
        return super().visit(node)

    def visit_Expr(self, node):
        if DEBUG:
            print(f'{node.lineno} - {node}')
        return node


class TransformTestFunctionNodeTransformer(MyNodeTransformer):

    def visit_FunctionDef(self, node):
        return node


#class AddTestCallNodeTransformer(MyNodeTransformer):
#    def visit_FunctionDef

# transformed_tree = MyNodeTransformer().visit(module)


# 1. We want to call each test function.

# 2. When we run the file we want it to run all the tests even if one fails.

# 3. We want nice error messages with plain `assert`.



def get_log_to_errors_node(value_to_log: ast.Expr) -> ast.Expr:
    """First approach: append the error to a global list that we can manipulate afterwards.
    Caveat: There's almost nothing to work with on an AssertionError!


    In [147]: try:
     ...:     assert 1 == 0
     ...: except AssertionError as e:
     ...:     for k in dir(e):
     ...:         print(f'{k} --> {getattr(e, k)}')
     ...:


    
    -> We can still find relevant info in e.__traceback__.tb_frame.f_locals.
    
    """
    log_to_errors_node = ast.parse('_global_errors.append(1)')
    call = log_to_errors_node.body[0]
    call.value.args = [value_to_log]
    # We have a module, we want to return the single top-level expr it contains
    return log_to_errors_node.body[0]

def on_fail_message(test_name):
    return f'The test {test_name} failed.'


_global_errors = {}

def _log_runner_error(test_function_id, value_to_log_id: str) -> ast.Expr:
    # Instead of building the ast manually we parse the line we want.
    # Then we need to 'flatten' it since we want a single Expr and not a Module.
    return ast.parse(f'_global_errors[{test_function_id}] = {value_to_log_id}').body[0]
    


import typing

def get_print_node(value_to_print: typing.Union[ast.Expr, str]) -> ast.Expr:
    if isinstance(value_to_print, str):
        value_to_print = ast.Str(s=value_to_print)
    return ast.Expr(ast.Call(ast.Name(id='print', ctx=ast.Load()), [value_to_print], []))


def on_success_message(test_name) -> str:
    return f'The test {test_name} passed!'
    

for n_already_inserted, (i, f) in enumerate(test_functions):

    name = ast.Name(id=f.name, ctx=ast.Load())
    # No args passed to the test functions for the moment
    call = ast.Call(name, [], [])
    # Call node needs to be wrapped. In Expr since we dont use the value.
    call_expr = ast.Expr(call)

    # Now we wrap in a try except so we can keep running even if the test fails
    except_handler = ast.ExceptHandler(type=ast.Name(id='AssertionError', ctx=ast.Load()), name='e', 
            body=[
                get_print_node(on_fail_message(f.name)), 
                _log_runner_error(f.name, 'e'),
                #get_log_to_errors_node(ast.Name(id='e', ctx=ast.Load()))
                ])

    wrapped = ast.Try(body=[call_expr], handlers=[except_handler], orelse=[get_print_node(on_success_message(f.name))], finalbody=[])


    module.body.insert(i + 1 + n_already_inserted, wrapped)
#
## Our module has nodes without lineno and column offset. Tis bad. Breaks compiling.
ast.fix_missing_locations(module)





examples = {
        'try_except': """
try:
    a + 1
except NameError as e:
    print(e.args)
else:
    print('in else')
        """.strip(' ')
        }

#m = ast.parse(examples['try_except'])
# ast.dump(m)


import traceback
def print_failures(errors):
    print('-' * 50)
    print(f'{" Details ":-^50}')
    print('-' * 50)
    for f, error in errors.items():
        print(f'Test {f.__name__} failed!')
        # first argument is exception type, now inferred from second arg and ignored. weird signature seems to be legacy.
        traceback.print_exception(None, error, error.__traceback__)
        stack_summary = traceback.StackSummary.extract(traceback.walk_tb(error.__traceback__), capture_locals=True)
        # f-string inception?
        print(f'With: {" ".join([f"{k}={v}" for k, v in stack_summary[1].locals.items()])}')






if __name__ == '__main__':
    files = sys.argv[1:]
    main(files)
    # We pass '<ast>' as filename so it's clear where it came from.
    # Actually we will pass the file containing the tests: it's a trick to get traceback to work.
    # Otherwise we have line numbers from the original file but traceback tries to look up an '<ast>' file that does not exist 
    # Sidenote: The trace module even ignores file whose name starts with < and ends with >.
    compiled = compile(module, filename='tests_assert.py', mode='exec')
    exec(compiled)
    print_failures(_global_errors)



