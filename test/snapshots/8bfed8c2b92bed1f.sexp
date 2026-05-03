# input:
#   CREATE VIRTUAL TABLE fts USING fts5(content, tokenize='porter');
---
(source_file
  (create_virtual_table_statement
    name: (qualified_table_name
      name: (identifier))
    module: (identifier)
    module_arguments: (vtab_module_arg)
    module_arguments: (vtab_module_arg)))
