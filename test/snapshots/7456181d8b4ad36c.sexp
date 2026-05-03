# input:
#   SELECT CASE x WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (case_expression
          subject: (column_reference
            name: (identifier))
          when: (numeric_literal)
          then: (string_literal)
          when: (numeric_literal)
          then: (string_literal)
          else: (string_literal))))))
