from macropy.core.test.macros.basic_block_macro import macros, my_macro, my_nested_outer, my_nested_inner

def run():
    x = 10
    with my_macro as y:
        x = x + 1

    z = 10
    with my_nested_outer:
        with my_nested_inner:
            z = z + 1  # should get replaced by z = z * 2
    assert z == 80

    z = 10
    with my_nested_inner, my_nested_outer:
        z = z + 1
    assert z == 80

    return x
