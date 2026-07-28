# -*- coding: utf-8 -*-
"""What decides which side the barb sits on?

Hypothesis: there is no threshold at all. The side follows the sign of the
STRIKE-SLIP COMPONENT of the movement, so it flips the instant the slip leaves
pure dip-slip. Since the movement direction is (stored rake + 180) measured
from the strike end at (dip azimuth - 90),

    s . strike = cos(rake + 180) = -cos(stored rake)

so the predicted side is simply governed by whether the stored rake is under
or over 90 degrees.

Tested against every symbol whose head could be measured.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalogue_striae import symbols_of, ROOT
from pytensor import core

samples = []
for folder in sorted(os.listdir(ROOT)):
    if not os.path.isdir(os.path.join(ROOT, folder)):
        continue
    try:
        samples.extend(symbols_of(folder))
    except Exception:
        pass
have = [x for x in samples if x['side'] is not None]
print('%d symbols with a measurable head\n' % len(have))


def strike_component(x):
    """s . strike_vec, with the strike taken at (dip azimuth - 90)."""
    A = np.radians(x['rec']['dipaz'])
    sv = np.array([np.sin(A - np.pi / 2), np.cos(A - np.pi / 2), 0.0])
    s3 = np.array([x['s'][0], x['s'][1], x['s'][2]]) if 's' in x else None
    return None if s3 is None else float(s3 @ sv)


# rebuild the 3-D slip for each sample from its record
from pytensor.core import normal_from_dipaz, slip_from_rake
from pytensor.tensorfile import RAKE_OFFSET

rules = {'strike-slip component': [],
         'stored rake vs 90 deg': [],
         'movement letter': []}
detail = []
for x in have:
    r = x['rec']
    n = normal_from_dipaz(r['dipaz'], r['dip'])
    s = slip_from_rake(r['dipaz'], r['dip'], r['rake'] + RAKE_OFFSET)
    s = s - float(s @ n) * n
    s = s / np.linalg.norm(s)
    A = np.radians(r['dipaz'])
    sv = np.array([np.sin(A - np.pi / 2), np.cos(A - np.pi / 2), 0.0])
    comp = float(s @ sv)

    obs = np.sign(x['side'])
    rules['strike-slip component'].append(obs == np.sign(comp))
    rules['stored rake vs 90 deg'].append(
        obs == (1 if (r['rake'] % 360) > 90 else -1))
    rules['movement letter'].append(
        obs == {'D': 1, 'S': -1}.get(x['mv'], 1))
    detail.append((x['mv'], x['conf'], r['rake'], comp, x['side']))

for name, hits in rules.items():
    hits = np.array(hits)
    print('   %-24s %3d / %3d correct' % (name, hits.sum(), len(hits)))

print('\nstrike-slip component vs barb side, sorted by how oblique the slip is:')
print('  mv conf  rake   s.strike    barb side   agree')
detail.sort(key=lambda t: abs(t[3]))
for mv, conf, rake, comp, side in detail[:14]:
    print('   %s  %s   %5.1f  %+8.4f   %+8.4f     %s'
          % (mv, conf, rake, comp, side,
             'yes' if np.sign(comp) == np.sign(side) else 'NO'))
print('  ...')
for mv, conf, rake, comp, side in detail[-4:]:
    print('   %s  %s   %5.1f  %+8.4f   %+8.4f     %s'
          % (mv, conf, rake, comp, side,
             'yes' if np.sign(comp) == np.sign(side) else 'NO'))

mism = [d for d in detail if np.sign(d[3]) != np.sign(d[4])]
print('\n%d mismatches for the strike-slip rule' % len(mism))
for mv, conf, rake, comp, side in mism:
    print('   %s %s  rake %.1f  s.strike %+.4f  side %+.4f'
          % (mv, conf, rake, comp, side))

smallest = min(abs(d[3]) for d in detail)
print('\nsmallest strike-slip component in the archive: %.4f' % smallest)
print('(a pure dip-slip fault would give exactly 0, and none occurs)')
