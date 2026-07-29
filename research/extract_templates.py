# -*- coding: utf-8 -*-
"""Pull out the exact arrow polygon template, and work out the rule that sets
the star sizes, by measuring many archive plots at once."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import core, hpgl, tensorfile

from pytector.archive import ROOT
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


# ---------------------------------------------------------- arrow template --
d = os.path.join(ROOT, 'L12')
polys, _l, _ = hpgl.read(os.path.join(d, 'HPGL'))
site = tensorfile.read_site(os.path.join(d, 'L12'))
arch = tensorfile.parse_result_line(site.result_line)
c, R = find_primitive(polys)
uni = [((p - c) / R) for _pen, p in polys]

print('ARROW TEMPLATES (outermost outline of each filled arrow)')
groups = {}
for q in uni:
    if len(q) != 8:
        continue
    rr = np.hypot(q[:, 0], q[:, 1])
    if rr.max() < 1.05 or rr.min() < 0.98:
        continue
    ctr = q.mean(axis=0)
    az = round(float(np.degrees(np.arctan2(ctr[0], ctr[1])) % 360), 1)
    span = rr.max() - rr.min()
    if az not in groups or span > groups[az][0]:
        groups[az] = (span, q)

for key, nm in (('sigma1', 'sigma1 (compression, expect inward)'),
                ('sigma3', 'sigma3 (extension, expect outward)')):
    tr = arch[key][0]
    print('\n  %s   trend %.1f  plunge %.1f' % (nm, arch[key][0], arch[key][1]))
    for az in sorted(groups):
        if min(abs(az - tr), abs(az - (tr + 180) % 360)) > 3:
            continue
        _span, q = groups[az]
        u = np.array([np.sin(np.radians(az)), np.cos(np.radians(az))])
        w = np.array([u[1], -u[0]])
        along, across = q @ u, q @ w
        o = np.argsort(np.arctan2(across, along - along.mean()))
        print('    azimuth %6.1f' % az)
        print('      radial  ' + ' '.join('%6.3f' % v for v in along[o]))
        print('      lateral ' + ' '.join('%+6.3f' % v for v in across[o]))
        tip = along[np.argmax(np.abs(across) < 0.01)]
        print('      the narrow end (the point) sits at radius %.3f'
              % along[np.argmin(np.abs(across))])

# ------------------------------------------------------------- star sizes --
print('\n\nSTAR SIZE vs EIGENVALUE across the archive')
print(' site        n   PHI     lam1   lam2   lam3    S1size S2size S3size')
rows = []
for folder in sorted(os.listdir(ROOT)):
    d = os.path.join(ROOT, folder)
    hp, mo = os.path.join(d, 'HPGL'), os.path.join(d, 'MOHR1')
    if not (os.path.exists(hp) and os.path.exists(mo)):
        continue
    data = [f for f in os.listdir(d)
            if '.' not in f and f not in ('INFO1', 'MOHR1', 'PLOT1', 'HPGL')]
    if not data:
        continue
    try:
        polys, _l, _ = hpgl.read(hp)
        mohr = tensorfile.read_mohr(mo)
        site = tensorfile.read_site(os.path.join(d, data[0]))
        c, R = find_primitive(polys)
    except Exception:
        continue
    uni = [((p - c) / R) for _pen, p in polys]
    sizes = {}
    for npt, tag in ((11, 'S1'), (9, 'S2'), (7, 'S3')):
        cand = [q for q in uni if len(q) == npt]
        if len(cand) != 1:
            continue
        q = cand[0][:-1]
        ctr = q.mean(axis=0)
        sizes[tag] = float(np.hypot(q[:, 0] - ctr[0], q[:, 1] - ctr[1]).max())
    if len(sizes) != 3 or mohr['eigenvalues'] is None:
        continue
    e = mohr['eigenvalues']
    rows.append((folder, len(site), mohr['phi'], e, sizes))
    print(' %-11s %2d  %.3f  %+.3f %+.3f %+.3f   %.4f %.4f %.4f'
          % (folder[:11], len(site), mohr['phi'], e[0], e[1], e[2],
             sizes['S1'], sizes['S2'], sizes['S3']))

if len(rows) >= 3:
    lam, siz = [], []
    for _f, _n, _p, e, s in rows:
        lam.extend(list(e))
        siz.extend([s['S1'], s['S2'], s['S3']])
    lam, siz = np.array(lam), np.array(siz)
    A = np.column_stack([np.ones(len(lam)), lam])
    coef, *_ = np.linalg.lstsq(A, siz, rcond=None)
    pred = A @ coef
    print('\n  global fit  size = %.5f + %.5f * lambda' % (coef[0], coef[1]))
    print('  residual rms %.5f over %d stars' % (np.sqrt(((siz - pred) ** 2).mean()),
                                                 len(siz)))
    for tag, idx in (('S1', 0), ('S2', 1), ('S3', 2)):
        s = np.array([r[4][tag] for r in rows])
        print('  %s: mean size %.4f  sd %.4f' % (tag, s.mean(), s.std()))
