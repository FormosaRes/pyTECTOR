# -*- coding: utf-8 -*-
"""Render the archive's own HPGL plots to PNG so the drawing style can be
copied exactly. Also reports which HPGL commands the files actually use."""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import hpgl

from pytector.archive import ROOT
SITES = [('L12', os.path.join(ROOT, 'L12', 'HPGL')),
         ('0406-7', os.path.join(ROOT, '0406-7', 'HPGL'))]

fig, axes = plt.subplots(1, len(SITES), figsize=(13, 7))
if len(SITES) == 1:
    axes = [axes]

for ax, (name, path) in zip(axes, SITES):
    if not os.path.exists(path):
        ax.set_title('%s: missing' % name)
        ax.axis('off')
        continue
    polys, labels, cmds = hpgl.read(path)
    npts = sum(len(p) for _pen, p in polys)
    print('%-8s %5d polylines, %6d points, %2d labels   commands: %s'
          % (name, len(polys), npts, len(labels), ' '.join(sorted(cmds))))
    for item in labels[:12]:
        print('           label %r' % (item[3],))
    hpgl.draw(ax, polys, labels)
    ax.set_title('%s  (original TENSOR HPGL)' % name, fontsize=10)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'angelier_original_plots.png')
fig.savefig(out, dpi=140, bbox_inches='tight', facecolor='white')
print('\nwritten:', out)
