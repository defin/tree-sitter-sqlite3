# input:
#   SELECT * FROM t WHERE x IN (1, 2, 3);
---
(source_file
  (select_statement
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))
    where: (where_clause
      (in_list_expression
        operand: (column_reference
          name: (identifier))
        values: (numeric_literal)
        values: (numeric_literal)
        values: (numeric_literal)))))
