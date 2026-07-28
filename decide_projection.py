# -*- coding: utf-8 -*-
"""Decide the projection without relying on blob detection.

For each candidate projection, take every predicted striae position and measure
the distance to the nearest vertex anywhere in the HPGL. The projection the
program used is the one whose predictions land on ink.

Also measures the magnetic-north tick azimuth.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl, tensorfile

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


def project(trend, plunge, kind):
    if kind == 'equal-area':
        r = np.sqrt(np.maximum(1.0 - np.sin(np.radians(plunge)), 0))
    else:
        r = np.tan(np.radians(90.0 - plunge) / 2.0)
    return np.sin(np.radians(trend)) * r, np.cos(np.radians(trend)) * r


summary = {}
for folder, datafile in (('0406-7', '0406-04'), ('L12', 'L12'),
                         ('0404-1c', '0404-01C'), ('CH-01ABE', 'CH-01ABE')):
    d = os.path.join(ROOT, folder)
    hp, df = os.path.join(d, 'HPGL'), os.path.join(d, datafile)
    if not (os.path.exists(hp) and os.path.exists(df)):
        continue
    polys, _lab, _ = hpgl.read(hp)
    site = tensorfile.read_site(df)
    c, R = primitive(polys)
    verts = np.vstack([(p - c) / R for _pen, p in polys])

    s = site.s
    sl = np.where((s[:, 2] > 0)[:, None], -s, s)
    plunge = np.degrees(np.arcsin(np.clip(-sl[:, 2], -1, 1)))
    trend = np.degrees(np.arctan2(sl[:, 0], sl[:, 1])) % 360

    print('=' * 68)
    print('%-10s %2d faults, %d HPGL vertices' % (folder, len(site), len(verts)))
    for kind in ('equal-area', 'equal-angle'):
        px, py = project(trend, plunge, kind)
        dmin = np.array([np.hypot(verts[:, 0] - px[i],
                                  verts[:, 1] - py[i]).min()
                         for i in range(len(px))])
        print('   %-12s  median %.4f   mean %.4f   90th %.4f'
              % (kind, np.median(dmin), dmin.mean(), np.percentile(dmin, 90)))
        summary.setdefault(kind, []).append(np.median(dmin))

    # magnetic north tick: short radial segment in the north sector
    segs = []
    for _pen, p in polys:
        q = (p - c) / R
        for a, b in zip(q[:-1], q[1:]):
            L = np.hypot(*(b - a))
            if not (0.04 < L < 0.25):
                continue
            mid = 0.5 * (a + b)
            rr = np.hypot(*mid)
            if not (1.0 < rr < 1.35):
                continue
            az = (np.degrees(np.arctan2(mid[0], mid[1]))) % 360
            if az > 180:
                az -= 360
            if abs(az) < 45:
                segs.append((az, rr, L))
    segs.sort()
    if segs:
        print('   north-sector ticks (azimuth of midpoint, radius, length):')
        for az, rr, L in segs:
            print('      %+7.2f   %.3f   %.3f' % (az, rr, L))

print('=' * 68)
for kind, v in summary.items():
    print('%-12s  median over sites: %.4f' % (kind, float(np.median(v))))
