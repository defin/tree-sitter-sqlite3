# input:
#   SELECT * FROM t WHERE x IS NULL;
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
        right: (null_literal)))))
