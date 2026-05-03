# input:
#   SELECT * FROM a WHERE id IN (SELECT id FROM b);
---
(source_file
  (select_statement
    columns: (result_column_list
      (star_result_column))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))
    where: (where_clause
      (in_subquery_expression
        operand: (column_reference
          name: (identifier))
        (select_clause
          columns: (result_column_list
            (expression_result_column
              expression: (column_reference
                name: (identifier))))
          from: (from_clause
            source: (table_or_subquery
              (qualified_table_name
                name: (identifier)))))))))
