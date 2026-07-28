# -*- coding: utf-8 -*-
"""Measure the exact glyphs TENSOR 5.45 draws, from the HPGL vectors.

Locating the primitive correctly matters: it is the 92-point polyline whose
points are equidistant from their centre (radius 2002 plotter units), NOT the
109-point one, which is the frame box and circle merged. Getting that wrong
rescales everything by 1.32 and leads to false conclusions.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, hpgl, tensorfile

from pytensor.archive import ROOT
def fit_circle(P):
    x, y = P[:, 0], P[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    sol, *_ = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0))
    return np.array([cx, cy]), r


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
    arch = tensorfile.parse_result_line(site.result_line)
    c, R = find_primitive(polys)
    uni = [((p - c) / R) for _pen, p in polys]

    print('=' * 72)
    print('%s   primitive radius %.0f plotter units' % (folder, R))

    # ---- stars: exactly one 11-, 9- and 7-point polyline -----------------
    for npt, nm, key in ((11, 'S1 (5-point)', 'sigma1'),
                         (9, 'S2 (4-point)', 'sigma2'),
                         (7, 'S3 (3-point)', 'sigma3')):
        cand = [q for q in uni if len(q) == npt]
        if len(cand) != 1:
            print('  %s: found %d candidates, skipped' % (nm, len(cand)))
            continue
        q = cand[0][:-1]                      # drop the repeated closing point
        ctr = q.mean(axis=0)
        v = core.vec_from_trend_plunge(*arch[key])
        vv = v if v[2] <= 0 else -v
        rr = np.sqrt(max(1.0 - (-vv[2]), 0.0))
        h = np.hypot(vv[0], vv[1])
        tx, ty = (vv[0] / h * rr, vv[1] / h * rr) if h > 1e-9 else (0.0, 0.0)

        rad = np.hypot(q[:, 0] - ctr[0], q[:, 1] - ctr[1])
        ang = np.degrees(np.arctan2(q[:, 1] - ctr[1], q[:, 0] - ctr[0]))
        o = np.argsort(ang)
        print('  %s' % nm)
        print('     centroid (%+.4f, %+.4f)  Schmidt prediction (%+.4f, %+.4f)'
              '  offset %.4f'
              % (ctr[0], ctr[1], tx, ty, np.hypot(ctr[0] - tx, ctr[1] - ty)))
        print('     outer %.4f  inner %.4f  inner/outer %.3f'
              % (rad.max(), rad.min(), rad.min() / rad.max()))
        print('     vertex angles ' + ' '.join('%6.1f' % a for a in ang[o]))
        print('     vertex radii  ' + ' '.join('%6.4f' % r for r in rad[o]))

    # ---- heavy arrows: closed polygons straddling the primitive ----------
    arrows = []
    for q in uni:
        if not (5 <= len(q) <= 12):
            continue
        rr = np.hypot(q[:, 0], q[:, 1])
        if rr.max() > 1.05 and rr.min() > 0.98:
            arrows.append(q)
    print('  %d heavy arrows' % len(arrows))
    for k, q in enumerate(arrows):
        ctr = q.mean(axis=0)
        az = np.degrees(np.arctan2(ctr[0], ctr[1])) % 360
        u = np.array([np.sin(np.radians(az)), np.cos(np.radians(az))])
        w = np.array([u[1], -u[0]])
        print('    arrow %d  n=%2d  az %6.1f  radial %.3f..%.3f  half-width %.3f'
              % (k, len(q), az, (q @ u).min(), (q @ u).max(),
                 max(abs(q @ w))))
    for key in ('sigma1', 'sigma3'):
        print('    (%s trend %.1f plunge %.1f)' % ((key,) + arch[key]))

    # ---- N and M letter strokes -----------------------------------------
    gl = []
    for q in uni:
        ctr = q.mean(axis=0)
        rr = np.hypot(*ctr)
        if not (1.05 < rr < 1.45) or len(q) > 12:
            continue
        az = np.degrees(np.arctan2(ctr[0], ctr[1]))
        if abs(az) < 30:
            gl.append((az, rr, len(q)))
    gl.sort()
    print('  north-sector strokes (azimuth, radius, npts):')
    for az, rr, n in gl:
        print('     %+7.2f  %.3f  %d' % (az, rr, n))
    print()
