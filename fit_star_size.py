# -*- coding: utf-8 -*-
"""The star size TENSOR draws is not constant. Fit it across the archive."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl, tensorfile

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
    hp, mo = os.path.join(d, 'HPGL'), os.path.join(d, 'MOHR1')
    if not (os.path.exists(hp) and os.path.exists(mo)):
        continue
    try:
        polys, _l, _ = hpgl.read(hp)
        mohr = tensorfile.read_mohr(mo)
        c, R = find_primitive(polys)
    except Exception:
        continue
    if mohr['eigenvalues'] is None:
        continue
    uni = [((p - c) / R) for _pen, p in polys]
    sizes = {}
    for npt, tag in ((11, 'S1'), (9, 'S2'), (7, 'S3')):
        cand = [q for q in uni if len(q) == npt]
        if len(cand) == 1:
            q = cand[0][:-1]
            ctr = q.mean(axis=0)
            sizes[tag] = float(np.hypot(q[:, 0] - ctr[0],
                                        q[:, 1] - ctr[1]).max())
    if len(sizes) == 3:
        rows.append((folder, mohr['phi'], mohr['eigenvalues'], sizes))

print('%d plots measured' % len(rows))

# model:  size_i = a + (b + c*Phi) * lambda_i
A, y = [], []
for _f, phi, e, s in rows:
    for k, tag in enumerate(('S1', 'S2', 'S3')):
        A.append([1.0, e[k], e[k] * phi])
        y.append(s[tag])
A, y = np.array(A), np.array(y)
coef, *_ = np.linalg.lstsq(A, y, rcond=None)
pred = A @ coef
rms = float(np.sqrt(((y - pred) ** 2).mean()))
print('\nsize_i = %.5f + (%.5f %+.5f * PHI) * lambda_i'
      % (coef[0], coef[1], coef[2]))
print('rms %.5f over %d stars   max error %.5f'
      % (rms, len(y), float(np.abs(y - pred).max())))
print('(star sizes span %.4f to %.4f, so that rms is %.1f%% of the range)'
      % (y.min(), y.max(), 100 * rms / (y.max() - y.min())))

print('\nworst 6 plots:')
err = np.abs(y - pred).reshape(-1, 3).max(axis=1)
for i in np.argsort(-err)[:6]:
    f, phi, e, s = rows[i]
    p = pred[3 * i:3 * i + 3]
    print('   %-13s PHI %.3f   actual %.4f %.4f %.4f   fitted %.4f %.4f %.4f'
          % (f[:13], phi, s['S1'], s['S2'], s['S3'], p[0], p[1], p[2]))
