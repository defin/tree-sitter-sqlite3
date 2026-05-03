#!/usr/bin/env python3
"""Quick probe: does libsqlite3 accept this SQL? Reports the error
message verbatim so we can see exactly what classifier is seeing."""

import ctypes, ctypes.util, sys

lib = ctypes.CDLL(ctypes.util.find_library("sqlite3"))
lib.sqlite3_open.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
lib.sqlite3_prepare_v2.argtypes = [
    ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int,
    ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_char_p),
]
lib.sqlite3_prepare_v2.restype = ctypes.c_int
lib.sqlite3_finalize.argtypes = [ctypes.c_void_p]
lib.sqlite3_errmsg.argtypes = [ctypes.c_void_p]
lib.sqlite3_errmsg.restype = ctypes.c_char_p

db = ctypes.c_void_p()
lib.sqlite3_open(b":memory:", ctypes.byref(db))

# Read SQL from argv OR stdin (one per line, '\\n'-escaped if needed).
if sys.argv[1:]:
    inputs = sys.argv[1:]
else:
    inputs = []
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        inputs.append(line.replace("\\n", "\n").replace("\\t", "\t"))

for sql in inputs:
    sql_b = sql.encode("utf-8")
    stmt = ctypes.c_void_p()
    pz_tail = ctypes.c_char_p()
    rc = lib.sqlite3_prepare_v2(db, sql_b, -1, ctypes.byref(stmt), ctypes.byref(pz_tail))
    err = lib.sqlite3_errmsg(db)
    msg = err.decode("utf-8", errors="replace") if err else "(none)"
    print(f"--- {sql!r}")
    print(f"  rc:  {rc}")
    print(f"  msg: {msg}")
    if pz_tail.value:
        print(f"  tail: {pz_tail.value[:80]!r}")
    lib.sqlite3_finalize(stmt)
