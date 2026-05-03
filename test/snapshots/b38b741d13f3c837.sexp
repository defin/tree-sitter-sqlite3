# input:
#   EXPLAIN SELECT * FROM t;
---
(source_file
  (explain_statement
    statement: (select_statement
      columns: (result_column_list
        (star_result_column))
      from: (from_clause
        source: (table_or_subquery
          (qualified_table_name
            name: (identifier)))))))
