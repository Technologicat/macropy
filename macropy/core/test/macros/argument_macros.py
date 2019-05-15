import macropy.core
import macropy.core.macros

macros = macropy.core.macros.Macros()

@macros.expr
def expr_macro_with_named_args(tree, args, kwargs, **kw):
    assert "a" in kwargs, kwargs
    assert macropy.core.unparse(kwargs["a"]) == "(1 + math.sqrt(5))", macropy.core.unparse(kwargs["a"])
    assert list(map(macropy.core.unparse, args)) == ["((1 + 2) + 3)"], macropy.core.unparse(args)
    return tree

@macros.expr
def expr_macro(tree, args, **kw):
    assert list(map(macropy.core.unparse, args)) == ["(1 + math.sqrt(5))"], macropy.core.unparse(args)
    return tree

@macros.block
def block_macro(tree, args, **kw):
    assert list(map(macropy.core.unparse, args)) == ["(1 + math.sqrt(5))"], macropy.core.unparse(args)
    return tree

@macros.decorator
def decorator_macro(tree, args, **kw):
    assert list(map(macropy.core.unparse, args)) == ["(1 + math.sqrt(5))"], macropy.core.unparse(args)
    return tree
