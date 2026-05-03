# input:
#   SELECT 1, 'a', NULL;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (numeric_literal))
      (expression_result_column
        expression: (string_literal))
      (expression_result_column
        expression: (null_literal)))))
