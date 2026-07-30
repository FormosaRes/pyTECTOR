# -*- coding: utf-8 -*-
"""Axial statistics behave as axial statistics, not directional ones.

The whole reason this module exists rather than a call to a mean() is that
orientation data is bidirectional. These tests pin the cases where treating it
as directional gives the wrong answer.

Run:  python tests/test_rose.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pytector import rose

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


print('1. an axis is the same axis read from either end')
a = rose.axial_stats([20, 200])
ok(a is not None and abs(a['R'] - 1.0) < 1e-9,
   'R = 1 for 020 and 200 (a directional mean would give 0)')
ok(abs(a['mean'] - 20.0) < 1e-6, 'mean comes back as 020, not 110')

b = rose.axial_stats([20, 20, 20])
ok(abs(b['R'] - 1.0) < 1e-9 and abs(b['mean'] - 20) < 1e-9,
   'three parallel axes: R = 1, mean 020')

print('\n2. perpendicular axes have no preferred direction')
c = rose.axial_stats([0, 90])
ok(c['R'] < 1e-6, 'R collapses to 0')
ok(c['sd'] is None,
   'no standard deviation is reported rather than a meaningless 247 deg')

print('\n3. the mean wraps correctly through north')
d = rose.axial_stats([350, 10])
ok(abs(d['mean'] - 0.0) < 1e-6 or abs(d['mean'] - 180.0) < 1e-6,
   'mean of 350 and 010 is 000, not 180')

print('\n4. fewer than two values is not a statistic')
ok(rose.axial_stats([]) is None, 'empty returns None')
ok(rose.axial_stats([45]) is None, 'a single axis returns None')

print('\n5. the histogram is symmetric and counts both ends')
edges, counts = rose.histogram([20], bin_deg=10)
ok(sum(counts) == 2, 'one axis contributes two counts')
ok(counts[2] == 1 and counts[20] == 1,
   'bins at 020 and 200 both filled')
ok(len(edges) == 36, '36 bins at 10 degrees')

print('\n6. steep axes are dropped, not silently averaged')
trends, dropped = rose.shallow_only(
    [(10, 5), (20, 80), (30, 44), (40, 45)])
ok(trends == [10, 30], 'kept only the two under 45 deg')
ok(dropped == 2, 'reported both drops, including exactly 45')

print('\n7. pick_readable finds the axis that actually has data')
groups = {
    'sigma1': [(10, 70), (20, 75), (30, 80)],      # all too steep
    'sigma3': [(100, 5), (110, 8), (105, 3)],      # all usable
}
ok(rose.pick_readable(groups) == 'sigma3',
   'an all-steep axis loses to a shallow one')

groups2 = {
    'a': [(10, 5), (80, 5)],       # usable but scattered
    'b': [(10, 5), (12, 5)],       # usable and tight
}
ok(rose.pick_readable(groups2) == 'b',
   'equal counts: the tighter set wins on R')

print('\n8. drawing returns the same statistics it labelled')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
st = rose.plot_rose(ax, [(20, 10), (25, 12), (200, 8)], title='test')
ok(st is not None and st['n'] == 3, 'all three shallow axes used')
ok(abs(st['R'] - 1.0) < 0.02,
   'the 200 datum reinforced the 020 pair instead of cancelling it')
fig2, ax2 = plt.subplots(subplot_kw=dict(projection='polar'))
st2 = rose.plot_rose(ax2, [(20, 70), (25, 80)], title='all steep')
ok(st2 is None, 'a panel with nothing usable returns None, and says so')
plt.close('all')

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
