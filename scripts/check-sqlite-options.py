#!/usr/bin/env python3
"""Check which compile-time options the loaded libsqlite3 has."""
import ctypes, ctypes.util

lib = ctypes.CDLL("/usr/local/lib/libsqlite3.so")
lib.sqlite3_libversion.restype = ctypes.c_char_p
lib.sqlite3_compileoption_get.argtypes = [ctypes.c_int]
lib.sqlite3_compileoption_get.restype = ctypes.c_char_p

print(f"version: {lib.sqlite3_libversion().decode()}")
print("compile options:")
i = 0
while True:
    opt = lib.sqlite3_compileoption_get(i)
    if not opt:
        break
    print(f"  {opt.decode()}")
    i += 1
