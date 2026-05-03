# input:
#   SELECT CAST(x AS INTEGER) FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (cast_expression
          value: (column_reference
            name: (identifier))
          type: (type_name
            (identifier)))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
