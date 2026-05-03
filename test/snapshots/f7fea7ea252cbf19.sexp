# input:
#   SELECT * FROM a WHERE EXISTS (SELECT 1 FROM b WHERE b.x = a.x);
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
      (exists_expression
        (select_clause
          columns: (result_column_list
            (expression_result_column
              expression: (numeric_literal)))
          from: (from_clause
            source: (table_or_subquery
              (qualified_table_name
                name: (identifier))))
          where: (where_clause
            (binary_expression
              left: (column_reference
                table: (identifier)
                name: (identifier))
              right: (column_reference
                table: (identifier)
                name: (identifier)))))))))
