# input:
#   EXPLAIN QUERY PLAN SELECT * FROM t WHERE id = 1;
---
(source_file
  (explain_statement
    statement: (select_statement
      columns: (result_column_list
        (star_result_column))
      from: (from_clause
        source: (table_or_subquery
          (qualified_table_name
            name: (identifier))))
      where: (where_clause
        (binary_expression
          left: (column_reference
            name: (identifier))
          right: (numeric_literal))))))
