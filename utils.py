# grep "operator):" /path/to/_ast.py
import ast
import traceback
import typing

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
    """A very basic function that takes an ast node and tries to return a line of python code.
    It does not handle a lot of cases, specifically we want to rewrite assignments and function calls.
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
    if isinstance(node, ast.Attribute):
        # This is a bit random, I had to do it to run test_runner using the runner.
        if isinstance(node.ctx, ast.Load):
            return f'{ast_to_code(node.value)}.{node.attr}'
        else:
            raise ValueError('Context not handled in ast.Attribute: ', node.ctx)
    else:
        raise ValueError('Type not handled yet:', node)


def print_failures(errors: typing.Dict, parse_context):
    """Print the failures (as listed in `errors`) that occurred in all the tests

    `parse_context`: a function that takes some locals() dict and mangles it into a list of key, value tuples.
    (Changing the key names in the process)
    """
    if not errors:
        # Good job! No failures to print.
        return

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
        # The info we want is in the last frame (the one containing the `assert`)
        variables_of_interest = stack_summary[-1].locals
        variables_of_interest = parse_context(variables_of_interest)
        debug_str = '\n'.join([f'{k}={v}' for k, v in variables_of_interest])
        print('Where: ')
        print_indent_lines(debug_str, indent=2)


def print_indent_lines(arg: str, indent=0, **kwargs):
    lines = arg.split('\n')
    indented_lines = [' ' * indent + line for line in lines]
    print(*indented_lines, sep='\n', **kwargs)

