# -*- coding: utf-8 -*-
"""Determine, from the HPGL alone:
   1. which projection TENSOR 5.45 actually uses (equal-area vs equal-angle)
   2. the magnetic declination it drew
   3. the exact star and arrow polygons

The striae dots are the reference: their orientations are known exactly from
the data file, so whichever projection puts them where the plotter put them is
the one the program used.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import core, hpgl, tensorfile

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
    return np.array([cx, cy]), r


def radius_equal_area(plunge_deg):
    return np.sqrt(1.0 - np.sin(np.radians(plunge_deg)))


def radius_equal_angle(plunge_deg):
    return np.tan(np.radians(90.0 - plunge_deg) / 2.0)


for folder, datafile in (('0406-7', '0406-04'), ('L12', 'L12')):
    d = os.path.join(ROOT, folder)
    polys, _lab, _ = hpgl.read(os.path.join(d, 'HPGL'))
    site = tensorfile.read_site(os.path.join(d, datafile))
    c, R = primitive(polys)
    uni = [(p - c) / R for _pen, p in polys]

    print('=' * 72)
    print('%s   %d faults' % (folder, len(site)))

    # --- 1. dots: small closed blobs -------------------------------------
    dots = []
    for p in uni:
        rad = np.hypot(p[:, 0] - p[:, 0].mean(), p[:, 1] - p[:, 1].mean())
        if 3 <= len(p) <= 14 and rad.max() < 0.030 and rad.max() > 0.004:
            spread = rad.max() - rad.min()
            if spread < 0.010:                      # round, not a star
                dots.append(p.mean(axis=0))
    dots = np.array(dots)
    print('  %d dot-like blobs found' % len(dots))

    s = site.s
    sl = np.where((s[:, 2] > 0)[:, None], -s, s)
    plunge = np.degrees(np.arcsin(np.clip(-sl[:, 2], -1, 1)))
    trend = np.degrees(np.arctan2(sl[:, 0], sl[:, 1])) % 360

    for name, fn in (('equal-area  (Schmidt)', radius_equal_area),
                     ('equal-angle (Wulff)  ', radius_equal_angle)):
        rr = fn(plunge)
        px = np.sin(np.radians(trend)) * rr
        py = np.cos(np.radians(trend)) * rr
        if len(dots) == 0:
            continue
        tot = 0.0
        for i in range(len(px)):
            dd = np.hypot(dots[:, 0] - px[i], dots[:, 1] - py[i])
            tot += dd.min()
        print('    %s  mean nearest-dot distance %.4f' % (name, tot / len(px)))

    # --- 2. magnetic north tick ------------------------------------------
    cands = []
    for p in uni:
        if len(p) != 2:
            continue
        r0 = np.hypot(*p[0])
        r1 = np.hypot(*p[1])
        if min(r0, r1) > 0.98 and max(r0, r1) < 1.35:
            mid = p.mean(axis=0)
            az = np.degrees(np.arctan2(mid[0], mid[1])) % 360
            if az < 60 or az > 300:
                cands.append((az, min(r0, r1), max(r0, r1)))
    cands.sort()
    print('  north-area radial ticks (azimuth, r_in, r_out):')
    for az, a, b in cands:
        print('     %6.2f   %.3f  %.3f' % (az, a, b))

    # --- 3. arrows: polygons reaching outside the primitive ---------------
    arrows = [p for p in uni
              if len(p) >= 5 and np.hypot(p[:, 0], p[:, 1]).max() > 1.05
              and np.hypot(p[:, 0], p[:, 1]).min() > 0.95 and len(p) < 30]
    print('  %d arrow polygons' % len(arrows))
    for k, p in enumerate(arrows):
        ctr = p.mean(axis=0)
        az = np.degrees(np.arctan2(ctr[0], ctr[1])) % 360
        rr = np.hypot(*ctr)
        u = np.array([np.sin(np.radians(az)), np.cos(np.radians(az))])
        w = np.array([u[1], -u[0]])
        along = p @ u
        across = p @ w
        print('    arrow %d  n=%2d  centre r=%.3f az=%6.1f  along %.3f..%.3f'
              '  across %+.3f..%+.3f'
              % (k, len(p), rr, az, along.min(), along.max(),
                 across.min(), across.max()))
    print()
