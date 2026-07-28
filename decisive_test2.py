# -*- coding: utf-8 -*-
"""Decisive projection test, with the primitive located properly.

A great circle projects to a TRUE circular arc under the stereographic
(equal-angle) projection and to a non-circular curve under equal-area. The
archive draws one 37-point polyline per fault, so fit circles to those.
"""
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
    r = np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0))
    return (cx, cy), r, float(np.sqrt(((np.hypot(x - cx, y - cy) - r) ** 2).mean()))


def find_primitive(polys):
    """The primitive is the long polyline whose points are most equidistant
    from their own centroid."""
    best, bestcv = None, 9e9
    for _pen, p in polys:
        if len(p) < 40:
            continue
        ctr = p.mean(axis=0)
        r = np.hypot(p[:, 0] - ctr[0], p[:, 1] - ctr[1])
        cv = r.std() / max(r.mean(), 1e-9)
        if cv < bestcv:
            best, bestcv = p, cv
    ctr, r, _ = fit_circle(best)
    return np.array(ctr), r, bestcv, len(best)


def synth(dip_deg, kind, npts=37):
    A, d = np.radians(30.0), np.radians(dip_deg)
    nrm = np.array([np.sin(d) * np.sin(A), np.sin(d) * np.cos(A), np.cos(d)])
    a = np.array([0., 0., 1.]) if abs(nrm[2]) < 0.95 else np.array([1., 0., 0.])
    u = np.cross(nrm, a); u /= np.linalg.norm(u)
    w = np.cross(nrm, u)
    t = np.linspace(0, 2 * np.pi, 8 * npts)
    pts = np.outer(np.cos(t), u) + np.outer(np.sin(t), w)
    pts = pts[pts[:, 2] <= 0]
    pl = np.degrees(np.arcsin(np.clip(-pts[:, 2], -1, 1)))
    tr = np.degrees(np.arctan2(pts[:, 0], pts[:, 1]))
    r = (np.sqrt(np.maximum(1 - np.sin(np.radians(pl)), 0))
         if kind == 'equal-area' else np.tan(np.radians(90 - pl) / 2))
    return np.column_stack([np.sin(np.radians(tr)) * r,
                            np.cos(np.radians(tr)) * r])


print('reference, synthetic great circles:')
for dip in (42, 62, 74, 88):
    print('   dip %2d   equal-area rms %.5f   equal-angle rms %.5f'
          % (dip, fit_circle(synth(dip, 'equal-area'))[2],
             fit_circle(synth(dip, 'equal-angle'))[2]))

for folder, datafile in (('0406-7', '0406-04'), ('0404-1c', '0404-01C'),
                         ('L12', 'L12')):
    hp = os.path.join(ROOT, folder, 'HPGL')
    if not os.path.exists(hp):
        continue
    polys, _l, _ = hpgl.read(hp)
    c, R, cv, npts = find_primitive(polys)
    site = tensorfile.read_site(os.path.join(ROOT, folder, datafile))
    print('=' * 64)
    print('%-9s primitive: %d pts, radial cv %.5f, radius %.0f'
          % (folder, npts, cv, R))

    arcs = [((p - c) / R) for _pen, p in polys if len(p) == 37]
    print('   %d 37-point polylines (expected %d faults)'
          % (len(arcs), len(site)))
    if not arcs:
        continue
    rms = np.array([fit_circle(q)[2] for q in arcs])
    print('   circle-fit rms: median %.5f   mean %.5f   max %.5f'
          % (np.median(rms), rms.mean(), rms.max()))
    dips = np.array([r['dip'] for r in site.records])
    exp_area = np.median([fit_circle(synth(int(d), 'equal-area'))[2]
                          for d in dips])
    print('   expected if equal-area: %.5f      if equal-angle: 0.00000'
          % exp_area)
    verdict = ('EQUAL-ANGLE (stereographic / Wulff)'
               if np.median(rms) < exp_area * 0.35 else 'EQUAL-AREA (Schmidt)')
    print('   ==> %s' % verdict)
