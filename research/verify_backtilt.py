# -*- coding: utf-8 -*-
"""Pin the rotation convention against the archive.

The 應力軸旋轉 folder holds back-tilted copies whose names record the rotation,
e.g. '0404-04C(backtilted 020 -20)'. If the un-rotated original is also on
disk, rotating it by the stated axis and angle must reproduce the back-tilted
file. That settles the sign and the axis convention without guessing.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import rotate, tensorfile

from pytector.archive import ROOT
PAT = re.compile(r'\(backtilted\s*([0-9]{1,3})\s*([+-]?\d+)\s*\)',
                 re.IGNORECASE)


def load(path):
    site = tensorfile.read_site(path)
    return site, site.n, site.s


def key(site):
    """A signature that survives rotation only if the data really match."""
    return tuple(sorted((r['dipaz'], r['dip'], int(round(r['rake'])))
                        for r in site.records))


# collect every site file on disk
files = tensorfile.discover(ROOT)
by_len = {}
for p in files:
    try:
        s = tensorfile.read_site(p)
    except Exception:
        continue
    if len(s) >= 4:
        by_len.setdefault(len(s), []).append((p, s))

print('%d site files, %d distinct fault counts\n' % (len(files), len(by_len)))

tested = 0
for p in files:
    m = PAT.search(p)
    if not m:
        continue
    trend, angle = float(m.group(1)), float(m.group(2))
    try:
        tgt = tensorfile.read_site(p)
    except Exception:
        continue
    cands = [(q, s) for q, s in by_len.get(len(tgt), [])
             if not PAT.search(q) and 'backtilt' not in q.lower()]
    if not cands:
        continue

    print('=' * 74)
    print('%s' % os.path.relpath(p, ROOT))
    print('   stated rotation: trend %03d, angle %+d, %d faults'
          % (trend, angle, len(tgt)))

    best = None
    for q, src in cands:
        for sign in (+1, -1):
            n2, s2 = rotate.rotate_site(src.n, src.s, trend, 0.0, sign * angle)
            recs = rotate.as_records(n2, s2)
            got = tuple(sorted((r['dipaz'], r['dip'], int(round(r['rake'])))
                               for r in recs))
            want = key(tgt)
            if len(got) != len(want):
                continue
            d = sum(min(abs(a[0] - b[0]), 360 - abs(a[0] - b[0]))
                    + abs(a[1] - b[1])
                    + min(abs(a[2] - b[2]), 360 - abs(a[2] - b[2]))
                    for a, b in zip(got, want)) / float(len(got))
            if best is None or d < best[0]:
                best = (d, q, sign)
    if best is not None:
        d, q, sign = best
        verdict = 'MATCH' if d < 3.0 else ('close' if d < 12 else 'no match')
        print('   best source: %s' % os.path.relpath(q, ROOT))
        print('   sign %+d, mean per-datum difference %.2f deg   -> %s'
              % (sign, d, verdict))
        tested += 1

print('=' * 74)
print('%d back-tilted folders tested' % tested)
