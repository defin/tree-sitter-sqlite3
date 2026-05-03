# input:
#   SELECT row_number() OVER () FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (function_call
          name: (identifier)
          over: (over_clause))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
