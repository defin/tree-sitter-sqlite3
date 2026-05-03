# input:
#   SELECT data -> 'a' ->> 'b';
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (binary_expression
          left: (binary_expression
            left: (column_reference
              name: (identifier))
            right: (string_literal))
          right: (string_literal))))))
