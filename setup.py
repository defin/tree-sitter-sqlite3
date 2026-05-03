"""Build script for the tree-sitter-sqlite3 Python bindings.

setuptools cannot infer Extension specs from pyproject.toml alone, so
we declare them here. The wheel ships:

  - the pure-Python `tree_sitter_sqlite3` package (bindings/python/...)
  - a `_binding` C extension that links the parser produced by
    tree-sitter-cli (`src/parser.c`) into a `language()` function.
"""

from setuptools import Extension, setup


setup(
    ext_modules=[
        Extension(
            name="tree_sitter_sqlite3._binding",
            sources=[
                "bindings/python/tree_sitter_sqlite3/binding.c",
                "src/parser.c",
                "src/scanner.c",
            ],
            include_dirs=["src"],
            extra_compile_args=["-std=c11"],
            define_macros=[("PY_SSIZE_T_CLEAN", None)],
        ),
    ],
)
