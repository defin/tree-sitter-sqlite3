# input:
#   CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1;
---
(source_file
  (create_view_statement
    name: (qualified_table_name
      name: (identifier))
    body: (select_clause
      columns: (result_column_list
        (star_result_column))
      from: (from_clause
        source: (table_or_subquery
          (qualified_table_name
            name: (identifier))))
      where: (where_clause
        (binary_expression
          left: (column_reference
            name: (identifier))
          right: (numeric_literal))))))
