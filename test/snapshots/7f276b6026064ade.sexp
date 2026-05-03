# input:
#   SELECT 1 INTERSECT SELECT 2 EXCEPT SELECT 3;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (numeric_literal)))
    columns: (result_column_list
      (expression_result_column
        expression: (numeric_literal)))
    columns: (result_column_list
      (expression_result_column
        expression: (numeric_literal)))))
