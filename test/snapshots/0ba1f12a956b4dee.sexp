# input:
#   SELECT * FROM main.users;
---
(source_file
  (select_statement
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          schema: (identifier)
          name: (identifier))))))
