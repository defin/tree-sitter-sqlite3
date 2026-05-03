# input:
#   SELECT * FROM t WHERE x NOT NULL;
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
      (is_null_expression
        operand: (column_reference
          name: (identifier))))))
