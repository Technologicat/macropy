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
from sys import stderr

from ipykernel.ipkernel import IPythonKernel

from macropy import __version__ as macropy_version
from macropy.core.macros import ModuleExpansionContext, detect_macros

class MacroTransformer(ast.NodeTransformer):
    def __init__(self, kernel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel = kernel
        self.bindings = OrderedDict()

    def visit(self, tree):
        try:
            for fullname, macro_bindings in detect_macros(tree, '__main__', reload=True):
                mod = importlib.import_module(fullname)
                self.bindings[fullname] = (mod, macro_bindings)
            newtree = ModuleExpansionContext(tree, self.kernel.src, self.bindings.values()).expand_macros()
            self.kernel._clear_src()
            return newtree
        except Exception as err:
            print("Macro expansion error: {}".format(err), file=stderr)
            return tree

_placeholder = "<interactive input>"

class MacroPyKernel(IPythonKernel):
    implementation = 'macropy'
    implementation_version = macropy_version

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.src = _placeholder
        if hasattr(self.shell, "input_transformers_post"):  # IPython 7.0+ with Python 3.5+
            def get_source_code(lines):
                self.src = lines
                return lines
            self.shell.input_transformers_post.append(get_source_code)

        self.shell.ast_transformers.append(MacroTransformer(kernel=self))

        # initialize MacroPy in the session
        self.do_execute("import macropy.activate", silent=True,
                        store_history=False,
                        user_expressions=None,
                        allow_stdin=False)

    def _clear_src(self):
        self.src = _placeholder

    @property
    def banner(self):
        return "MacroPy {} on {}".format(self.implementation_version, super().banner)

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=MacroPyKernel)
