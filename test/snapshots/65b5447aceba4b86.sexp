# input:
#   INSERT INTO archive SELECT * FROM users WHERE id < 100;
---
(source_file
  (insert_statement
    target: (qualified_table_name
      name: (identifier))
    source: (select_clause
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
