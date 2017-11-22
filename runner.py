#!/home/laurent/miniconda3/envs/genetic/bin/python


# Grammar here: https://docs.python.org/3/library/ast.html
# A-mazing practical docs: http://greentreesnakes.readthedocs.io/en/latest/index.html


# 1. We want to call each test function (top-level function starting with 'test').

# 2. When we run the file we want it to run all the tests even if one fails.

# 3. We want nice error messages with plain `assert`.


import sys
import traceback
import typing
from typing import List
import ast


def run(mod: ast.Module, filename: str):
    # We pass '<ast>' as filename so it's clear where it came from.
    # Actually we will pass the file containing the tests: it's a trick to get traceback to work.
    # Otherwise we have line numbers from the original file but traceback tries to look up a non-existing '<ast>' file
    # Sidenote: The trace module even ignores file whose name starts with < and ends with >.
    compiled = compile(mod, filename=filename, mode='exec')
    errors = {}
    # This is a bit fragile: things will break if a _global_errors variable is defined by the other program.
    context = {'_global_errors': errors}
    exec(compiled, context, context)
    print_failures(errors)


def rewrite_as_test(fname) -> ast.Module:
    """Find all test functions.
    Add a function call wrapped in a try except AssertionError after the definition for each test.
    """
    src = read_file(fname)
    mod = ast.parse(src)
    functions = [(i, statement) for i, statement in enumerate(mod.body) if isinstance(statement, ast.FunctionDef)]

    test_functions = [(i, function_def) for i, function_def in functions if is_test_function(function_def)]
    print(f'Collected {len(test_functions)} tests...')

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
                                               get_log_error_node(f.name, 'e'),
                                           ])

        wrapped = ast.Try(body=[call_expr], handlers=[except_handler],
                          orelse=[get_print_node(on_success_message(f.name))], finalbody=[])

        mod.body.insert(i + 1 + n_already_inserted, wrapped)

    # Our module has nodes without lineno and column offset. Tis bad. Breaks compiling. We fill it sort-of-randomly.
    ast.fix_missing_locations(mod)
    return mod


def read_file(fname: str) -> str:
    with open(fname, 'r') as f:
        return f.read()


def is_test_function(f: ast.FunctionDef) -> bool:
    return f.name.startswith('test')


def get_log_error_node(test_function_id, value_to_log_id: str) -> ast.Expr:
    """Return an ast node that appends the exception to a global list that we will be able to manipulate afterwards.

    We can find relevant info on an AssertionError e in e.__traceback__.tb_frame.f_locals.
    """
    # Instead of building the ast manually we parse the line we want.
    # Then we need to 'flatten' it since we want a single Expr and not a Module.
    return ast.parse(f'_global_errors[{test_function_id}] = {value_to_log_id}').body[0]


def get_print_node(value_to_print: typing.Union[ast.Expr, str]) -> ast.Expr:
    """Return a node that will print a value when executed."""
    if isinstance(value_to_print, str):
        value_to_print = ast.Str(s=value_to_print)
    return ast.Expr(ast.Call(ast.Name(id='print', ctx=ast.Load()), [value_to_print], []))


def on_success_message(test_name) -> str:
    return f'The test {test_name} passed!'


def on_fail_message(test_name) -> str:
    return f'The test {test_name} failed.'


def print_indent_lines(arg: str, indent=0, **kwargs):
    lines = arg.split('\n')
    indented_lines = [' ' * indent + line for line in lines]
    print(*indented_lines, sep='\n', **kwargs)


def print_failures(errors: typing.Dict):
    """Print the failures (as listed in `errors`) that occurred in all the tests"""
    print('-' * 50)
    print(f'{"Failure details ":-^50}')
    for test_function, error in errors.items():
        print('-' * 50)
        print(f'Test {test_function.__name__} failed with the following stacktrace:')
        # first argument is exception type, now inferred from second arg and ignored. Signature seems to be legacy.
        exception_tb = '\n'.join(traceback.format_exception(None, error, error.__traceback__))
        print_indent_lines(exception_tb, indent=2)
        # We use the traceback module to walk the traceback stack and give us a list of frame summaries.
        stack_summary = traceback.StackSummary.extract(traceback.walk_tb(error.__traceback__), capture_locals=True)
        # The info we want is one frame higher
        debug_information = '\n'.join([f'{k}={v}' for k, v in stack_summary[1].locals.items()])
        print('Where: ')
        print_indent_lines(debug_information, indent=2)


def main(files: List):
    """files: list of filenames relative to current directory."""
    for fname in files:
        test_module = rewrite_as_test(fname)
        run(test_module, fname)


if __name__ == '__main__':
    files = sys.argv[1:]
    main(files)
