# -*- coding: utf-8 -*-
"""Is the A/B disagreement concentrated where the ellipsoid is near-degenerate?

At Phi -> 1 the ellipsoid is oblate (sigma1 = sigma2), so sigma1's position in
the plane perpendicular to sigma3 is barely constrained; at Phi -> 0 it is
prolate and sigma2/sigma3 swap freely. If the explanation holds, d_sigma1
should grow with Phi while d_sigma3 stays small.
"""
import csv

import numpy as np

rows = list(csv.DictReader(open('pytensor_AB_comparison.csv',
                                encoding='utf-8-sig')))
rows = [r for r in rows if int(r['n']) >= 10]
phi = np.array([float(r['A_phi']) for r in rows])
d1 = np.array([float(r['d_s1']) for r in rows])
d3 = np.array([float(r['d_s3']) for r in rows])

print('n >= 10 sites: %d\n' % len(rows))
print(' A_Phi band     sites   median d_sigma1   median d_sigma3')
for lo, hi in ((0.0, 0.35), (0.35, 0.65), (0.65, 1.01)):
    m = (phi >= lo) & (phi < hi)
    if m.sum():
        print('  %.2f - %.2f     %2d        %6.1f            %6.1f'
              % (lo, hi, m.sum(), np.median(d1[m]), np.median(d3[m])))

print('\ncorrelation(A_Phi, d_sigma1) = %+.2f' % np.corrcoef(phi, d1)[0, 1])
print('correlation(A_Phi, d_sigma3) = %+.2f' % np.corrcoef(phi, d3)[0, 1])
