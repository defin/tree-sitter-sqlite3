# input:
#   SELECT count(*) FILTER (WHERE x > 0) OVER () FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (function_call
          name: (identifier)
          arguments: (star_argument)
          filter: (filter_clause
            (binary_expression
              left: (column_reference
                name: (identifier))
              right: (numeric_literal)))
          over: (over_clause))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
