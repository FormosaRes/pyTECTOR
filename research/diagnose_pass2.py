# -*- coding: utf-8 -*-
"""L12 needs a second INVDIR pass, and pyTECTOR lands 1 degree off with a
slightly WORSE S4. 0406-7, which needs only one pass, reproduces to 0.05
degrees. So the residual is in what lambda is carried into pass 2.

Scan lambda directly and see which value reproduces the recorded axes.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import core, invdir, tensorfile
from pytector.archive import ROOT, require

require('diagnose_pass2.py')
d = os.path.join(ROOT, 'L12')
site = tensorfile.read_site(os.path.join(d, 'L12'))
mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
arch = tensorfile.parse_result_line(site.result_line)
n, s = site.n, site.s

V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                     for k in ('sigma1', 'sigma2', 'sigma3')])
U, _, Wt = np.linalg.svd(V)
T_old = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T
tgt = core.summary(T_old, n, s)
v_tgt = core.vec_from_trend_plunge(*tgt['sigma1'])

print('target: sigma1 %.1f/%.1f  Phi %.3f  S4 %.6f'
      % (tgt['sigma1'][0], tgt['sigma1'][1], tgt['phi'],
         core.S4(T_old, n, s)))

# what does pass 1 hand over?
T1, s4_1, psi1, p1 = invdir.invdir_pass(n, s, np.sqrt(3) / 2)
d1 = core.describe(T1)
scale1 = np.sqrt(1.5 / float((d1['eigenvalues'] ** 2).sum()))
print('\npass 1 at lambda = %.4f' % (np.sqrt(3) / 2))
print('   raw taumax %.4f   -> pyTECTOR carries this into pass 2'
      % d1['taumax'])
print('   the same rescaled onto the normalised tensor: %.4f'
      % (d1['taumax'] * scale1))
print('   lambda printed by pyTECTOR for pass 2: %.2f'
      % ((np.sqrt(3) / 2) * scale1))
print('   lambda printed by TENSOR:              0.76')

print('\nscanning the lambda used in pass 2')
print('  lambda    sigma1        Phi     S4        deviation from target')
best = None
for lam in np.arange(0.60, 1.35, 0.01):
    T, s4, psi, p = invdir.invdir_pass(n, s, lam)
    r = core.describe(T)
    v = core.vec_from_trend_plunge(*r['sigma1'])
    dev = np.degrees(np.arccos(min(abs(float(v @ v_tgt)), 1.0)))
    if best is None or dev < best[0]:
        best = (dev, lam, r, core.S4(T, n, s))
    if abs(lam - round(lam, 2)) < 1e-9 and int(round(lam * 100)) % 5 == 0:
        print('   %.2f    %5.1f /%4.1f   %.3f   %.6f   %5.2f deg'
              % (lam, r['sigma1'][0], r['sigma1'][1], r['phi'],
                 core.S4(T, n, s), dev))

dev, lam, r, s4 = best
print('\nclosest: lambda %.3f gives sigma1 %.1f/%.1f, Phi %.3f, S4 %.6f,'
      ' %.2f deg off' % (lam, r['sigma1'][0], r['sigma1'][1], r['phi'],
                         s4, dev))
