from macropy.core.test.macros.argument_macros import macros, expr_macro, block_macro, decorator_macro, expr_macro_with_named_args
import math

def run():
    x = expr_macro(1 + math.sqrt(5))[10 + 10 + 10]

    x = expr_macro_with_named_args(1 + 2 + 3, a=(1 + math.sqrt(5)))[10 + 10 + 10]

    with block_macro(1 + math.sqrt(5)) as y:
        x = x + 1

    @decorator_macro(1 + math.sqrt(5))
    def f():
        pass

    return x
