# input:
#   SELECT a FROM t1 UNION ALL SELECT b FROM t2;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (column_reference
          name: (identifier))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))
    columns: (result_column_list
      (expression_result_column
        expression: (column_reference
          name: (identifier))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
