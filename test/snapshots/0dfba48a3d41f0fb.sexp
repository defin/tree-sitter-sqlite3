# input:
#   SELECT a || 'x';
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (binary_expression
          left: (column_reference
            name: (identifier))
          right: (string_literal))))))
