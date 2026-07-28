# -*- coding: utf-8 -*-
"""Measure the striae symbol across the whole archive.

Each symbol is double ended: a filled dot with two opposed shafts, so it reads
as a shear couple. The head on each shaft carries the confidence:

    S  shaft only, no head
    P  shaft + one barb line
    C  shaft + a two-segment triangular head

What still needs pinning down is which SIDE the barb sits on, and whether that
side is fixed or encodes the movement sense.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl, plot, tensorfile

ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"


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


rows = []
for folder in sorted(os.listdir(ROOT)):
    d = os.path.join(ROOT, folder)
    hp = os.path.join(d, 'HPGL')
    if not os.path.exists(hp):
        continue
    data = [f for f in os.listdir(d)
            if '.' not in f and f not in ('INFO1', 'MOHR1', 'PLOT1', 'HPGL')]
    if not data:
        continue
    try:
        polys, _l, _ = hpgl.read(hp)
        site = tensorfile.read_site(os.path.join(d, data[0]))
        c, R = find_primitive(polys)
    except Exception:
        continue
    uni = [((p - c) / R) for _pen, p in polys]
    shafts = [q for q in uni if len(q) == 2]
    heads2 = [q for q in uni if len(q) == 3]

    s = site.s
    sl = np.where((s[:, 2] > 0)[:, None], -s, s)
    X, Y = plot.schmidt(sl)

    for i, rec in enumerate(site.records):
        px, py = X[i], Y[i]
        # horizontal projection of hanging wall motion, the symbol's axis
        hx, hy = s[i][0], s[i][1]
        h = np.hypot(hx, hy)
        if h < 1e-9:
            continue
        u = np.array([hx / h, hy / h])
        w = np.array([-u[1], u[0]])                # rotate +90
        # shafts of this symbol: 2-point strokes starting at the dot edge
        mine = []
        for q in shafts:
            d0 = np.hypot(q[0][0] - px, q[0][1] - py)
            d1 = np.hypot(q[1][0] - px, q[1][1] - py)
            near, far = (q[0], q[1]) if d0 < d1 else (q[1], q[0])
            if not (0.015 < min(d0, d1) < 0.040):
                continue
            if not (0.09 < max(d0, d1) < 0.20):
                continue
            mine.append((near, far))
        if len(mine) != 2:
            continue
        L = np.mean([np.hypot(*(f - n)) for n, f in mine])
        start = np.mean([np.hypot(n[0] - px, n[1] - py) for n, f in mine])
        # is the pair really opposed?
        d1 = mine[0][1] - mine[0][0]
        d2 = mine[1][1] - mine[1][0]
        opp = float(np.dot(d1, d2) / (np.linalg.norm(d1) * np.linalg.norm(d2)))

        # head strokes hanging off a tip
        side = None
        for n_, f_ in mine:
            uu = (f_ - n_) / np.linalg.norm(f_ - n_)
            ww = np.array([-uu[1], uu[0]])
            for q in heads2:
                if np.hypot(q[-1][0] - f_[0], q[-1][1] - f_[1]) < 0.006:
                    b = q[1] - f_
                    side = float(b @ ww)
                    break
            if side is not None:
                break

        rows.append(dict(site=folder, i=i + 1,
                         conf=rec.get('confidence'),
                         mv=(rec['tail'][1:2] or '?').upper(),
                         L=L, start=start, opp=opp, side=side))

print('%d symbols measured\n' % len(rows))
import collections
by = collections.Counter((r['conf'], r['mv']) for r in rows)
print('class counts (confidence, movement):')
for k in sorted(by):
    print('   %s %s   %3d' % (k[0], k[1], by[k]))

opp = np.array([r['opp'] for r in rows])
print('\nthe two shafts are opposed: cos(angle) median %.4f  worst %.4f'
      % (np.median(opp), opp.max()))
LL = np.array([r['L'] for r in rows])
st = np.array([r['start'] for r in rows])
print('shaft length  median %.4f  sd %.4f' % (np.median(LL), LL.std()))
print('shaft starts at radius %.4f (dot radius is 0.028)' % np.median(st))

print('\nbarb side, by movement type (positive = +90 deg from the shaft):')
for mv in sorted({r['mv'] for r in rows}):
    v = [r['side'] for r in rows if r['mv'] == mv and r['side'] is not None]
    if not v:
        continue
    v = np.array(v)
    print('   %s   n=%3d   median %+.4f   %d positive, %d negative'
          % (mv, len(v), np.median(v), (v > 0).sum(), (v < 0).sum()))
