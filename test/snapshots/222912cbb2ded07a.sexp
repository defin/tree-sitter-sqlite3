# input:
#   SELECT CURRENT_TIMESTAMP;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (current_time_literal)))))
