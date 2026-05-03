# input:
#   SELECT main.users.id FROM main.users;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (column_reference
          schema: (identifier)
          table: (identifier)
          name: (identifier))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          schema: (identifier)
          name: (identifier))))))
