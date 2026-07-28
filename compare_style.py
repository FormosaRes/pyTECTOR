# -*- coding: utf-8 -*-
"""Side by side: the original TENSOR HPGL against pyTENSOR's rendering of the
same site with the same solution. This is the acceptance test for the drawing
style."""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import core, hpgl, plot, tensorfile

ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"
SITES = [('L12', 'L12', 'L12', 5.0), ('0406-7', '0406-04', '0406-7', 6.9)]

fig, axes = plt.subplots(2, len(SITES), figsize=(12.5, 12.6))

for col, (folder, datafile, label, decl) in enumerate(SITES):
    d = os.path.join(ROOT, folder)
    hp = os.path.join(d, 'HPGL')
    site = tensorfile.read_site(os.path.join(d, datafile))
    mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
    arch = tensorfile.parse_result_line(site.result_line)

    ax = axes[0][col]
    if os.path.exists(hp):
        polys, labels, _ = hpgl.read(hp)
        hpgl.draw(ax, polys, labels)
    ax.set_title('%s   original TENSOR 5.45' % label, fontsize=10)

    V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                         for k in ('sigma1', 'sigma2', 'sigma3')])
    U, _, Wt = np.linalg.svd(V)
    T = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T
    res = core.summary(T, site.n, site.s)

    ax = axes[1][col]
    plot.plot_site(ax, site.n, site.s, res, certainty=site.confidence,
                   sides=site.sides, declination=decl,
                   site_code='01', header=label, program='pyTENSOR')
    plot.annotate_result(ax, res, n_data=len(site))
    ax.set_title('%s   pyTENSOR, same tensor' % label, fontsize=10)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style_check.png')
fig.savefig(out, dpi=135, bbox_inches='tight', facecolor='white')
print('written:', out)
