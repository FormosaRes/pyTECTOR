# -*- coding: utf-8 -*-
"""What does the parsed HPGL actually contain?"""
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl

ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"
polys, labels, cmds = hpgl.read(os.path.join(ROOT, '0406-7', 'HPGL'))

best, score = None, -1
for _pen, p in polys:
    if len(p) < 100:
        continue
    w = (p[:, 0].max() - p[:, 0].min()) + (p[:, 1].max() - p[:, 1].min())
    if w > score:
        best, score = p, w
c = np.array([0.5 * (best[:, 0].max() + best[:, 0].min()),
              0.5 * (best[:, 1].max() + best[:, 1].min())])
R = 0.25 * ((best[:, 0].max() - best[:, 0].min())
            + (best[:, 1].max() - best[:, 1].min()))
print('primitive centre', c, 'radius %.0f' % R, ' npts', len(best))

lens = Counter()
print('\npolyline inventory (n points -> count):')
for _pen, p in polys:
    lens[len(p)] += 1
for k in sorted(lens):
    print('   %4d pts  x%d' % (k, lens[k]))

print('\nthe 12 longest polylines:')
order = sorted(range(len(polys)), key=lambda i: -len(polys[i][1]))
for i in order[:12]:
    q = (polys[i][1] - c) / R
    rr = np.hypot(q[:, 0], q[:, 1])
    print('   idx %3d  n=%4d  r %.3f..%.3f' % (i, len(q), rr.min(), rr.max()))
