# -*- coding: utf-8 -*-
"""Dump the first polylines of the L12 HPGL verbatim: these are the frame
furniture, drawn before any data."""
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
print('primitive radius %.0f\n' % R)

for i, (_pen, p) in enumerate(polys[:14]):
    q = (p - c) / R
    print('poly %2d   n=%d' % (i, len(q)))
    if len(q) > 15:
        rr = np.hypot(q[:, 0], q[:, 1])
        print('     (long) r %.4f .. %.4f' % (rr.min(), rr.max()))
        continue
    for pt in q:
        rr = np.hypot(*pt)
        aa = ((np.degrees(np.arctan2(pt[0], pt[1])) + 180) % 360) - 180
        print('     (%+.4f, %+.4f)  r=%.4f  az=%+7.2f' % (pt[0], pt[1], rr, aa))
