# input:
#   SELECT rank() OVER (PARTITION BY dept ORDER BY salary DESC) FROM emp;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (function_call
          name: (identifier)
          over: (over_clause
            (window_definition
              (window_partition_clause
                expression: (column_reference
                  name: (identifier)))
              (order_by_clause
                (order_term
                  (column_reference
                    name: (identifier)))))))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
