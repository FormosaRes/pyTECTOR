# -*- coding: utf-8 -*-
"""Do modes A and B disagree about anything the data actually constrain?

The stress ellipsoid goes degenerate at both ends of Phi: at Phi -> 0 it is
prolate and sigma2/sigma3 swap freely, at Phi -> 1 it is oblate and
sigma1/sigma2 do. So compare the axis that IS constrained:

    Phi < 0.5   sigma1 is the well constrained one
    Phi > 0.5   sigma3 is

If A and B agree on that axis, the choice between them is a footnote rather
than a fork in the road.
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

path = sys.argv[1] if len(sys.argv) > 1 else 'pytensor_AB_comparison.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
n = np.array([int(r['n']) for r in rows])
phi = np.array([float(r['A_phi']) for r in rows])
d1 = np.array([float(r['d_s1']) for r in rows])
d3 = np.array([float(r['d_s3']) for r in rows])
dphi = np.array([abs(float(r['d_phi'])) for r in rows])

# the constrained axis, and the degenerate one, per site
well = np.where(phi < 0.5, d1, d3)
poor = np.where(phi < 0.5, d3, d1)

print('%d sites\n' % len(rows))
for lo, lab in ((0, 'all sites      '), (7, 'n >= 7         '),
                (10, 'n >= 10        '), (15, 'n >= 15        ')):
    m = n >= lo
    if not m.any():
        continue
    print('%s  well-constrained axis: median %5.1f  p90 %5.1f  max %5.1f'
          % (lab, np.median(well[m]), np.percentile(well[m], 90),
             well[m].max()))
    print('%s  degenerate axis      : median %5.1f  p90 %5.1f  max %5.1f'
          % (' ' * len(lab), np.median(poor[m]), np.percentile(poor[m], 90),
             poor[m].max()))

m = n >= 7
print('\nfor the %d sites with 7 or more faults:' % m.sum())
for thr in (5, 10, 15, 20):
    print('   well-constrained axis agrees within %2d deg on %3d of %d sites'
          ' (%.0f%%)'
          % (thr, (well[m] <= thr).sum(), m.sum(),
             100.0 * (well[m] <= thr).sum() / m.sum()))
print('   |dPhi| median %.3f, p90 %.3f' % (np.median(dphi[m]),
                                           np.percentile(dphi[m], 90)))

print('\nsites where even the constrained axis moves more than 15 deg:')
idx = np.argsort(-well)
shown = 0
for i in idx:
    if well[i] <= 15 or n[i] < 7:
        continue
    print('   %-42s n=%2d  Phi %.2f  well-axis %5.1f deg'
          % (rows[i]['site'][:42], n[i], phi[i], well[i]))
    shown += 1
    if shown >= 10:
        break
if shown == 0:
    print('   none')
