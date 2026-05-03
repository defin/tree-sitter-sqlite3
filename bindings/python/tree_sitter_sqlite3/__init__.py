"""SQLite3 grammar for tree-sitter.

Minimal binding — exposes `language()` for use with `tree_sitter.Language`.
Queries (highlights / locals / tags) live at the repo root in queries/
and are referenced by editor integrations via tree-sitter.json. They
are not bundled into the Python package.
"""

from ._binding import language


__all__ = ["language"]
