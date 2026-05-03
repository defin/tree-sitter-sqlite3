# input:
#   SELECT * FROM a INNER JOIN b ON a.id = b.a_id;
---
(source_file
  (select_statement
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier)))
      join: (join_step
        source: (table_or_subquery
          (qualified_table_name
            name: (identifier)))
        constraint: (binary_expression
          left: (column_reference
            table: (identifier)
            name: (identifier))
          right: (column_reference
            table: (identifier)
            name: (identifier)))))))
