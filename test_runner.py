"""Tests for runner.py

The big question is: Can these tests be run using runner?
Answer is: Yes it can!

It's not a great idea though, since this is supposed to check the runner correctness, a failing runner could
pretend to be working fine...
"""
import ast

from runner import AddIntermediateVariablesTransformer


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
