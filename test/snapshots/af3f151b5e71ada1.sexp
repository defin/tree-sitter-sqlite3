# input:
#   ROLLBACK TO SAVEPOINT s1;
---
(source_file
  (rollback_statement
    savepoint: (identifier)))
