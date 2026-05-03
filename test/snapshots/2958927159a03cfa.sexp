# input:
#   SELECT a & b | c << 2;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (binary_expression
          left: (binary_expression
            left: (binary_expression
              left: (column_reference
                name: (identifier))
              right: (column_reference
                name: (identifier)))
            right: (column_reference
              name: (identifier)))
          right: (numeric_literal))))))
