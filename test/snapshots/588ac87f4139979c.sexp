# input:
#   SELECT * FROM a JOIN b ON a.x=b.x JOIN c ON b.y=c.y;
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
            name: (identifier))))
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
