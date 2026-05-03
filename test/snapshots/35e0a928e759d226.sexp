# input:
#   SELECT -x, ~y, NOT z;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (unary_expression
          operand: (column_reference
            name: (identifier))))
      (expression_result_column
        expression: (unary_expression
          operand: (column_reference
            name: (identifier))))
      (expression_result_column
        expression: (unary_expression
          operand: (column_reference
            name: (identifier)))))))
