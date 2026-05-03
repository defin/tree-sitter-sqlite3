# input:
#   SELECT CASE WHEN x > 0 THEN 'pos' ELSE 'np' END;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (case_expression
          when: (binary_expression
            left: (column_reference
              name: (identifier))
            right: (numeric_literal))
          then: (string_literal)
          else: (string_literal))))))
