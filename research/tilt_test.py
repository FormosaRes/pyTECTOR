# -*- coding: utf-8 -*-
"""Incremental restoration on a real site: before, after, and everything in
between, with both diagnostics plotted against the fraction restored."""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, invdir, plot, rotate, tensorfile, tilt
from pytensor.archive import ROOT, require

require('tilt_test.py')

SITE = sys.argv[1] if len(sys.argv) > 1 else '0404-4C-2'
DATA = sys.argv[2] if len(sys.argv) > 2 else '0404-4C'
#: reference plane, dip azimuth / dip. The archive rotated this site about a
#: horizontal axis at 020, so a plane dipping 110/20 is the equivalent surface.
REF_DIPAZ, REF_DIP = 110.0, 20.0

d = os.path.join(ROOT, SITE)
site = tensorfile.read_site(os.path.join(d, DATA))
n, s = site.n, site.s
print('%s, %d faults' % (SITE, len(site)))

t, p, a = rotate.restores_to_horizontal(REF_DIPAZ, REF_DIP)
print('reference plane %03.0f/%02.0f  ->  axis %03.0f/%02.0f, angle %+.0f'
      % (REF_DIPAZ, REF_DIP, t, p, a))


def run(nn, ss):
    return invdir.run(nn, ss, n_pass=1)['T']


rows = tilt.sweep(n, s, t, p, a, run)
print()
for line in tilt.summarise(rows):
    print('   ' + line)

print('\n  frac  angle   ANG   RUP    PHI   sigma1      sigma2      sigma3'
      '     Anders  regime')
for r in rows[::2]:
    print('  %4.2f  %+5.1f  %5.1f %5.0f  %.3f  %5.1f/%4.1f %5.1f/%4.1f'
          ' %5.1f/%4.1f  %5.1f  %s'
          % (r['fraction'], r['angle'], r['ANG'], r['RUP'], r['phi'],
             r['sigma1'][0], r['sigma1'][1], r['sigma2'][0], r['sigma2'][1],
             r['sigma3'][0], r['sigma3'][1], r['andersonian'], r['regime']))

# ---------------------------------------------------------------- figure ---
fig = plt.figure(figsize=(13.5, 8.6), facecolor='white')

def ref_after(angle):
    """The reference surface carried through a partial restoration."""
    nv = core.normal_from_dipaz(REF_DIPAZ, REF_DIP)
    nv = rotate.rotate_vectors(np.atleast_2d(nv), t, p, angle)[0]
    return plot.reference_from_vectors(nv)


ax0 = fig.add_subplot(2, 3, 1)
res0 = core.summary(run(n, s), n, s)
plot.plot_site(ax0, n, s, res0, certainty=site.confidence, sides=site.sides,
               site_code=site.name, header='as measured',
               reference=(REF_DIPAZ, REF_DIP))
plot.annotate_result(ax0, res0, n_data=len(site))

nr, sr = rotate.rotate_site(n, s, t, p, a)
ax1 = fig.add_subplot(2, 3, 2)
res1 = core.summary(run(nr, sr), nr, sr)
plot.plot_site(ax1, nr, sr, res1, certainty=site.confidence,
               sides=site.sides, site_code=site.name,
               header='fully restored %s' % rotate.describe(t, p, a),
               reference=ref_after(a))
plot.annotate_result(ax1, res1, n_data=len(site))

b = tilt.best(rows, 'ANG')
nb, sb = rotate.rotate_site(n, s, t, p, b['angle'])
ax2 = fig.add_subplot(2, 3, 3)
plot.plot_site(ax2, nb, sb, b['result'], certainty=site.confidence,
               sides=site.sides, site_code=site.name,
               header='best fit at %.0f %%' % (100 * b['fraction']),
               reference=ref_after(b['angle']))
plot.annotate_result(ax2, b['result'], n_data=len(site))

f = np.array([r['fraction'] for r in rows]) * 100
axa = fig.add_subplot(2, 1, 2)
axa.plot(f, [r['ANG'] for r in rows], 'o-', color='#23324A', lw=1.6, ms=4,
         label='mean ANG, the fit')
axa.plot(f, [r['andersonian'] for r in rows], 's-', color='#8A5A00', lw=1.6,
         ms=4, label='Andersonian misfit, 0 = one axis vertical')
axa.axvline(100, color='0.7', lw=1.0, ls='--')
axa.text(100, axa.get_ylim()[1], ' full restoration', va='top', fontsize=9,
         color='0.45')
axa.axvline(100 * b['fraction'], color='#23324A', lw=1.0, ls=':')
axa.set_xlabel('per cent of the rotation removed')
axa.set_ylabel('degrees')
axa.legend(fontsize=9, frameon=False)
axa.grid(alpha=0.25)
for side in ('top', 'right'):
    axa.spines[side].set_visible(False)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'tilt_test.png')
fig.savefig(out, dpi=125, bbox_inches='tight', facecolor='white')
print('\nwritten', out)
