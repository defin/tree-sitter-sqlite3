# input:
#   VACUUM INTO 'backup.db';
---
(source_file
  (vacuum_statement
    destination: (string_literal)))
