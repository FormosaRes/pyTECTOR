# -*- coding: utf-8 -*-
"""Per-datum diagnostics: misfit bands, and leave-one-out influence.

Run:  python tests/test_diagnose.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pytector import core, diagnose, invdir, tensorfile

from pytector.archive import ROOT

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


print('1. the bands are Angelier\'s own')
ok(diagnose.band(10.0, diagnose.ANG_BANDS) == '', 'ANG 10 is clean')
ok(diagnose.band(30.0, diagnose.ANG_BANDS) == '!', 'ANG 30 is the middle band')
ok(diagnose.band(60.0, diagnose.ANG_BANDS) == '!!', 'ANG 60 is the far band')
ok(diagnose.band(40.0, diagnose.RUP_BANDS) == '', 'RUP 40 is clean')
ok(diagnose.band(60.0, diagnose.RUP_BANDS) == '!', 'RUP 60 is the middle band')
ok(diagnose.band(90.0, diagnose.RUP_BANDS) == '!!', 'RUP 90 is the far band')

print('\n2. leave-one-out on a real site')
site = os.path.join(ROOT, '0406-7', '0406-04')
if os.path.exists(site):
    st = tensorfile.read_site(site)
    n, s = st.n, st.s
    solver = lambda a, b: invdir.run(a, b, n_pass=1)['T']      # noqa: E731
    res = core.summary(solver(n, s), n, s)
    rows = diagnose.combine(res, n, s, solver)

    ok(len(rows) == len(st), 'one row per datum (%d)' % len(rows))

    # 0406-7 carries one striation 174 degrees from the predicted shear. It is
    # the reason the site's mean ANG is 21 over all data but 15 over the subset
    # under 45, and it must land in the far band.
    worst = max(rows, key=lambda r: r['ANG'])
    ok(worst['ANG'] > 170 and worst['ang_flag'] == '!!',
       'the 174 degree outlier is found and flagged (n=%d, ANG=%.1f)'
       % (worst['i'], worst['ANG']))

    # Influence has to be measured, not assumed: check one directly by
    # dropping that datum and re-inverting.
    i = worst['i'] - 1
    keep = np.ones(len(st), bool)
    keep[i] = False
    d = core.describe(solver(n[keep], s[keep]))
    u = core.vec_from_trend_plunge(*res['sigma1'])
    v = core.vec_from_trend_plunge(*d['sigma1'])
    moved = float(np.degrees(np.arccos(min(abs(float(u @ v)), 1.0))))
    ok(abs(moved - worst['s1_move']) < 0.05,
       'reported sigma1 movement %.2f matches a direct re-inversion %.2f'
       % (worst['s1_move'], moved))

    # Fitting badly and deciding the answer are different properties, which is
    # the whole reason for the module. At this site the worst-fitting datum is
    # NOT the most influential one.
    heaviest = max(rows, key=lambda r: r['worst_move'] or 0)
    ok(heaviest['i'] != worst['i'],
       'worst fit (n=%d) and greatest influence (n=%d) are different data'
       % (worst['i'], heaviest['i']))

    drawn = [r for r in rows if r['plot_mark']]
    flagged = [r for r in rows if r['flag']]
    ok(len(drawn) < len(flagged),
       'the diagram marks fewer than the table lists (%d vs %d): ringing '
       'every imperfect datum would say nothing' % (len(drawn), len(flagged)))
    ok(all(r['plot_mark'] == '!!' for r in drawn if r['load_bearing']),
       'anything that moves an axis gets the heavy ring')
else:
    print('   archive missing, skipped')

print('\n3. too few data to leave one out')
ok(diagnose.influence(np.eye(3)[:4], np.eye(3)[:4], lambda a, b: np.eye(3))
   == [], 'under five data returns nothing rather than guessing')

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
