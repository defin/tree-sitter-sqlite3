# input:
#   WITH RECURSIVE counter (n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM counter WHERE n < 10) SELECT * FROM counter;
---
(source_file
  (select_statement
    with: (with_clause
      cte: (cte_definition
        name: (identifier)
        column: (identifier)
        body: (select_clause
          columns: (result_column_list
            (expression_result_column
              expression: (numeric_literal)))
          columns: (result_column_list
            (expression_result_column
              expression: (binary_expression
                left: (column_reference
                  name: (identifier))
                right: (numeric_literal))))
          from: (from_clause
            source: (table_or_subquery
              (qualified_table_name
                name: (identifier))))
          where: (where_clause
            (binary_expression
              left: (column_reference
                name: (identifier))
              right: (numeric_literal))))))
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
