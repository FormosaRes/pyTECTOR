# -*- coding: utf-8 -*-
"""Break the A/B comparison down by data-set size, so the headline number is
not dominated by 4-fault sites where 4 unknowns are barely determined."""
import csv
import sys

import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else 'pytensor_AB_comparison.csv'
rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
n = np.array([int(r['n']) for r in rows])
d1 = np.array([float(r['d_s1']) for r in rows])
dphi = np.array([abs(float(r['d_phi'])) for r in rows])
dS4 = np.array([float(r['d_S4']) for r in rows])

print('%d sites\n' % len(rows))
print('  n range        sites   sigma1 A-B (deg)        |dPhi|')
print('                         median   p90    max     median   max')
for lo, hi, lab in ((4, 6, '  4-6  '), (7, 9, '  7-9  '),
                    (10, 14, ' 10-14 '), (15, 99, '  >=15 ')):
    m = (n >= lo) & (n <= hi)
    if not m.any():
        continue
    print('  %s      %3d    %6.1f %6.1f %6.1f    %6.3f %6.3f'
          % (lab, m.sum(), np.median(d1[m]), np.percentile(d1[m], 90),
             d1[m].max(), np.median(dphi[m]), dphi[m].max()))

m = n >= 10
print('\n  sites with n >= 10 (%d): sigma1 median %.1f deg, p90 %.1f, max %.1f'
      % (m.sum(), np.median(d1[m]), np.percentile(d1[m], 90), d1[m].max()))
print('  |dPhi| median %.3f, max %.3f' % (np.median(dphi[m]), dphi[m].max()))

worse = (dS4 > 1e-9).sum()
print('\n  sites where Mode B failed to beat Mode A on S4: %d of %d'
      % (worse, len(rows)))

print('\n  largest sigma1 differences among n >= 10:')
idx = np.argsort(-d1)
shown = 0
for i in idx:
    if n[i] < 10:
        continue
    r = rows[i]
    print('    %-42s n=%2d  ds1 %5.1f  A Phi %.3f -> B %.3f'
          % (r['site'][:42], n[i], d1[i], float(r['A_phi']), float(r['B_phi'])))
    shown += 1
    if shown >= 8:
        break
