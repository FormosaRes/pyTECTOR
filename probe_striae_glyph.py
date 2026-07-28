# -*- coding: utf-8 -*-
"""Isolate the striae arrow strokes for one example of each confidence class.

Each striae symbol is: a filled dot (a 55-point spiral, radius 0.028) plus a
few short strokes that form the shaft and the head. The great circles are the
37-point polylines and are excluded.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl, plot, tensorfile

ROOT = r"<PYTECTOR_ARCHIVE>"


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


for folder, datafile in (('0406-7', '0406-04'), ('L12', 'L12')):
    d = os.path.join(ROOT, folder)
    polys, _l, _ = hpgl.read(os.path.join(d, 'HPGL'))
    site = tensorfile.read_site(os.path.join(d, datafile))
    c, R = find_primitive(polys)
    uni = [((p - c) / R) for _pen, p in polys]
    s = site.s
    X, Y = plot.schmidt(np.where((s[:, 2] > 0)[:, None], -s, s))

    # which strokes are candidates: short, and not a dot spiral
    cand = [(j, q) for j, q in enumerate(uni) if 2 <= len(q) <= 12]

    seen = set()
    print('#' * 70)
    print(folder)
    for want in ('S', 'P', 'C'):
        # pick the most isolated record of this class
        best, bestd = None, -1
        for i, rec in enumerate(site.records):
            if rec.get('confidence') != want:
                continue
            dd = [np.hypot(X[k] - X[i], Y[k] - Y[i])
                  for k in range(len(X)) if k != i]
            m = min(dd) if dd else 9.9
            if m > bestd:
                best, bestd = i, m
        if best is None:
            continue
        i = best
        px, py = X[i], Y[i]
        rec = site.records[i]
        print('=' * 66)
        print('%s   record %d   %s   nearest neighbour %.3f away'
              % (want, i + 1, rec['tail'], bestd))
        strokes = []
        for j, q in cand:
            dmin = np.hypot(q[:, 0] - px, q[:, 1] - py).min()
            if dmin > 0.22 or j in seen:
                continue
            rr = np.hypot(q[:, 0], q[:, 1])
            if rr.min() > 0.95:          # skip the heavy arrows and frame
                continue
            strokes.append((j, q, dmin))
        strokes.sort(key=lambda t: t[2])
        for j, q, dmin in strokes[:6]:
            print('   stroke %3d  n=%d  nearest %.4f' % (j, len(q), dmin))
            for pt in q:
                print('        rel (%+.4f, %+.4f)  |d| %.4f'
                      % (pt[0] - px, pt[1] - py,
                         np.hypot(pt[0] - px, pt[1] - py)))
