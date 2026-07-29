# -*- coding: utf-8 -*-
"""Does adopting the archive's recorded LAMBDA close the L12 gap?

Re-deriving lambda from scratch lands about a degree away on L12 with a
slightly worse S4, because that site is six near-parallel near-vertical planes
and the pass-1 surface is nearly flat. Reading LAMBDA out of the site's own
INFO1 and solving for the solver lambda that prints it should reproduce the
historical run instead.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import core, invdir, tensorfile
from pytector.archive import ROOT, require

require('check_archive_lambda.py')

for folder, datafile in (('L12', 'L12'), ('0406-7', '0406-04'),
                         ('0404-1c', '0404-01C'), ('CH-01ABE', 'CH-01ABE')):
    d = os.path.join(ROOT, folder)
    if not os.path.isdir(d):
        continue
    site = tensorfile.read_site(os.path.join(d, datafile))
    mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
    arch = tensorfile.parse_result_line(site.result_line)
    info = tensorfile.read_info_lambda(os.path.join(d, 'INFO1'))
    n, s = site.n, site.s

    V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                         for k in ('sigma1', 'sigma2', 'sigma3')])
    U, _, Wt = np.linalg.svd(V)
    T_old = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T
    s4_old = core.S4(T_old, n, s)
    v_old = core.vec_from_trend_plunge(*arch['sigma1'])

    npass = info.get('pass_no', 1)
    lam_rec = info.get('lambda_invdir')

    print('=' * 76)
    print('%-9s %2d faults, INVDIR pass NO %d, recorded LAMBDA %.2f'
          % (folder, len(site), npass, lam_rec if lam_rec else float('nan')))
    print('   TENSOR    sigma1 %5.1f/%4.1f   Phi %.3f   S4 %.6f'
          % (arch['sigma1'][0], arch['sigma1'][1], mohr['phi'], s4_old))

    for label, kw in (('re-derived', {}),
                      ('archive LAMBDA', {'lam_printed': lam_rec})):
        if kw.get('lam_printed') is None and label != 're-derived':
            continue
        r = invdir.run(n, s, n_pass=npass, **kw)
        res = core.summary(r['T'], n, s)
        v = core.vec_from_trend_plunge(*res['sigma1'])
        dev = np.degrees(np.arccos(min(abs(float(v @ v_old)), 1.0)))
        print('   %-14s sigma1 %5.1f/%4.1f   Phi %.3f   S4 %.6f'
              '   off by %.2f deg   (S4 %+.4f)'
              % (label, res['sigma1'][0], res['sigma1'][1], res['phi'],
                 core.S4(r['T'], n, s), dev,
                 core.S4(r['T'], n, s) - s4_old))
