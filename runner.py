#!/home/laurent/miniconda3/envs/genetic/bin/python

# Grammar here: https://docs.python.org/3/library/ast.html
# A-mazing practical docs: http://greentreesnakes.readthedocs.io/en/latest/index.html


# 1. We want to call each test function (top-level function starting with 'test').

# 2. When we run the file we want it to run all the tests even if one fails.

# 3. We want nice error messages with plain `assert`.


import sys
import typing
from typing import List
import ast

import re

from utils import ast_to_code, print_failures


def rewrite_as_test(fname: str) -> ast.Module:
    """Read `fname` into an AST tree and:

    * Find all test functions.
    * Add a function call wrapped in a try except AssertionError after the definition for each test.
    * Rewrite assert statements so we have more relevant data to show in our failure report.

    :return the rewritten ast.Module.
    """
    with open(fname, 'r') as f:
        src = f.read()

    mod = ast.parse(src)
    functions = [(i, statement) for i, statement in enumerate(mod.body) if isinstance(statement, ast.FunctionDef)]

    test_functions = [(i, function_def) for i, function_def in functions if is_test_function(function_def)]
    print(f'Collected {len(test_functions)} tests...' if test_functions else 'No tests have been found!')

    for n_already_inserted, (i, f) in enumerate(test_functions):
        f = RewriteAssertNodeTransformer().visit(f)
        name = ast.Name(id=f.name, ctx=ast.Load())
        # No args passed to the test functions for now
        call = ast.Call(name, [], [])
        # Call node needs to be wrapped. In Expr since we don't use the return value.
        call_expr = ast.Expr(call)

        # Now we wrap in a try except so we can keep running even if the test fails
        except_handler = ast.ExceptHandler(type=ast.Name(id='AssertionError', ctx=ast.Load()), name='e',
                                           body=[
                                               get_print_node(on_fail_message(f.name)),
                                               get_log_error_node(f.name, 'e'),
                                           ])

        wrapped = ast.Try(body=[call_expr], handlers=[except_handler],
                          orelse=[get_print_node(on_success_message(f.name))], finalbody=[])

        # We insert it at the top-level of our module (similar to adding lines to the file)
        mod.body.insert(i + 1 + n_already_inserted, wrapped)

    # Our module has nodes without lineno and column offset. Tis bad. Breaks compiling. We fill it sort-of-randomly.
    ast.fix_missing_locations(mod)
    return mod


class RewriteAssertNodeTransformer(ast.NodeTransformer):
    """NodeTransformer lets us return a list when the node is part of a collection of statements.
    This lets us add to the `body` of a module or function definition for instance.

    In our case we have:

    FunctionDef -> body: List[statement]

    with an ast.Assert somewhere in `body`, and we want to add a node before the ast.Assert in the `body` list.
    """

    def visit_Assert(self, node):
        # This super is not really required, it would be if we had asserts in asserts. But that's unlikely!
        # Though not impossible if we have intermediate functions with asserts in it...
        super().generic_visit(node)

        # We want to look at all computation nodes in the children and store intermediate values in variables.
        # Then use these variables in the assert statement (so functions are not called twice).
        # We cant do variable assignments under the assert node (at least without some serious trick!)
        # So we need a step where we collect all assignments we want to make.
        transformer = AddIntermediateVariablesTransformer()
        node = transformer.visit(node)

        return [*reversed(transformer.assignments), node]


class AddIntermediateVariablesTransformer(ast.NodeTransformer):
    """Replaces all Call and BinOp nodes with call to variables whose definition we will (later) insert before the
    transformed node.

    The transformed node output after .visit will not be 'standalone' as it relies on variable assignments being
    previously run.
    """

    # A prefix on all variables we create here so we (hopefully!) dont collide with the user variables.
    prefix = '_intermediate_'
    reg = re.compile(f'{prefix}([0-9]+)_(.*)')

    def __init__(self):
        super().__init__()
        # A list of the assignment nodes we need for our transformed node to make sense
        # We will insert these before the transformed node so all variables we refer to are defined.
        self.assignments = []
        self.counter = 1

        # I would like to record the depth of the assignment but the parent class implements a depth-first traversal.
        # This would be the depth in terms of Call and BinOp nodes (to be accurate)
        # I can do this by rewriting entirely generic_visit. I don't see a simpler solution right now.
        # self.depth = 1

    def generic_visit(self, node):
        return super().generic_visit(node)

    def collect_assignments_and_transform(self, node):
        # Note since ast_to_code is recursive we will be doing a lot of repeated work here.
        # (We will call it from the root node, then on children... But the call on the root does all the work already!)
        user_friendly_name = ast_to_code(node)
        # We need a unique id so we use a counter. Fun to see we can use whatever we want (?) in the variable name.
        variable_id = f'{self.prefix}{self.counter}_{user_friendly_name}'
        self.assignments.append(ast.Assign(targets=[ast.Name(id=variable_id, ctx=ast.Store())], value=node))
        self.counter += 1
        self.generic_visit(node)
        return ast.Name(id=variable_id, ctx=ast.Load())

    def visit_Call(self, node):
        return self.collect_assignments_and_transform(node)

    def visit_BinOp(self, node):
        return self.collect_assignments_and_transform(node)

    @classmethod
    def get_friendly_name(cls, variable_id: str) -> str:
        return cls.reg.match(variable_id).groups()[1]

    @classmethod
    def get_order(cls, variable_id: str) -> int:
        """return counter at the time of transformation for this assignment node."""
        groups = cls.reg.match(variable_id).groups()
        return int(groups[0])


