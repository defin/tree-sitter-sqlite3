# input:
#   SELECT u.* FROM users u;
---
(source_file
  (select_statement
    columns: (result_column_list
      (qualified_star_result_column
        table: (identifier)))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))
        alias: (identifier)))))
