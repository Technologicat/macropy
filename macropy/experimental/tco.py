from macropy.core.macros import *
from macropy.experimental.pattern import macros, switch, _matching

from macropy.core.quotes import macros, q

__all__ = ['tco']

macros = Macros()

in_tc_stack = [False]

def trampoline(func, args, varargs, kwargs):
    """
    Repeatedly apply a function until it returns a value.

    The function may return (tco.CALL, func, args, kwargs) or (tco.IGNORE,
    func, args, kwargs) or just a value.
    """
    ignoring = False
    while True:
        if hasattr(func, 'tco'):
            in_tc_stack[-1] = True
        result = func(*list(args), **kwargs)
        # for performance reasons, do not use pattern matching here
        if isinstance(result, tuple):
            if result[0] is tco.CALL:
                func = result[1]
                args = result[2]
                varargs = result[3]
                kwargs = result[4]
                continue
            elif result[0] is tco.IGNORE:
                ignoring = True
                func = result[1]
                args = result[2]
                varargs = result[3]
                kwargs = result[4]
                continue
        if ignoring:
            in_tc_stack.pop()
            return None
        else:
            in_tc_stack.pop()
            return result


def trampoline_decorator(func):
    import functools
    @functools.wraps(func)
    def trampolined(*args, **kwargs):
        if in_tc_stack[-1]:
            in_tc_stack[-1] = False
            return func(*args, **kwargs)
        in_tc_stack.append(False)
        return trampoline(func, args, [], kwargs)

    trampolined.tco = True
    return trampolined


@macros.decorator()
def tco(tree, **kw):
    @Walker
    # Replace returns of calls
    def return_replacer(tree, **kw):
        with switch(tree):
            if Return(value=Call(
                    func=func, 
                    args=args, 
                    starargs=starargs, 
                    kwargs=kwargs)):
                with q as code:
                    return (tco.CALL,
                            ast(func),
                            ast(List(args, Load())),
                            ast(starargs or List([], Load())),
                            ast(kwargs or Dict([],[])))
                return code
            else:
                return tree

    # Replace calls (that aren't returned) which happen to be in a tail-call
    # position
    def replace_tc_pos(node):
        with switch(node):
            if Expr(value=Call(
                    func=func,
                    args=args,
                    starargs=starargs,
                    kwargs=kwargs)):
                with q as code:
                    return (tco.IGNORE,
                            ast(func),
                            ast(List(args, Load())),
                            ast(starargs or List([], Load())),
                            ast(kwargs or Dict([], [])))
                return code
            elif If(test=test, body=body, orelse=orelse):
                body[-1] = replace_tc_pos(body[-1])
                if orelse:
                    orelse[-1] = replace_tc_pos(orelse[-1])
                return If(test, body, orelse)
            else:
                return node

    tree = return_replacer.recurse(tree)
    tree.decorator_list = ([q(tco.trampoline_decorator)] +
            tree.decorator_list)
    tree.body[-1] = replace_tc_pos(tree.body[-1])
    return tree


# ok, so now you will only need to import tco...
tco.trampoline_decorator = trampoline_decorator
tco.IGNORE = ['tco_ignore']
tco.CALL = ['tco_call']
tco.in_tc_stack = in_tc_stack