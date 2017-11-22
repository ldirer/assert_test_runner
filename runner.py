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

# At top level for convenience. We can use it in an ipython interactive session.
import re

errors = {}


def run(mod: ast.Module, filename: str):
    # We pass '<ast>' as filename so it's clear where it came from.
    # Actually we will pass the file containing the tests: it's a trick to get traceback to work.
    # Otherwise we have line numbers from the original file but traceback tries to look up a non-existing '<ast>' file
    # Sidenote: The trace module even ignores file whose name starts with < and ends with >.
    compiled = compile(mod, filename=filename, mode='exec')
    # This is a bit fragile: things will break if a _global_errors variable is defined by the other program.
    context = {'_global_errors': errors}
    exec(compiled, context, context)
    print_failures(errors)


# grep "operator):" /path/to/_ast.py
BINOP_TO_SYMBOL = {
    ast.Add: '+',
    ast.BitAnd: '&',
    ast.BitOr: '|',
    ast.BitXor: '^',
    ast.Div: '/',
    ast.FloorDiv: '//',
    ast.LShift: '<<',
    ast.MatMult: '@',
    ast.Mod: '%',
    ast.Mult: '*',
    ast.Pow: '**',
    ast.RShift: '>>',
    ast.Sub: '-'
}


def ast_to_code(node) -> str:
    """A very basic function that does not handle a lot of cases but tries to return a friendly code based on an ast.
    Specifically we want to rewrite assignments and function calls.
    We dont have to deal with try except, etc.

    Though that's still a lot of things!
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        args = ", ".join([ast_to_code(arg) for arg in node.args])
        return f'{ast_to_code(node.func)}({args})'
    if isinstance(node, ast.BinOp):
        return f'{ast_to_code(node.left)} {BINOP_TO_SYMBOL[node.op.__class__]} {ast_to_code(node.right)}'
    if isinstance(node, ast.Num):
        return str(node.n)
    else:
        raise ValueError('Type not handled:', node)


class AddIntermediateVariablesTransformer(ast.NodeTransformer):
    """The transformed node output after .visit will not be 'standalone' as it relies on variable assignments being
    previously run."""

    # A prefix on all variables we create here so we (hopefully!) dont collide with the user variables.
    prefix = '_intermediate_'
    reg = re.compile(f'{prefix}[0-9]+_(.*)')

    def __init__(self):
        super().__init__()
        # A list of the assignment nodes we need for our transformed node to make sense
        # (so all variables we refer to in the transformed tree are defined).
        self.assignments = []
        self.counter = 0

    def collect_assignments_and_transform(self, node):
        # Note since ast_to_code is recursive we will be doing a lot of repeated work here.
        # (We will call it from the root node, then on children... But the call on the root does all the work already!)
        user_friendly_name = ast_to_code(node)
        # We need a unique id so we use a counter. Fun to see we can use whatever we want (?) in the variable name.
        variable_id = f'{self.prefix}{self.counter}_{user_friendly_name}'
        self.assignments.append(ast.Assign(targets=[ast.Name(id=variable_id, ctx=ast.Store())], value=node))
        self.counter += 1
        super().generic_visit(node)
        return ast.Name(id=variable_id, ctx=ast.Load())

    def visit_Call(self, node):
        return self.collect_assignments_and_transform(node)

    def visit_BinOp(self, node):
        return self.collect_assignments_and_transform(node)

    @classmethod
    def get_friendly_name(cls, variable_id: str) -> str:
        return cls.reg.match(variable_id).groups()[0]


class RewriteAssertNodeTransformer(ast.NodeTransformer):
    """NodeTransformer lets us return a list when the node is part of a collection of statements.
    This lets us add to the `body` of a module for instance."""

    def visit_Assert(self, node):
        # This super is not really required, it would be if we had asserts in asserts. But that's unlikely!
        # Though not impossible if we have intermediate functions with asserts in it...
        super().generic_visit(node)

        # We want to look at all Call, BinOp nodes in the children and store intermediate values in variables.
        # Then use these variables in the assert statement (so functions are not called twice!).
        # The nodes of interest might be at any depth from the assert node though... And we cant do variable
        # assignments under assert. So we need a step where we collect all assignments we want to make.

        transformer = AddIntermediateVariablesTransformer()
        node = transformer.visit(node)

        return [*reversed(transformer.assignments), node]


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
        f = RewriteAssertNodeTransformer().visit(f)
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


def parse_context(variables: typing.Dict) -> typing.List[typing.Tuple]:
    """

    We might have collisions between our variables and the user's (or even between our variables alone!)
    here after getting the 'friendly name'...
    :param variables: Basically locals() of the relevant frame.
    :return: a list of tuples. Like locals().items() with better names (not necessarily unique in some edge cases!)
    """

    def to_friendly(key: str) -> str:
        if key.startswith(AddIntermediateVariablesTransformer.prefix):
            return AddIntermediateVariablesTransformer.get_friendly_name(key)
        return key
    # TODO: order this based on counter values (depth in tree?...)
    return [(to_friendly(k), v) for k, v in variables.items()]


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
        # The info we want is one frame higher TODO: NOPE NOT ALWAYS. Nested function...
        variables_of_interest = stack_summary[1].locals
        variables_of_interest = parse_context(variables_of_interest)
        debug_str = '\n'.join([f'{k}={v}' for k, v in variables_of_interest])
        print('Where: ')
        print_indent_lines(debug_str, indent=2)


# TODO:
# Change the assert statement so that we can report ALL intermediate values computed durig the assert
# e.g assert f(g(a)) == b
# --> a=1,b=0,g(a)='wat',f(g(a))='woops'


def annotate_ast_log(node: ast.Expr) -> ast.Expr:
    """Log all intermediate values computed. To achieve that we need to store each computation in a variable."""
    ast


def main(files: List):
    """files: list of filenames relative to current directory."""
    for fname in files:
        test_module = rewrite_as_test(fname)
        run(test_module, fname)


examples = {
    'try_except': """
try:
    a + 1
except NameError as e:
    print(e.args)
else:
    print('in else')
        """.strip(' '),
    'multiline_function': """
def f():
    print(1)
    print(2)
""".strip(' ')

}


def test_transformer():
    src = """
def test_plain_add():
    a, b = 4, 4
    # Ideally we want to see that a + b = 8 in the failure report!
    assert 9 == a + b
    """

    a = ast.parse(src).body[0].body
    import ipdb;
    ipdb.set_trace()


# test_transformer()



if __name__ == '__main__':
    files = sys.argv[1:]
    main(files)
