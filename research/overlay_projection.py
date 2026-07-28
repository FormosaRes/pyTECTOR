# -*- coding: utf-8 -*-
"""Overlay both candidate projections on the original HPGL. Whichever set of
markers lands on the plotted dots and stars is the projection TENSOR uses."""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, hpgl, tensorfile

from pytensor.archive import ROOT
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
    if kind == 'area':
        r = np.sqrt(np.maximum(1.0 - np.sin(np.radians(plunge)), 0))
    else:
        r = np.tan(np.radians(90.0 - plunge) / 2.0)
    return np.sin(np.radians(trend)) * r, np.cos(np.radians(trend)) * r


fig, axes = plt.subplots(1, 2, figsize=(15, 8))

for ax, (folder, datafile) in zip(axes, (('0406-7', '0406-04'),
                                         ('L12', 'L12'))):
    d = os.path.join(ROOT, folder)
    polys, _lab, _ = hpgl.read(os.path.join(d, 'HPGL'))
    site = tensorfile.read_site(os.path.join(d, datafile))
    arch = tensorfile.parse_result_line(site.result_line)
    c, R = primitive(polys)

    for _pen, p in polys:
        q = (p - c) / R
        ax.plot(q[:, 0], q[:, 1], color='0.35', lw=0.7, zorder=1)

    s = site.s
    sl = np.where((s[:, 2] > 0)[:, None], -s, s)
    plunge = np.degrees(np.arcsin(np.clip(-sl[:, 2], -1, 1)))
    trend = np.degrees(np.arctan2(sl[:, 0], sl[:, 1])) % 360

    for kind, col, mk in (('area', 'red', 'o'), ('angle', 'blue', 's')):
        x, y = project(trend, plunge, kind)
        ax.plot(x, y, mk, ms=9, markerfacecolor='none', markeredgecolor=col,
                mew=1.6, zorder=5,
                label='striae, equal-%s' % ('area' if kind == 'area' else 'angle'))
        ax_pts = []
        for key in ('sigma1', 'sigma2', 'sigma3'):
            tr, pl = arch[key]
            ax_pts.append(project(tr, pl, kind))
        ax_pts = np.array(ax_pts)
        ax.plot(ax_pts[:, 0], ax_pts[:, 1], 'P', ms=15,
                markerfacecolor='none', markeredgecolor=col, mew=2.2, zorder=6)

    ax.set_title('%s   red circle = equal-area,  blue square = equal-angle\n'
                 '(big plus = stress axes)' % folder, fontsize=10)
    ax.set_aspect('equal')
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.axis('off')
    ax.legend(loc='lower left', fontsize=8)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'projection_overlay.png')
fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
print('written:', out)
