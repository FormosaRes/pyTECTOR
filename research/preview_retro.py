# -*- coding: utf-8 -*-
"""Render the stereogram in both palettes so 1991 mode can be checked without
launching Qt."""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import core, entry, invdir, plot, retro

TYPED = [('SN', '174', '74E', '62N'), ('SN', '169', '75E', '59N'),
         ('PN', '135', '85W', '80S'), ('PN', '136', '88W', '81S'),
         ('CN', '123', '42S', '89W'), ('CN', '151', '69W', '72N'),
         ('CN', '145', '62W', '50N'), ('PN', '178', '63E', '76N')]
recs = []
for t in TYPED:
    r = entry.parse_record(*t)
    r['confidence'] = r['sense'][0]
    recs.append(r)
n, s = entry.records_to_arrays(recs)
conf = [r['confidence'] for r in recs]
sides = plot.strike_slip_sign([r['dipaz'] for r in recs],
                              [r['dip'] for r in recs],
                              [r['rake'] + 180.0 for r in recs])
res = core.summary(invdir.run(n, s, n_pass=1)['T'], n, s)

for tag, pen, paper, aa, stroke in (
        ('normal', 'k', 'white', True, None),
        ('1991', retro.PLOT_PEN, retro.PLOT_PAPER, False, retro.PLOT_STROKE)):
    plot.set_palette(pen, paper, aa=aa, stroke=stroke)
    fig = plt.figure(figsize=(5.2, 6.2), facecolor=paper)
    ax = fig.add_subplot(111)
    ax.set_facecolor(paper)
    plot.plot_site(ax, n, s, res, certainty=conf, sides=sides,
                   site_code='01', header='MESURE' if tag == '1991'
                   else 'observed')
    out = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'retro_%s.png' % tag)
    fig.savefig(out, dpi=130, facecolor=paper, bbox_inches='tight')
    print('written', out)
plot.set_palette()
