# -*- coding: utf-8 -*-
"""IPython extension for a MacroPy-enabled REPL.

To enable::

    %load_ext macropy.imacro

To autoload it at IPython startup, put this into your ``ipython_config.py``::

    c.InteractiveShellApp.extensions = ["macropy.imacro"]
"""

import ast
import importlib
from collections import OrderedDict
from functools import partial

from IPython.core.error import InputRejected

from macropy import __version__ as macropy_version
from macropy.core.macros import ModuleExpansionContext, detect_macros

_placeholder = "<interactive input>"
_instance = None

def load_ipython_extension(ipython):
    print("MacroPy {} -- Syntactic macros for Python.".format(macropy_version))
    global _instance
    if not _instance:
        _instance = IMacroPyExtension(shell=ipython)

def unload_ipython_extension(ipython):
    global _instance
    _instance = None

class MacroTransformer(ast.NodeTransformer):
    def __init__(self, extension_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ext = extension_instance
        self.bindings = OrderedDict()

    def visit(self, tree):
        try:
            bindings = detect_macros(tree, '__main__', reload=True)  # macro imports
            if bindings:
                self.ext.macro_bindings_changed = True
                for fullname, macro_bindings in bindings:
                    mod = importlib.import_module(fullname)
                    self.bindings[fullname] = (mod, macro_bindings)
            newtree = ModuleExpansionContext(tree, self.ext.src, self.bindings.values()).expand_macros()
            self.ext.src = _placeholder
            return newtree
        except Exception as err:
            # see IPython.core.interactiveshell.InteractiveShell.transform_ast()
            raise InputRejected(*err.args)

class IMacroPyExtension:
    def __init__(self, shell):
        self.src = _placeholder
        self.shell = shell

        self.shell.get_ipython().events.register('pre_run_cell', self._get_source_code)
#        # TODO: maybe use something like the following instead, to get the
#        # source code after any string-based transformers have run:
#        if hasattr(self.shell, "input_transformers_post"):  # IPython 7.0+ with Python 3.5+
#            def get_source_code(lines):
#                self.src = lines
#                return lines
#            self.shell.input_transformers_post.append(get_source_code)

        self.macro_bindings_changed = False
        self.current_stubs = set()
        self.macro_transformer = MacroTransformer(extension_instance=self)
        self.shell.ast_transformers.append(self.macro_transformer)  # TODO: last or first?

        self.shell.get_ipython().events.register('post_run_cell', self._refresh_stubs)

        # initialize MacroPy in the session
        self.shell.run_cell("import macropy.activate", store_history=False, silent=True)

    def __del__(self):
        self.shell.get_ipython().events.unregister('post_run_cell', self._refresh_stubs)
        self.shell.ast_transformers.remove(self.macro_transformer)
        self.shell.get_ipython().events.unregister('pre_run_cell', self._get_source_code)

    def _get_source_code(self, info):
        """Get the source code of the current cell just before it runs."""
        self.src = info.raw_cell

    def _refresh_stubs(self, info):
        """Refresh macro stub imports.

        Called after running a cell, so that Jupyter help "some_macro?" works
        for the currently available macros.

        This allows the user to view macro docstrings.
        """
        if not self.macro_bindings_changed:
            return
        self.macro_bindings_changed = False
        internal_execute = partial(self.shell.run_cell,
                                   store_history=False,
                                   silent=True)

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
