# -*- coding: utf-8 -*-
"""Check everything the GUI depends on, without constructing any Qt object.

A QApplication cannot be created from an automated shell here (it pops a Qt
platform-plugin dialog and exits), so the widgets themselves are exercised by
the user. What this test can do is verify the contract between the GUI and the
library: that every attribute and function the GUI reaches for exists and
returns what the GUI expects.
"""
import ast
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pytensor import (core, entry, invdir, modern, penrec, plot, report,
                      tensorfile, hpgl)
from pytensor.ui_style import QSS

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


print('1. stylesheet')
ok(QSS.count('{') == QSS.count('}'), 'braces balanced')
ok('font-weight: bold' not in QSS.replace('font-weight: 600', ''),
   'no bold on tabs (Qt clips the label)')
ok('QFrame#panel' in QSS and 'QFrame#plotpanel' in QSS,
   'frame borders scoped by objectName')
for name in ('heading', 'value', 'axis', 'secondary', 'seg', 'run', 'report'):
    ok('#%s' % name in QSS, 'style defined for #%s' % name)
# a stylesheet beats setFont, so the fixed-width tables need their family set
# in the QSS or they render proportional and the columns fall apart
ok('font-family' in QSS.split('QPlainTextEdit#report')[1].split('}')[0],
   'report boxes force a monospace family in the stylesheet')
ok('line-height' not in QSS, 'no line-height (Qt stylesheets ignore it)')

print('\n2. the GUI source only calls things that exist')
src = open(os.path.join(ROOT, 'pyTENSOR.py'), encoding='utf-8').read()
tree = ast.parse(src)
mods = {'core': core, 'entry': entry, 'invdir': invdir, 'modern': modern,
        'plot': plot, 'report': report, 'tensorfile': tensorfile,
        'hpgl': hpgl, 'penrec': penrec}
missing = set()
for node in ast.walk(tree):
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id in mods):
        if not hasattr(mods[node.value.id], node.attr):
            missing.add('%s.%s' % (node.value.id, node.attr))
ok(not missing, 'every pytensor attribute referenced exists %s'
   % (sorted(missing) if missing else ''))

print('\n3. the data path the GUI drives')
recs = []
for t in (('CS', '122', '87W', '124'), ('PN', '135', '85W', '80S'),
          ('CN', '145', '62W', '50N'), ('SN', '174', '74E', '62N'),
          ('CN', '151', '69W', '72N')):
    r = entry.parse_record(*t)
    r['confidence'] = r['sense'][0]
    recs.append(r)
n, s = entry.records_to_arrays(recs)
ok(n.shape == (5, 3) and s.shape == (5, 3), 'records -> arrays')
ok(np.allclose(np.einsum('ki,ki->k', n, s), 0, atol=1e-9),
   'slip lies in the fault plane')

ra = invdir.run(n, s, n_pass=1)
A = core.summary(ra['T'], n, s)
A['T'] = ra['T']
rb = modern.run(n, s, n_starts=80)
B = core.summary(rb['T'], n, s)
B['T'] = rb['T']
for key in ('sigma1', 'sigma2', 'sigma3', 'phi', 'ANG_mean', 'RUP_mean',
            'S4', 'n_rup1', 'eigenvalues'):
    ok(key in A and key in B, 'summary provides %r' % key)
ok(B['S4'] <= A['S4'] + 1e-9, 'mode B reaches a lower or equal S4')

print('\n4. plotting entry points the GUI uses')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig = plt.figure(figsize=(12, 5))
conf = [r['confidence'] for r in recs]
axp = fig.add_subplot(1, 3, 1)
plot.plot_site(axp, n, s, A, certainty=conf, site_code='01', header='mode A')
plot.annotate_result(axp, A, n_data=len(recs))
axp = fig.add_subplot(1, 3, 2)
plot.plot_site(axp, n, s, B, certainty=conf, site_code='01', header='mode B')
axp = fig.add_subplot(1, 3, 3)
plot.plot_fitted(axp, n, A['T'], site_code='01', header='fitted shear')
out = os.path.join(HERE, 'ui_contract_panels.png')
fig.savefig(out, dpi=120, facecolor='white', bbox_inches='tight')
ok(os.path.exists(out), 'three-panel figure renders -> %s' % out)

print('\n5. INFO1 / MOHR1 shown in the interface and exported')
ra2 = invdir.run(n, s, n_pass=1)
A['lambda_trace'] = ra2['lambda_trace']
A['invdir_summary'] = core.summary(ra2['T_invdir'], n, s)
info_txt = report.info1_text('DEMO', A, len(recs),
                             invdir=A['invdir_summary'],
                             lam_invdir=A['lambda_trace'][-1]['lam_printed'],
                             pass_no=1)
mohr_txt = report.mohr1_text(A, len(recs))
ok('SOLUTION INVDIR' in info_txt and 'SOLUTION PSIDIR' in info_txt,
   'INFO1 carries both solution blocks')
ok(info_txt.count('\n') > 40, 'INFO1 is a full report (%d lines)'
   % info_txt.count('\n'))
ok(len(mohr_txt.splitlines()) == len(recs) + 2,
   'MOHR1 has one row per datum plus header and result line')
back = report.result_line(A, len(recs))
ok(tensorfile.parse_result_line(back) is not None,
   'our own result line parses back with the reader')
p = tensorfile.parse_result_line(back)
ok(abs(p['phi'] - A['phi']) < 0.001, 'round trip keeps PHI')

print("\n6. HPGL export draws the whole plot, at the archive's own scale")
# The export replays plot.plot_site into a recorder, so it cannot quietly lose
# elements the way the separate, shorter routine it replaced did.
rec = penrec.Recorder()
plot.plot_site(rec, n, s, A, certainty=['C'] * len(n), site_code='01',
               header='INVDIR', reference=[(90.0, 30.0, True)])
ok(not rec.ignored, 'no Axes call was silently skipped %s'
   % (sorted(rec.ignored) if rec.ignored else ''))
polys, labels, cmds = hpgl.parse(rec.emit(hpgl.Writer()).dumps())
ok(len(polys) > 100, 'the whole figure is exported, not just the outline '
   '(%d polylines)' % len(polys))
ok(len(labels) == 3, 'site code, header and program tag all reach the file')

# The frame is the one thing at a fixed place in every archive HPGL, so its
# four edges pin both the scale and the origin. Identical to four decimals in
# all 93 archive files:  x 400 .. 5420,  y 396 .. 5928.
allpts = np.vstack([a for _pen, a in polys])
for got, want, what in ((allpts[:, 0].min(), 400, 'left'),
                        (allpts[:, 0].max(), 5420, 'right'),
                        (allpts[:, 1].min(), 396, 'bottom'),
                        (allpts[:, 1].max(), 5928, 'top')):
    ok(abs(got - want) <= 2,
       'frame %-6s at %5.0f plotter units, archive has %d' % (what, got, want))
ok('SI' in cmds and 'DI' in cmds, 'character size and direction are set')

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
