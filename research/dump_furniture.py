# -*- coding: utf-8 -*-
"""Dump the exact coordinates of the frame furniture: cardinal ticks, the N and
M marks, and the centre cross. Also count over-drawn strokes, which is how a
pen plotter makes a line look heavier."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytensor import hpgl

from pytensor.archive import ROOT
def fit_circle(P):
    x, y = P[:, 0], P[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    sol, *_ = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    return np.array([cx, cy]), np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0))


def find_primitive(polys):
    best, bestcv = None, 9e9
    for _pen, p in polys:
        if len(p) < 40:
            continue
        ctr = p.mean(axis=0)
        r = np.hypot(p[:, 0] - ctr[0], p[:, 1] - ctr[1])
        cv = r.std() / max(r.mean(), 1e-9)
        if cv < bestcv:
            best, bestcv = p, cv
    return fit_circle(best)


polys, labels, _ = hpgl.read(os.path.join(ROOT, 'L12', 'HPGL'))
c, R = find_primitive(polys)
print('primitive radius %.0f plotter units\n' % R)

short = []
for i, (_pen, p) in enumerate(polys):
    q = (p - c) / R
    if len(q) > 12:
        continue
    short.append((i, q))

print('SHORT POLYLINES, grouped by where they sit')
print('(coordinates in units of the primitive radius)\n')


def describe(q):
    r = np.hypot(q[:, 0], q[:, 1])
    az = np.degrees(np.arctan2(q[:, 0], q[:, 1])) % 360
    return r, az


# cardinal ticks: segments crossing r = 1 near N/E/S/W
print('--- cardinal ticks ---')
for i, q in short:
    r, az = describe(q)
    if len(q) != 2:
        continue
    a = az.mean()
    near = min(abs(a - k) for k in (0, 90, 180, 270, 360))
    if near > 4 or r.max() < 0.9 or r.min() > 1.12:
        continue
    print('  poly %3d  az %6.2f  r %.4f -> %.4f  (length %.4f)'
          % (i, a, r[0], r[1], np.hypot(*(q[1] - q[0]))))

print('\n--- centre cross ---')
for i, q in short:
    r, _az = describe(q)
    if r.max() < 0.15 and len(q) == 2:
        print('  poly %3d  (%+.4f,%+.4f) -> (%+.4f,%+.4f)  length %.4f'
              % (i, q[0][0], q[0][1], q[1][0], q[1][1],
                 np.hypot(*(q[1] - q[0]))))

print('\n--- everything in the north sector outside the circle ---')
for i, q in short:
    r, az = describe(q)
    a = ((az.mean() + 180) % 360) - 180
    if abs(a) > 25 or r.max() < 1.0:
        continue
    print('  poly %3d  n=%d' % (i, len(q)))
    for pt in q:
        rr = np.hypot(*pt)
        aa = ((np.degrees(np.arctan2(pt[0], pt[1])) + 180) % 360) - 180
        print('       (%+.4f, %+.4f)   r=%.4f  az=%+7.2f' % (pt[0], pt[1], rr, aa))

print('\n--- duplicate strokes (same geometry drawn more than once) ---')
seen = {}
for i, q in short:
    key = tuple(np.round(q.ravel(), 3))
    seen.setdefault(key, []).append(i)
dups = {k: v for k, v in seen.items() if len(v) > 1}
print('  %d distinct short polylines, %d drawn more than once'
      % (len(seen), len(dups)))
for k, v in list(dups.items())[:10]:
    pts = np.array(k).reshape(-1, 2)
    print('     x%d  first point (%+.3f,%+.3f) r=%.3f'
          % (len(v), pts[0][0], pts[0][1], np.hypot(*pts[0])))
