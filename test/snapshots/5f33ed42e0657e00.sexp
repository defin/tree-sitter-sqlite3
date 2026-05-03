# input:
#   WITH t AS MATERIALIZED (SELECT 1) SELECT * FROM t;
---
(source_file
  (select_statement
    with: (with_clause
      cte: (cte_definition
        name: (identifier)
        body: (select_clause
          columns: (result_column_list
            (expression_result_column
              expression: (numeric_literal))))))
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
