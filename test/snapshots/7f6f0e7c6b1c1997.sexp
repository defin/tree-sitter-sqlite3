# input:
#   SELECT 1 + 2 * 3;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (binary_expression
          left: (numeric_literal)
          right: (binary_expression
            left: (numeric_literal)
            right: (numeric_literal)))))))
