# input:
#   CREATE TABLE archive AS SELECT * FROM users WHERE id < 100;
---
(source_file
  (create_table_statement
    name: (qualified_table_name
      name: (identifier))
    (select_clause
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
