# -*- coding: utf-8 -*-
"""Zoom into the original HPGL around individual striae so the three arrow
styles (C / P / S confidence) can be read off, with each one labelled by the
confidence letter taken from the data record."""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl, tensorfile, plot as pplot

ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"
CONF = {'1': 'C', '2': 'P', '3': 'S'}

folder, datafile = '0406-7', '0406-04'
d = os.path.join(ROOT, folder)
polys, labels, _ = hpgl.read(os.path.join(d, 'HPGL'))
site = tensorfile.read_site(os.path.join(d, datafile))

# HPGL plotter units -> unit-circle coordinates. Fit using the primitive:
# the largest closed polyline is the circle.
best, bestr = None, -1
for pen, p in polys:
    r = (p[:, 0].max() - p[:, 0].min()) + (p[:, 1].max() - p[:, 1].min())
    if r > bestr and len(p) > 100:
        best, bestr = p, r
cx = 0.5 * (best[:, 0].max() + best[:, 0].min())
cy = 0.5 * (best[:, 1].max() + best[:, 1].min())
scale = 0.25 * ((best[:, 0].max() - best[:, 0].min())
                + (best[:, 1].max() - best[:, 1].min()))
print('primitive: centre (%.0f, %.0f) radius %.0f plotter units'
      % (cx, cy, scale))

s = site.s
X, Y = pplot.schmidt(np.where((s[:, 2] > 0)[:, None], -s, s))

# pick a few records with different confidence letters, well separated
by_conf = {}
for i, r in enumerate(site.records):
    by_conf.setdefault(CONF.get(r['code'][0], '?'), []).append(i)
print('confidence counts:', {k: len(v) for k, v in by_conf.items()})

picks = []
for c in ('C', 'P', 'S'):
    for i in by_conf.get(c, [])[:3]:
        picks.append((c, i))

fig, axes = plt.subplots(3, 3, figsize=(11, 11))
for ax, (c, i) in zip(axes.ravel(), picks):
    px, py = cx + X[i] * scale, cy + Y[i] * scale
    w = scale * 0.20
    for pen, p in polys:
        m = ((p[:, 0] > px - w) & (p[:, 0] < px + w)
             & (p[:, 1] > py - w) & (p[:, 1] < py + w))
        if m.any():
            ax.plot(p[:, 0], p[:, 1], color='k', lw=1.4)
    ax.plot([px], [py], marker='+', ms=10, color='red', mew=1.2)
    ax.set_xlim(px - w, px + w)
    ax.set_ylim(py - w, py + w)
    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title('rec %d   %s   code %s   %s'
                 % (i + 1, c, site.records[i]['code'],
                    site.records[i]['tail'][:2]), fontsize=9)
for ax in axes.ravel()[len(picks):]:
    ax.axis('off')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'arrow_styles.png')
fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
print('written:', out)
