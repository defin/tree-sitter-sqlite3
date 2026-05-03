# input:
#   SELECT name COLLATE NOCASE FROM t;
---
(source_file
  (select_statement
    columns: (result_column_list
      (expression_result_column
        expression: (collate_expression
          operand: (column_reference
            name: (identifier))
          collation: (identifier))))
    from: (from_clause
      source: (table_or_subquery
        (qualified_table_name
          name: (identifier))))))
