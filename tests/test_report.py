# -*- coding: utf-8 -*-
"""Regenerate INFO1 and MOHR1 and check them against the originals.

Two separate things are checked, because they can fail for different reasons:

  LAYOUT   every number must occupy exactly the same columns as in the
           original. Compared by the spans of non-space runs, so it is
           independent of the values.
  VALUES   compared numerically with a tolerance, because the test rebuilds
           TENSOR's tensor from axes the file only records to 0.1 degree, so
           the last decimal cannot match exactly. Exactness of the physics is
           covered by test_replication.py.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, report, tensorfile

ROOT = r"<PYTECTOR_ARCHIVE>"
SITES = [('L12', 'L12'), ('0406-7', '0406-04')]
NUM = re.compile(r'-?\d+\.?\d*')

fails = []


def spans(line):
    """Column spans of every run of non-space characters."""
    return [(m.start(), m.end()) for m in re.finditer(r'\S+', line)]


def compare(tag, got, want, tol):
    """Layout must be identical; numbers must agree within tol."""
    bad_layout = bad_value = 0
    for i, (a, b) in enumerate(zip(got, want)):
        if spans(a) != spans(b):
            bad_layout += 1
            if bad_layout <= 3:
                print('   %s layout differs, line %d' % (tag, i + 1))
                print('     ours %r' % a)
                print('     file %r' % b)
            continue
        na = [float(x) for x in NUM.findall(a)]
        nb = [float(x) for x in NUM.findall(b)]
        if len(na) == len(nb):
            d = max((abs(p - q) for p, q in zip(na, nb)), default=0.0)
            if d > tol:
                bad_value += 1
                if bad_value <= 3:
                    print('   %s values differ by %.3f, line %d'
                          % (tag, d, i + 1))
                    print('     ours %r' % a)
                    print('     file %r' % b)
    print('   %-6s %3d lines: %d layout, %d value mismatches'
          % (tag, len(want), bad_layout, bad_value))
    if bad_layout or bad_value:
        fails.append('%s %s' % (tag, 'layout' if bad_layout else 'values'))


for folder, datafile in SITES:
    d = os.path.join(ROOT, folder)
    if not os.path.exists(d):
        print('%s: archive missing, skipped' % folder)
        continue
    site = tensorfile.read_site(os.path.join(d, datafile))
    mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
    arch = tensorfile.parse_result_line(site.result_line)
    info = tensorfile.read_info_lambda(os.path.join(d, 'INFO1'))

    V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                         for k in ('sigma1', 'sigma2', 'sigma3')])
    U, _, Wt = np.linalg.svd(V)
    T = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T
    res = core.summary(T, site.n, site.s)

    print('=' * 74)
    print('%s   %d faults' % (folder, len(site)))

    got = report.mohr1_text(res, len(site)).splitlines()
    want = [l for l in open(os.path.join(d, 'MOHR1'),
                            errors='replace').read().splitlines() if l.strip()]
    compare('MOHR1', got, want, tol=0.35)

    txt = report.info1_text(datafile, res, len(site),
                            pass_no=info.get('pass_no', 1),
                            lam_invdir=info.get('lambda_invdir'),
                            full_header=False)
    got = txt.splitlines()
    orig = open(os.path.join(d, 'INFO1'),
                errors='replace').read().splitlines()
    start = next(i for i, l in enumerate(orig)
                 if 'FILE READY TO BE MODIFIED' in l)
    want = orig[start:]

    # the per-fault table and the summary block are the parts that must match
    def table(lines):
        out, on = [], False
        for l in lines:
            if l.startswith(' NUMERO'):
                on = True
            if on:
                out.append(l)
            if l.strip().startswith('rup:'):
                break
        return out

    # RMU is |tau| / |sigma_n|, so it blows up when the normal stress is near
    # zero: a 0.001 difference in SIGMN moves it by tens of per cent. Every
    # other column in this table is within 1.
    compare('INFO1', table(got), table(want), tol=20.0)

    # and the PSIDIR block
    def psidir(lines):
        i = next((k for k, l in enumerate(lines)
                  if 'SOLUTION PSIDIR' in l), None)
        return lines[i:i + 7] if i is not None else []

    compare('PSIDIR', psidir(got), psidir(want), tol=0.6)

    # the result line, which downstream tools parse
    def res_line(lines):
        return [l for l in lines if '03INVD' in l or '03PSID' in l]

    compare('03 line', res_line(got), res_line(want), tol=0.4)

print('=' * 74)
print('%d failures' % len(fails))
for f in fails:
    print('  -', f)
sys.exit(1 if fails else 0)
