# input:
#   SELECT * FROM a NATURAL JOIN b;
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
            name: (identifier)))))))
