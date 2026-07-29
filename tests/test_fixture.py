# -*- coding: utf-8 -*-
"""End-to-end regression against the committed fixture. Needs NO archive.

tests/fixtures/L12-2 is a complete run of the ORIGINAL programs on a
synthetic five-fault site: the data file typed into MESURE 5.51 (the
keystroke log survives as Mesure_key.txt), inverted by TENSOR 5.45 with INVD,
NO 1, no weighting, on the user's Windows XP machine. The folder holds the
data file, INFO1, MOHR1, PLOT1 and the HPGL plot, and a photographed re-run
on 2026-07-29 reproduced the recorded 03 line digit for digit.

The site is synthetic (site 01, author PANG, no coordinates), so unlike the
field archive it can be published, and this test runs for anyone who clones
the repository.

What the original recorded:

    SOLUTION INVDIR (NO 1)  LAMBDA= 0.73     Phi 0.674 at the INVDIR stage
    SOLUTION PSIDIR         LAMBDA= 0.87  TAUMAX= 0.85
    S1= 0.77  S2= 0.16  S3=-0.94
    sigma1 254.8/20.7   sigma2 114.6/63.9   sigma3 350.7/15.3   Phi 0.645
    mean ANG 3.7   mean RUP 16.1   n = 5
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pytector import core, entry, hpgl, invdir, modern, tensorfile

FIX = os.path.join(HERE, 'fixtures', 'L12-2')

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


print('1. the reader on the fixture data file')
site = tensorfile.read_site(os.path.join(FIX, 'L12-2'))
n, s = site.n, site.s
ok(len(site) == 5, '5 records read')
ok(site.name == 'L12-2', 'site name from the file name')
# what MESURE's keystroke log says was typed, against what was stored
typed = ['CD 029 37E 201', 'CD 020 42E 205', 'CD 034 33E 207',
         'CD 025 39E 203', 'CD 022 37E 200']
worst = 0.0
for t, rec in zip(typed, site.records):
    p = entry.parse_line(t)
    ok(p['dipaz'] == rec['dipaz'] and p['dip'] == rec['dip'],
       '%s -> dip azimuth %d, dip %d' % (t, rec['dipaz'], rec['dip']))
    worst = max(worst, abs(p['rake'] - rec['rake']))
ok(worst < 1.0, 're-typing every record recovers the stored rake '
   '(worst %.2f deg)' % worst)

print('\n2. the recorded result and INFO1 fields')
arch = tensorfile.parse_result_line(site.result_line)
ok(arch is not None, 'the 03 line parses')
ok(abs(arch['phi'] - 0.645) < 1e-9, 'Phi 0.645 from the 03 line')
ok(arch['sigma1'] == (254.8, 20.7), 'sigma1 254.8/20.7 from the 03 line')
info = tensorfile.read_info_lambda(os.path.join(FIX, 'INFO1'))
ok(info.get('pass_no') == 1, 'INFO1: pass NO 1')
ok(abs(info.get('lambda_invdir', 0) - 0.73) < 1e-9, 'INFO1: LAMBDA 0.73')
mohr = tensorfile.read_mohr(os.path.join(FIX, 'MOHR1'))
ok(np.allclose(mohr['eigenvalues'], [0.772, 0.165, -0.937]),
   'MOHR1 eigenvalues 0.772 / 0.165 / -0.937')
# the PSIDIR TAUMAX the original prints is 3 / (4 sqrt(Phi^2 - Phi + 1))
taumax = 3.0 / (4.0 * np.sqrt(0.645 ** 2 - 0.645 + 1.0))
ok(abs(taumax - 0.85) < 0.005,
   'printed TAUMAX 0.85 = 3/(4 sqrt(Phi^2-Phi+1)) at Phi 0.645')

print('\n3. forward model: the recorded tensor reproduces MOHR1')
V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                     for k in ('sigma1', 'sigma2', 'sigma3')])
U, _, Wt = np.linalg.svd(V)
R = U @ Wt
est = core.estimators(R @ np.diag(mohr['eigenvalues']) @ R.T, n, s)
tab = mohr['table']
for col, name, tol in ((0, 'SIGMN', 0.002), (1, 'TAU', 0.002),
                       (2, 'TAUST', 0.002), (3, 'RUP', 0.15),
                       (4, 'ANG', 0.10)):
    err = float(np.abs(est[name if name != 'SIGMN' else 'SIGMN']
                       - tab[:, col]).max())
    ok(err <= tol, 'max |%s error| %.4f  (tol %g)' % (name, err, tol))

print('\n4. the whole pipeline, plain NO 1, no archive LAMBDA')
r = invdir.run(n, s, n_pass=1)
res = core.summary(r['T'], n, s)


def axis_diff(key):
    u = core.vec_from_trend_plunge(*res[key])
    v = core.vec_from_trend_plunge(*arch[key])
    return float(np.degrees(np.arccos(min(abs(float(u @ v)), 1.0))))


for key in ('sigma1', 'sigma2', 'sigma3'):
    d = axis_diff(key)
    ok(d <= 0.5, '%s within %.2f deg of the original' % (key, d))
ok(abs(res['phi'] - 0.645) <= 0.005, 'Phi %.3f (original 0.645)' % res['phi'])
tr = r['lambda_trace'][-1]
ok(abs(tr['lam_printed'] - 0.73) <= 0.01,
   'printed LAMBDA %.2f (original 0.73)' % tr['lam_printed'])
ok(abs(r['invdir']['phi'] - 0.674) <= 0.005,
   'INVDIR-stage Phi %.3f (INFO1 says 0.674)' % r['invdir']['phi'])
ok(abs(res['ANG_mean'] - 3.7) <= 0.2,
   'mean ANG %.1f (original 3.7)' % res['ANG_mean'])
ok(abs(res['RUP_mean'] - 16.1) <= 0.6,
   'mean RUP %.1f (original 16.1)' % res['RUP_mean'])

print('\n5. S4MIN reaches at least as low an S4 on the same criterion')
b = modern.run(n, s, n_starts=200)
s4_a = core.S4(r['T'], n, s)
s4_b = core.S4(b['T'], n, s)
ok(s4_b <= s4_a + 1e-9, 'S4MIN %.4f <= INVDIR %.4f' % (s4_b, s4_a))

print('\n6. the original HPGL sits on the geometry the plot code assumes')
polys, labels, cmds = hpgl.read(os.path.join(FIX, 'HPGL'))
best = None
for _pen, pts in polys:
    if len(pts) < 60:
        continue
    c = pts.mean(0)
    rad = np.hypot(*(pts - c).T)
    if rad.std() < 60 and (best is None or abs(rad.mean() - 2002) <
                           abs(best[1] - 2002)):
        best = (c, float(rad.mean()))
ok(best is not None and abs(best[1] - 2002) < 5,
   'primitive circle radius %.0f (expect 2002)' % (best[1] if best else -1))
allp = np.vstack([a for _pen, a in polys])
for got, want, what in ((allp[:, 0].min(), 400, 'left'),
                        (allp[:, 0].max(), 5420, 'right'),
                        (allp[:, 1].min(), 396, 'bottom'),
                        (allp[:, 1].max(), 5928, 'top')):
    ok(abs(got - want) <= 2, 'frame %-6s %5.0f (expect %d)' % (what, got, want))

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
