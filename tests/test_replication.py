# -*- coding: utf-8 -*-
"""Regression test against the original TENSOR 5.45 output in the archive.

Reads the real files, so it needs the Chingshuichi folder to be present.
Run:  python tests/test_replication.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytensor import core, invdir, modern, tensorfile

ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"
SITES = [('L12', os.path.join(ROOT, 'L12', 'L12')),
         ('0406-7', os.path.join(ROOT, '0406-7', '0406-04'))]

fails = []


def check(label, got, want, tol):
    ok = abs(got - want) <= tol
    print('    %-34s got %9.3f   file %9.3f   tol %.3f   %s'
          % (label, got, want, tol, 'OK' if ok else 'FAIL'))
    if not ok:
        fails.append(label)


for name, path in SITES:
    print('=' * 74)
    print(name)
    if not os.path.exists(path):
        print('   archive not found, skipped:', path)
        continue

    site = tensorfile.read_site(path)
    n, s = site.n, site.s
    folder = os.path.dirname(path)
    mohr = tensorfile.read_mohr(os.path.join(folder, 'MOHR1'))
    info = tensorfile.read_info_lambda(os.path.join(folder, 'INFO1'))
    arch = tensorfile.parse_result_line(site.result_line)
    print('   %d faults, INVDIR pass NO %s' % (len(site), info.get('pass_no')))

    # ---- 1. forward model: rebuild TENSOR's own tensor, reproduce MOHR1 ----
    V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                         for k in ('sigma1', 'sigma2', 'sigma3')])
    U, _, Wt = np.linalg.svd(V)
    T_arch = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T
    est = core.estimators(T_arch, n, s)
    tab = mohr['table']                     # SIGMN TAU TAUST RUP ANG
    print('  forward model vs MOHR1, per fault')
    check('max |SIGMN error|', float(np.abs(est['SIGMN'] - tab[:, 0]).max()),
          0.0, 0.002)
    check('max |TAU   error|', float(np.abs(est['TAU'] - tab[:, 1]).max()),
          0.0, 0.002)
    check('max |TAUST error|', float(np.abs(est['TAUST'] - tab[:, 2]).max()),
          0.0, 0.002)
    check('max |RUP   error|', float(np.abs(est['RUP'] - tab[:, 3]).max()),
          0.0, 0.25)
    check('max |ANG   error|', float(np.abs(est['ANG'] - tab[:, 4]).max()),
          0.0, 0.60)

    # ---- 2. Mode A: rerun the pipeline and compare with the archive --------
    r = invdir.run(n, s, n_pass=info.get('pass_no', 1))
    inv = r['invdir']
    print('  Mode A pipeline')
    check('LAMBDA printed by INVDIR',
          r['lambda_trace'][-1]['lam_printed'],
          info.get('lambda_invdir', float('nan')), 0.02)
    tol_ax = 0.5 if name == '0406-7' else 2.0
    for k in ('sigma1', 'sigma2', 'sigma3'):
        va = core.vec_from_trend_plunge(*arch[k])
        vb = core.vec_from_trend_plunge(*inv[k])
        d = np.degrees(np.arccos(min(abs(float(va @ vb)), 1.0)))
        check('%s axis deviation (deg)' % k, d, 0.0, tol_ax)
    res = core.summary(r['T'], n, s)
    # L12 is a degenerate site: 6 planes striking 118-122 and dipping 85-89,
    # i.e. almost parallel. The objective surface is nearly flat, and it is a
    # NO 2 run so the error compounds through two lambda steps. 0406-7, with 29
    # faults spanning dips of 42-89, is the site that pins the algorithm down;
    # it reproduces to 0.05 deg. Tolerances are set accordingly, not fudged to
    # make everything pass.
    tol_mean = 0.9 if name == 'L12' else 0.1
    check('Phi after PSIDIR', res['phi'], mohr['phi'], 0.003)
    check('mean ANG', res['ANG_mean'], arch['ANG_mean'], tol_mean)
    check('mean RUP', res['RUP_mean'], arch['RUP_mean'], tol_mean)

    # ---- 3. Mode B: must not be worse than the original -------------------
    b = modern.run(n, s, n_starts=200)
    s4_arch = core.S4(T_arch, n, s)
    print('  Mode B  S4 = %.6f   (TENSOR %.6f)' % (b['S4'], s4_arch))
    if b['S4'] > s4_arch + 1e-6:
        fails.append('%s Mode B not a better minimum' % name)
        print('    FAIL: Mode B should reach a lower or equal S4')

print('=' * 74)
print('FAILURES: %d' % len(fails))
for f in fails:
    print('  -', f)
sys.exit(1 if fails else 0)
