# input:
#   SELECT * FROM t WHERE a IS NOT DISTINCT FROM b;
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
      (is_expression
        left: (column_reference
          name: (identifier))
        right: (column_reference
          name: (identifier))))))
