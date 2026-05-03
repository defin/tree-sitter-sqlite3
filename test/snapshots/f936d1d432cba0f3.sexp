# input:
#   SELECT CAST(x AS VARCHAR(255)) FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (cast_expression
          value: (column_reference
            name: (identifier))
          type: (type_name
            (identifier)
            (numeric_literal)))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
