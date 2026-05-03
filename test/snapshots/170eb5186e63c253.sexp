# input:
#   CREATE TRIGGER log_insert AFTER INSERT ON users BEGIN INSERT INTO audit VALUES (1); END;
---
(source_file
  (create_trigger_statement
    name: (qualified_table_name
      name: (identifier))
    event: (trigger_event)
    table: (qualified_table_name
      name: (identifier))
    body: (insert_statement
      target: (qualified_table_name
        name: (identifier))
      source: (values_clause
        value: (numeric_literal)))))
