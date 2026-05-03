# input:
#   SELECT length(trim(name)) FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (function_call
          name: (identifier)
          arguments: (normal_function_arguments
            (function_call
              name: (identifier)
              arguments: (normal_function_arguments
                (column_reference
                  name: (identifier))))))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
