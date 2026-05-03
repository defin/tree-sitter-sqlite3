# input:
#   UPDATE t SET n = 2 WHERE id = 1 RETURNING *;
---
(source_file
  (update_statement
    target: (qualified_table_name
      name: (identifier))
    assignment: (set_assignment
      column: (identifier)
      value: (numeric_literal))
    where: (where_clause
      (binary_expression
        left: (column_reference
          name: (identifier))
        right: (numeric_literal)))
    returning: (returning_clause
      (result_column_list
        (star_result_column)))))
