#!/home/laurent/miniconda3/envs/genetic/bin/python


# Grammar here: https://docs.python.org/3/library/ast.html
# A-mazing practical docs: http://greentreesnakes.readthedocs.io/en/latest/index.html

# Could use https://github.com/berkerpeksag/astor for debugging (ast -> string of code)

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


# This is nice but we need to know the position of the function in the module `body`
#class CollectTestFunctionsNodeTransformer(MyNodeTransformer):
#    """Collect the test functions nodes. Could just be a NodeVisitor."""
#
#    def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        self.test_functions = []
#
#
#    def visit_FunctionDef(self, node):
#        """We want to add a node"""
#        if node.name.startswith('test'):
#            self.test_functions.append(node)
#
#        return node
#
#collector = CollectTestFunctionsNodeTransformer()
#collector.visit(module)
#print(f'Collected {len(collector.test_functions)} test(s)!')


#class AddTestCallNodeTransformer(MyNodeTransformer):
#    def visit_FunctionDef

# transformed_tree = MyNodeTransformer().visit(module)


n_already_inserted = 0
for i, f in test_functions:
    name = ast.Name(id=f.name, ctx=ast.Load())
    call = ast.Call(name, [], [])
    # Call node needs to be wrapped. In Expr since we dont use the value.
    call_expr = ast.Expr(call)
    module.body.insert(i + 1 + n_already_inserted, call_expr)
    n_already_inserted += 1
#
## Our module has nodes without lineno and column offset. Tis bad. Breaks compiling.
ast.fix_missing_locations(module)

# We pass '<ast>' as filename so it's clear where it came from.
compiled = compile(module, filename='<ast>', mode='exec')

exec(compiled)



if __name__ == '__main__':
    files = sys.argv[1:]
    main(files)
