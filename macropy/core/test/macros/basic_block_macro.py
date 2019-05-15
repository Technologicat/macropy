import macropy.core
import macropy.core.macros

macros = macropy.core.macros.Macros()

@macros.block
def my_macro(tree, target, **kw):
    assert macropy.core.unparse(target) == "y"
    assert macropy.core.unparse(tree).strip() == "x = (x + 1)", macropy.core.unparse(tree)
    return tree * 3

@macros.block
def my_nested_outer(tree, **kw):
    assert macropy.core.unparse(tree).strip() == "z = (z * 2)", macropy.core.unparse(tree)
    return tree * 3

@macros.block
def my_nested_inner(tree, **kw):  # important: generate new tree from scratch for this test
    return [macropy.core.parse_stmt("z = z * 2")]
