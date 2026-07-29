# -*- coding: utf-8 -*-
"""Two oracles for the entry parser.

1. The archive's own human-readable tails, typed back in: the parser must
   recover the rake TENSOR stored in columns [7:10]. Needs PYTENSOR_ARCHIVE.

2. The original program itself. On 2026-07-29 the user ran MESURE 5.51 (aou91)
   on the Windows XP machine, typed three records, and photographed the echo,
   which prints the striae AXIS in lower-hemisphere form: the pitch with the
   quadrant letter of the end it is measured from, then the trend and plunge
   of the downward line. Needs nothing, so it always runs.

       typed                MESURE echo
       CD 090 50S 10E   ->  1 C1D 90 50S 10E  96  8
       CD 090 50N 150   ->  2 C1D 90 50N 70W 330 46
       CD 090 85N 150   ->  3 C1D 90 85N 87W 329 84

   In the code C1D the 1 is the tectonic-event number from MESURE's main menu,
   sitting between the confidence and movement letters. MESURE prints whole
   degrees, and its 329 against an exact 330.0 here is its own rounding; hence
   the 1.1 degree tolerance on the trend.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from pytensor import core, entry, tensorfile

from pytensor.archive import ROOT
SITES = [('L12', os.path.join(ROOT, 'L12', 'L12')),
         ('0406-7', os.path.join(ROOT, '0406-7', '0406-04'))]

bad = 0
total = 0

print('MESURE 5.51 oracle (photographed from the original on XP)')
MESURE = [
    (('CD', '090', '50S', '10E'), 10.0, 'E', 96.0, 8.0),
    (('CD', '090', '50N', '150'), 70.0, 'W', 330.0, 46.0),
    (('CD', '090', '85N', '150'), 87.0, 'W', 329.0, 84.0),
]
for fields, m_pitch, m_end, m_t, m_p in MESURE:
    total += 1
    r = entry.parse_record(*fields)
    line = core.slip_from_rake(r['dipaz'], r['dip'], r['rake'])
    if line[2] > 0:
        line = -line                      # the axis, lower hemisphere
    t = float(np.degrees(np.arctan2(line[0], line[1])) % 360.0)
    p = float(np.degrees(np.arcsin(-line[2])))
    canon = (r['dipaz'] - 90.0) % 360.0
    end = entry._end_matching(m_end, canon, (r['dipaz'] + 90.0) % 360.0)
    down = r['rake'] if r['rake'] <= 180.0 else (r['rake'] + 180.0) % 360.0
    pitch = down if end == canon else (180.0 - down) % 360.0
    ok = (abs(pitch - m_pitch) <= 1.0
          and abs((t - m_t + 180.0) % 360.0 - 180.0) <= 1.1
          and abs(p - m_p) <= 1.0)
    if not ok:
        bad += 1
    print('  %-18s pitch %5.1f%s line %5.1f/%4.1f   MESURE %3.0f%s %3.0f/%2.0f%s'
          % (' '.join(fields), pitch, m_end, t, p, m_pitch, m_end, m_t, m_p,
             '' if ok else '   <-- MISMATCH'))
print()
for name, path in SITES:
    if not os.path.exists(path):
        print('%s: archive missing, skipped' % name)
        continue
    site = tensorfile.read_site(path)
    print('=' * 62)
    print('%s  (%d records)' % (name, len(site)))
    for i, r in enumerate(site.records):
        total += 1
        try:
            p = entry.parse_line(r['tail'])
        except entry.RecordError as exc:
            print('  %2d  %-16s  PARSE FAIL: %s' % (i + 1, r['tail'], exc))
            bad += 1
            continue
        ok_az = (p['dipaz'] == r['dipaz'])
        ok_dip = (p['dip'] == r['dip'])
        ok_rake = abs(p['rake'] - r['rake']) < 1.0
        flag = '' if (ok_az and ok_dip and ok_rake) else '   <-- MISMATCH'
        if flag:
            bad += 1
        print('  %2d  %-16s  as %-5s  dipaz %3d/%3d  dip %2d/%2d  '
              'rake %5.1f/%3d%s'
              % (i + 1, r['tail'], p['entered_as'],
                 p['dipaz'], r['dipaz'], p['dip'], r['dip'],
                 p['rake'], r['rake'], flag))

print('=' * 62)
print('%d records, %d mismatches' % (total, bad))
sys.exit(1 if bad else 0)
