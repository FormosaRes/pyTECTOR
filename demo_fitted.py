# -*- coding: utf-8 -*-
"""Observed against fitted shear, so the meaning of the third panel is plain.

Site 0406-7 is the useful example: the average fit looks ordinary at
ANG = 20.9 deg, but datum 26 sits at ANG = 174 deg, so its arrow reverses
completely between the two panels.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import core, invdir, plot, tensorfile

from pytensor.archive import ROOT
site = tensorfile.read_site(os.path.join(ROOT, '0406-7', '0406-04'))
n, s = site.n, site.s
r = invdir.run(n, s, n_pass=1)
res = core.summary(r['T'], n, s)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 6.4), facecolor='white')
plot.plot_site(axes[0], n, s, res, certainty=site.confidence,
               sides=site.sides, site_code='0406-7', header='observed slip')
plot.plot_fitted(axes[1], n, r['T'], site_code='0406-7',
                 header='fitted shear, the same planes')

# mark the datum whose observed slip is nearly opposite to the prediction
worst = int(np.argmax(res['ANG']))
v = s[worst] if s[worst][2] <= 0 else -s[worst]
X, Y = plot.schmidt(v[None, :])
for ax in axes:
    ax.plot(X, Y, 'o', ms=26, markerfacecolor='none', markeredgecolor='#c0392b',
            mew=2.0, zorder=10)
axes[0].annotate('datum %d\nANG %.0f deg' % (worst + 1, res['ANG'][worst]),
                 xy=(X[0], Y[0]), xytext=(-1.15, -1.20), fontsize=10,
                 color='#c0392b',
                 arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.2))

fig.suptitle('what the third panel is: the same fault planes carrying the '
             'shear stress the solution predicts', fontsize=10, y=0.97)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'fitted_shear_explained.png')
fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
print('mean ANG %.1f deg, worst datum %d at %.1f deg'
      % (res['ANG_mean'], worst + 1, res['ANG'][worst]))
print('written:', out)
