#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kernel for a MacroPy-enabled REPL in IPython.

Installation::

    jupyter kernelspec install --user macroipy

The current directory should contain a subdirectory ``macroipy`` with the file
``kernel.json`` containing the kernel spec. Installation will register the kernel
for ``jupyter notebook``.

Usage in terminal::

    jupyter console --kernel macroipy

Based on ``macropy.core.console`` and the following:

    https://ipython.readthedocs.io/en/stable/config/inputtransforms.html
    https://docs.python.org/3/library/ast.html#ast.NodeVisitor
    https://ipython-books.github.io/16-creating-a-simple-kernel-for-jupyter/
"""

import ast
import importlib
from collections import OrderedDict
from functools import partial

from ipykernel.ipkernel import IPythonKernel
from IPython.core.error import InputRejected

from macropy import __version__ as macropy_version
from macropy.core.macros import ModuleExpansionContext, detect_macros

_placeholder = "<interactive input>"

class MacroTransformer(ast.NodeTransformer):
    def __init__(self, kernel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel = kernel
        self.bindings = OrderedDict()

    def visit(self, tree):
        try:
            bindings = detect_macros(tree, '__main__', reload=True)  # macro imports
            if bindings:
                self.kernel.stubs_changed = True
                for fullname, macro_bindings in bindings:
                    mod = importlib.import_module(fullname)
                    self.bindings[fullname] = (mod, macro_bindings)
            newtree = ModuleExpansionContext(tree, self.kernel.src, self.bindings.values()).expand_macros()
            self.kernel.src = _placeholder
            return newtree
        except Exception as err:
            # see IPython.core.interactiveshell.InteractiveShell.transform_ast()
            raise InputRejected(*err.args)

class MacroPyKernel(IPythonKernel):
    implementation = 'macropy'
    implementation_version = macropy_version

    @property
    def banner(self):
        return "MacroPy {} on {}".format(self.implementation_version, super().banner)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.src = _placeholder
        if hasattr(self.shell, "input_transformers_post"):  # IPython 7.0+ with Python 3.5+
            def get_source_code(lines):
                self.src = lines
                return lines
            self.shell.input_transformers_post.append(get_source_code)

        self.stubs_changed = False
        self.current_stubs = set()
        self.macro_transformer = MacroTransformer(kernel=self)
        self.shell.ast_transformers.append(self.macro_transformer)  # TODO: last or first?

        # initialize MacroPy in the session
        self.do_execute("import macropy.activate", silent=True,
                        store_history=False,
                        user_expressions=None,
                        allow_stdin=False)

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        ret = super().do_execute(code, silent,
                                 store_history=store_history,
                                 user_expressions=user_expressions,
                                 allow_stdin=allow_stdin)
        if self.stubs_changed:
            self._refresh_stubs()
        return ret

    def _refresh_stubs(self):
        """Refresh macro stub imports.

        Called whenever macro imports are performed, so that Jupyter help
        "some_macro?" works for the currently available macros.

        This allows the user to view macro docstrings.
        """
        self.stubs_changed = False
        internal_execute = partial(super().do_execute,
                                   silent=True,
                                   store_history=False,
                                   user_expressions=None,
                                   allow_stdin=False)

        # Clear previous stubs, because our MacroTransformer overrides
        # the available set of macros from a given module with those
        # most recently imported from that module.
        for asname in self.current_stubs:
            internal_execute("del {}".format(asname))
        self.current_stubs = set()

        for fullname, (_, macro_bindings) in self.macro_transformer.bindings.items():
            for _, asname in macro_bindings:
                self.current_stubs.add(asname)
            stubnames = ", ".join("{} as {}".format(name, asname) for name, asname in macro_bindings)
            internal_execute("from {} import {}".format(fullname, stubnames))

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=MacroPyKernel)