def is_test_function(f: ast.FunctionDef) -> bool:
    return f.name.startswith('test')


def get_log_error_node(test_function_id, value_to_log_id: str) -> ast.Expr:
    """Return an ast node that appends the exception to a global list that we will be able to manipulate afterwards.

    We can find relevant info on an AssertionError e in e.__traceback__.tb_frame.f_locals.
    """
    # Instead of building the ast manually we parse the line we want.
    # Then we need to 'flatten' it since we want a single Expr and not a Module.
    # Note the hardcoded _global_errors (which could easily be unhardcoded)
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


def parse_context(variables: typing.Dict) -> typing.List[typing.Tuple]:
    """
    We might have collisions between our variables and the user's (or even between our variables alone!)
    here after getting the 'friendly name'...
    :param variables: Basically locals() of the relevant frame.
    :return: a list of tuples. Like locals().items() with better names (not necessarily unique in some edge cases!)
    """

    def to_friendly(key: str) -> typing.Tuple[str, int]:
        """:return: (friendly_name, value for ordering)"""
        transformer_class = AddIntermediateVariablesTransformer
        if key.startswith(transformer_class.prefix):
            # count is a decent proxy for order.
            # It's like if we're giving all details about the left-hand side, then values for the right hand side.
            count = transformer_class.get_order(key)
            return transformer_class.get_friendly_name(key), count
        return key, 0
    # TODO: order this based on counter values (depth in tree?...)
    # We sort according to count
    sorted_pairs = sorted([(to_friendly(k), v) for k, v in variables.items()], key=lambda t: t[0][1])
    # We want to discard the count before we print it.
    return [(name, value) for (name, count), value in sorted_pairs]


def run(mod: ast.Module, filename: str):
    """Compile and run `mod`, report test results to stdout.
    `filename`: The name of the file containing the tests. Important so we can display the right stacktraces.
    """
    # We pass '<ast>' as filename so it's clear where it came from.
    # Actually we will pass the file containing the tests: it's a trick to get traceback to work.
    # Otherwise we have line numbers from the original file but traceback tries to look up a non-existing '<ast>' file
    # Sidenote: The trace module even ignores file whose name starts with < and ends with >.
    compiled = compile(mod, filename=filename, mode='exec')
    errors = {}
    # This is a bit fragile: things will break if a _global_errors variable is defined by the other program.
    # The (modified) tests we run will update this global variable.
    context = {'_global_errors': errors}
    exec(compiled, context, context)
    print_failures(errors, parse_context)


def main(files: List):
    """files: list of filenames relative to current directory."""
    for fname in files:
        test_module = rewrite_as_test(fname)
        run(test_module, fname)


def test_transformer():
    """Very basic test."""
    src = 'assert square(add(a, b)) == expected - 1'
    # We extract the assert node from the ast.Module we get from parsing.
    assert_node = ast.parse(src).body[0]
    transformer = AddIntermediateVariablesTransformer()
    assert_node = transformer.visit(assert_node)

    for descendant in ast.walk(assert_node):
        # We have replaced function calls and binary ops with variables (ast.Name).
        assert not isinstance(descendant, ast.Call)
        assert not isinstance(descendant, ast.BinOp)

    # We expect 3 new intermediary variables
    assert len(transformer.assignments) == 3
    var_names = [a.targets[0].id for a in transformer.assignments]
    names = set(transformer.get_friendly_name(name) for name in var_names)
    assert names == {'square(add(a, b))', 'add(a, b)', 'expected - 1'}


test_transformer()


if __name__ == '__main__':
    files = sys.argv[1:]
    main(files)
