# input:
#   SELECT * FROM (SELECT id FROM users) AS u;
---
(source_file
  (select_statement
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (select_clause
          columns: (result_column_list
            (expression_result_column
              expression: (column_reference
                name: (identifier))))
          from: (from_clause
            source: (table_or_subquery
              (qualified_table_name
                name: (identifier)))))
        alias: (identifier)))))
