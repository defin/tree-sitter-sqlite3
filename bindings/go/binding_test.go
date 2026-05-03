package tree_sitter_sqlite3_test

import (
	"testing"

	tree_sitter "github.com/tree-sitter/go-tree-sitter"
	tree_sitter_sqlite3 "github.com/defin/tree-sitter-sqlite3/bindings/go"
)

func TestCanLoadGrammar(t *testing.T) {
	language := tree_sitter.NewLanguage(tree_sitter_sqlite3.Language())
	if language == nil {
		t.Errorf("Error loading SQLite3 grammar")
	}
}
