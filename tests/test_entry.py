# -*- coding: utf-8 -*-
"""Type the archive's own human-readable tails back in and check that the
parser recovers the rake TENSOR stored in columns [7:10]."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytensor import entry, tensorfile

from pytensor.archive import ROOT
SITES = [('L12', os.path.join(ROOT, 'L12', 'L12')),
         ('0406-7', os.path.join(ROOT, '0406-7', '0406-04'))]

bad = 0
total = 0
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
