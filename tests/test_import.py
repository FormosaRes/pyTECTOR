# -*- coding: utf-8 -*-
"""Every module imports, and the module-level constants really build.

This exists because of a crash that reached the user. A help string in
pyTECTOR.py was written with the % operator applied to text containing a
literal per-cent sign ("0-200 %,"), which Python reads as a format specifier.
py_compile is happy with it -- the syntax is valid -- so it passed every check
that was being run, and the program then died on the first line of module-level
code with

    ValueError: unsupported format character ',' at index 204

and never opened a window. Compiling is not importing. This imports.

Importing pyTECTOR.py runs its constants and class bodies but not main(), which
sits behind the __name__ guard, so no QApplication is constructed and nothing
appears on screen.

Run:  python tests/test_import.py
"""
import importlib
import os
import pkgutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


print('1. every pytector submodule imports')
import pytector                                                   # noqa: E402
for mod in sorted(m.name for m in pkgutil.iter_modules(pytector.__path__)):
    try:
        importlib.import_module('pytector.' + mod)
        ok(True, 'pytector.%s' % mod)
    except Exception as exc:
        ok(False, 'pytector.%s -> %s: %s' % (mod, type(exc).__name__, exc))

print('\n2. the application module imports, constants and all')
try:
    app = importlib.import_module('pyTECTOR')
    ok(True, 'pyTECTOR')
except Exception as exc:
    app = None
    ok(False, 'pyTECTOR -> %s: %s' % (type(exc).__name__, exc))

if app is not None:
    print('\n3. the help strings are built, not just syntactically valid')
    for name in ('MOHR1_KEY', 'MOHR1_TIP', 'INFO1_KEY', 'INFO1_TIP'):
        v = getattr(app, name, None)
        ok(isinstance(v, str) and len(v) > 40,
           '%s is a real string (%s chars)'
           % (name, len(v) if isinstance(v, str) else '-'))
    # the specific trap: a stray %-conversion left in display text
    for name in ('MOHR1_KEY', 'INFO1_KEY'):
        v = getattr(app, name, '') or ''
        ok('%%' not in v,
           '%s carries no doubled per-cent left over from formatting' % name)

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
