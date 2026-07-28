# -*- coding: utf-8 -*-
"""Is pyTENSOR's L12 answer wrong, or just a different point on a flat surface?

The test is not "do the numbers match" but "which solution sits lower on the
criterion both programs claim to minimise". If ours is lower or equal, ours is
a valid answer to the same question and the difference is where two solvers
land, not an arithmetic error.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, invdir, tensorfile
from pytensor.archive import ROOT, require

require('compare_L12_runs.py')
d = os.path.join(ROOT, 'L12')
site = tensorfile.read_site(os.path.join(d, 'L12'))
mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
arch = tensorfile.parse_result_line(site.result_line)
n, s = site.n, site.s

# TENSOR's own tensor, rebuilt from what it recorded
V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                     for k in ('sigma1', 'sigma2', 'sigma3')])
U, _, Wt = np.linalg.svd(V)
T_old = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T

r = invdir.run(n, s, n_pass=2)
T_new = r['T']

print('S4, the quantity both programs minimise (lower is a better fit)')
print('   TENSOR 5.45 : %.6f' % core.S4(T_old, n, s))
print('   pyTENSOR    : %.6f' % core.S4(T_new, n, s))
print()

a = core.summary(T_old, n, s)
b = core.summary(T_new, n, s)
print('%-14s %-18s %-18s %s' % ('', 'TENSOR 5.45', 'pyTENSOR', 'difference'))
for k, nm in (('sigma1', 'sigma1'), ('sigma2', 'sigma2'), ('sigma3', 'sigma3')):
    va = core.vec_from_trend_plunge(*a[k])
    vb = core.vec_from_trend_plunge(*b[k])
    dd = np.degrees(np.arccos(min(abs(float(va @ vb)), 1.0)))
    print('%-14s %6.1f /%5.1f     %6.1f /%5.1f     %5.2f deg'
          % (nm, a[k][0], a[k][1], b[k][0], b[k][1], dd))
print('%-14s %-18.3f %-18.3f %+.3f' % ('Phi', a['phi'], b['phi'],
                                       b['phi'] - a['phi']))
print('%-14s %-18.1f %-18.1f %+.1f' % ('mean ANG', a['ANG_mean'],
                                       b['ANG_mean'],
                                       b['ANG_mean'] - a['ANG_mean']))
print('%-14s %-18.1f %-18.1f %+.1f' % ('mean RUP', a['RUP_mean'],
                                       b['RUP_mean'],
                                       b['RUP_mean'] - a['RUP_mean']))

print('\nwhy RMU moves so much: it is |tau| / |sigma_n|, and sigma_n is small')
print('  fault   SIGMN old   SIGMN new    RMU old   RMU new')
for i in range(len(n)):
    print('   %d      %7.3f     %7.3f     %6.0f    %6.0f'
          % (i + 1, a['SIGMN'][i], b['SIGMN'][i], a['RMU'][i], b['RMU'][i]))

print('\nhow flat is the surface here? S4 along the line between the two')
for t in np.linspace(0, 1, 6):
    Tm = (1 - t) * T_old + t * T_new
    w = np.linalg.eigvalsh(Tm)
    Tm = Tm * np.sqrt(1.5 / (w ** 2).sum())
    print('   %.1f of the way across: S4 %.6f' % (t, core.S4(Tm, n, s)))
