# -*- coding: utf-8 -*-
"""Decisive geometric test of the projection.

A great circle projects to a TRUE CIRCULAR ARC under the stereographic
(equal-angle, Wulff) projection, and to a non-circular curve under the
equal-area (Schmidt) projection. So fit a circle to the fault great circles in
the HPGL: a near-zero residual means stereographic.

Also locates the N and M letter glyphs to measure the declination that was
drawn.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl

ROOT = r"<PYTECTOR_ARCHIVE>"


def primitive(polys):
    best, score = None, -1
    for _pen, p in polys:
        if len(p) < 100:
            continue
        w = (p[:, 0].max() - p[:, 0].min()) + (p[:, 1].max() - p[:, 1].min())
        if w > score:
            best, score = p, w
    cx = 0.5 * (best[:, 0].max() + best[:, 0].min())
    cy = 0.5 * (best[:, 1].max() + best[:, 1].min())
    r = 0.25 * ((best[:, 0].max() - best[:, 0].min())
                + (best[:, 1].max() - best[:, 1].min()))
    return np.array([cx, cy]), r, best


def fit_circle(P):
    """Algebraic circle fit; returns (centre, radius, rms residual)."""
    x, y = P[:, 0], P[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0))
    res = np.hypot(x - cx, y - cy) - r
    return (cx, cy), r, float(np.sqrt((res ** 2).mean()))


# reference: what a fitted circle residual looks like for each projection,
# on synthetic great circles of the same dip range
def synth(dip_deg, kind, n=200):
    A, d = np.radians(30.0), np.radians(dip_deg)
    nrm = np.array([np.sin(d) * np.sin(A), np.sin(d) * np.cos(A), np.cos(d)])
    a = np.array([0., 0., 1.]) if abs(nrm[2]) < 0.95 else np.array([1., 0., 0.])
    u = np.cross(nrm, a); u /= np.linalg.norm(u)
    w = np.cross(nrm, u)
    t = np.linspace(0, 2 * np.pi, 4 * n)
    pts = np.outer(np.cos(t), u) + np.outer(np.sin(t), w)
    pts = pts[pts[:, 2] <= 0]
    pl = np.degrees(np.arcsin(np.clip(-pts[:, 2], -1, 1)))
    tr = np.degrees(np.arctan2(pts[:, 0], pts[:, 1]))
    if kind == 'equal-area':
        r = np.sqrt(np.maximum(1 - np.sin(np.radians(pl)), 0))
    else:
        r = np.tan(np.radians(90 - pl) / 2)
    return np.column_stack([np.sin(np.radians(tr)) * r,
                            np.cos(np.radians(tr)) * r])


print('reference: circle-fit rms for SYNTHETIC great circles')
for dip in (42, 62, 74, 88):
    ra = fit_circle(synth(dip, 'equal-area'))[2]
    rn = fit_circle(synth(dip, 'equal-angle'))[2]
    print('   dip %2d   equal-area rms %.5f    equal-angle rms %.5f'
          % (dip, ra, rn))

for folder in ('0406-7', 'L12', '0404-1c'):
    hp = os.path.join(ROOT, folder, 'HPGL')
    if not os.path.exists(hp):
        continue
    polys, _lab, _ = hpgl.read(hp)
    c, R, prim = primitive(polys)
    print('=' * 66)
    print(folder)

    res = []
    for _pen, p in polys:
        q = (p - c) / R
        if len(q) < 40 or len(q) > 400:
            continue
        rr = np.hypot(q[:, 0], q[:, 1])
        if rr.max() > 1.02:
            continue                       # skip the primitive itself
        if rr.max() - rr.min() < 0.15:
            continue                       # skip near-concentric stuff
        _ctr, _r, rms = fit_circle(q)
        res.append(rms)
    res = np.array(res)
    if len(res):
        print('   %d fault great circles, circle-fit rms: median %.5f  max %.5f'
              % (len(res), np.median(res), res.max()))

    # N and M glyphs: small polylines in the north sector outside the circle
    glyphs = []
    for _pen, p in polys:
        q = (p - c) / R
        ctr = q.mean(axis=0)
        rr = np.hypot(*ctr)
        if not (1.02 < rr < 1.35):
            continue
        az = np.degrees(np.arctan2(ctr[0], ctr[1]))
        if abs(az) > 40 or len(q) > 30:
            continue
        span = max(q[:, 0].max() - q[:, 0].min(), q[:, 1].max() - q[:, 1].min())
        glyphs.append((az, rr, len(q), span))
    glyphs.sort()
    print('   north-sector glyph strokes (azimuth, radius, npts, span):')
    for az, rr, n, span in glyphs:
        print('      %+7.2f  %.3f  %2d  %.3f' % (az, rr, n, span))
