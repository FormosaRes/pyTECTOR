# -*- coding: utf-8 -*-
"""Headless exercise of everything the GUI does except the Qt widgets:
typed record -> arrays -> stereogram -> inversion -> fitted panel -> HPGL out.

The GUI itself is never launched from an automated shell (a QApplication there
pops a Qt platform-plugin box and exits), so this covers the logic instead.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pytector import core, entry, hpgl, invdir, modern, plot

TYPED = [
    ('SN', '174', '74E', '62N'), ('SN', '169', '75E', '59N'),
    ('PN', '135', '85W', '80S'), ('PN', '136', '88W', '81S'),
    ('CN', '123', '42S', '89W'), ('CN', '151', '69W', '72N'),
    ('CN', '145', '62W', '50N'), ('PN', '178', '63E', '76N'),
    ('CS', '122', '87W', '124'),          # bare trend, no quadrant letter
]

print('1. parse typed records')
recs = []
for t in TYPED:
    r = entry.parse_record(*t)
    r['confidence'] = r['sense'][0]
    recs.append(r)
    print('   %-4s %-4s %-4s %-5s -> dipaz %3d  dip %2d  rake %5.1f  (%s)'
          % (t + (r['dipaz'], r['dip'], r['rake'], r['entered_as'])))

print('\n2. build vectors')
n, s = entry.records_to_arrays(recs)
assert n.shape == (len(recs), 3) and s.shape == n.shape
assert np.allclose(np.einsum('ki,ki->k', n, s), 0, atol=1e-9), 's must lie in plane'
assert np.allclose(np.linalg.norm(s, axis=1), 1, atol=1e-9)
print('   ok, %d faults, s perpendicular to n, unit length' % len(n))

print('\n3. invert both modes')
ra = invdir.run(n, s, n_pass=1)
A = core.summary(ra['T'], n, s)
rb = modern.run(n, s, n_starts=150)
B = core.summary(rb['T'], n, s)
for tag, r in (('A', A), ('B', B)):
    print('   mode %s  s1 %6.1f/%4.1f  PHI %.3f  ANG %.1f  RUP %.1f  S4 %.4f'
          % (tag, r['sigma1'][0], r['sigma1'][1], r['phi'],
             r['ANG_mean'], r['RUP_mean'], r['S4']))
assert B['S4'] <= A['S4'] + 1e-9, 'mode B should reach a lower or equal S4'

print('\n4. draw every panel the GUI draws')
conf = [r['confidence'] for r in recs]
fig = plt.figure(figsize=(15, 5.2), facecolor='white')
ax1 = fig.add_subplot(1, 3, 1)
plot.plot_site(ax1, n, s, A, certainty=conf, declination=5.0,
               site_code='01', header='mode A')
plot.annotate_result(ax1, A, n_data=len(recs))
ax2 = fig.add_subplot(1, 3, 2)
plot.plot_site(ax2, n, s, B, certainty=conf, declination=5.0,
               site_code='01', header='mode B')
plot.annotate_result(ax2, B, n_data=len(recs))
ax3 = fig.add_subplot(1, 3, 3)
plot.plot_fitted(ax3, n, ra['T'], declination=5.0, site_code='01',
                 header='fitted shear')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'gui_logic_panels.png')
fig.savefig(out, dpi=130, bbox_inches='tight', facecolor='white')
print('   written', out)

print('\n5. confidence styles and shear sense actually differ')
fig2, ax = plt.subplots(figsize=(5.4, 2.6), facecolor='white')
for row, side in ((0, +1.0), (1, -1.0)):
    for k, c in enumerate('SPC'):
        cx, cy = 0.45 * k, -0.42 * row
        plot._striae_symbol(ax, cx, cy, 1.0, 0.0, side=side, conf=c)
        if row == 0:
            ax.text(cx, 0.20, c, ha='center', va='bottom', fontsize=11)
    ax.text(-0.16, -0.42 * row, 'D' if side > 0 else 'S',
            ha='right', va='center', fontsize=10)
ax.set_xlim(-0.25, 1.15)
ax.set_ylim(-0.65, 0.32)
ax.set_aspect('equal'); ax.axis('off')
out2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'arrow_style_legend.png')
fig2.savefig(out2, dpi=200, bbox_inches='tight', facecolor='white')
print('   written', out2)

print('\n6. HPGL round trip')
w = hpgl.Writer()
t = np.linspace(0, 2 * np.pi, 361)
w.polyline(np.cos(t), np.sin(t))
for i in range(len(n)):
    for seg in plot.great_circle(n[i]):
        w.polyline(seg[:, 0], seg[:, 1])
w.label(-1.3, -1.25, 'TEST')
txt = w.dumps()
polys, labels, cmds = hpgl.parse(txt)
print('   wrote %d chars, re-read %d polylines, %d labels, commands %s'
      % (len(txt), len(polys), len(labels), ' '.join(sorted(cmds))))
assert len(polys) >= len(n), 'HPGL round trip lost geometry'
assert labels and labels[0][3] == 'TEST'

print('\nall GUI-logic checks passed')
