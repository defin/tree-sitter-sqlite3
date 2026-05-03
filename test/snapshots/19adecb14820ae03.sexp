# input:
#   SELECT (SELECT max(id) FROM b) FROM a;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (subquery_expression
          (select_clause
            columns: (result_column_list
              (expression_result_column
                expression: (function_call
                  name: (identifier)
                  arguments: (normal_function_arguments
                    (column_reference
                      name: (identifier))))))
            from: (from_clause
              source: (table_or_subquery
                (qualified_table_name
                  name: (identifier))))))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
