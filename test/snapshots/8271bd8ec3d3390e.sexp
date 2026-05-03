# input:
#   SELECT * FROM t WHERE x NOT BETWEEN 1 AND 10;
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
      (between_expression
        operand: (column_reference
          name: (identifier))
        low: (numeric_literal)
        high: (numeric_literal)))))
