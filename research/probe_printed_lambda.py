# -*- coding: utf-8 -*-
"""What printed LAMBDA values are reachable at all, and is the mapping
monotonic? The bisection in lambda_for_printed assumes both."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import core, invdir, tensorfile
from pytector.archive import ROOT, require

require('probe_printed_lambda.py')

for folder, datafile in (('L12', 'L12'), ('CH-01ABE', 'CH-01ABE')):
    d = os.path.join(ROOT, folder)
    site = tensorfile.read_site(os.path.join(d, datafile))
    info = tensorfile.read_info_lambda(os.path.join(d, 'INFO1'))
    n, s = site.n, site.s
    print('=' * 70)
    print('%s   recorded LAMBDA %.2f   pass NO %s'
          % (folder, info.get('lambda_invdir', float('nan')),
             info.get('pass_no')))
    print('   solver lambda -> printed lambda      sigma1')
    prev = None
    mono = True
    for lam in (0.30, 0.5, 0.8, 1.0, 1.3, 1.63, 2.0, 2.5, 3.0, 4.0, 6.0):
        pr, T, dd, _s4 = invdir.printed_lambda(n, s, lam, n_psi=1200)
        flag = ''
        if prev is not None and pr < prev:
            flag = '  <- not monotonic'
            mono = False
        prev = pr
        print('      %5.2f          %6.3f            %5.1f /%4.1f%s'
              % (lam, pr, dd['sigma1'][0], dd['sigma1'][1], flag))
    print('   monotonic over this range: %s' % mono)
    got = invdir.lambda_for_printed(n, s, info.get('lambda_invdir', 0.76))
    print('   lambda_for_printed(%.2f) -> %s'
          % (info.get('lambda_invdir', 0.76),
             'None (target not bracketed)' if got is None else '%.4f' % got))
