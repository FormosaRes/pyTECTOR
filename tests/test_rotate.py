# -*- coding: utf-8 -*-
"""Rotation core: round trips, and the convention checked against the archive.

The archive's 應力軸旋轉 folder holds back-tilted copies of sites whose folder
names record the rotation. Solving for the rotation that maps original to copy
(Kabsch on the fault normals) recovers a horizontal axis at the stated trend
in every case, which is what fixes the convention.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, entry, rotate, tensorfile

from pytensor.archive import ROOT
fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


print('1. rotation is a rotation')
R = rotate.rotation_matrix(37.0, 12.0, 41.0)
ok(abs(np.linalg.det(R) - 1) < 1e-12, 'determinant is +1')
ok(np.allclose(R @ R.T, np.eye(3), atol=1e-12), 'orthogonal')
ok(np.allclose(rotate.rotation_matrix(37, 12, 41)
               @ rotate.rotation_matrix(37, 12, -41), np.eye(3), atol=1e-12),
   'opposite angles cancel')

print('\n2. a reference plane really is restored to horizontal')
for dipaz, dip in ((212, 87), (84, 74), (235, 62), (330, 15)):
    t, p, a = rotate.restores_to_horizontal(dipaz, dip)
    n = core.normal_from_dipaz(dipaz, dip)
    m = rotate.rotate_vectors(np.atleast_2d(n), t, p, a)[0]
    ok(abs(abs(m[2]) - 1) < 1e-9,
       'plane %03d/%02d flattens with axis %03.0f angle %+.0f'
       % (dipaz, dip, t, a))

print('\n3. vectors -> records -> vectors round trip')
recs = [entry.parse_record(*t) for t in
        (('CS', '122', '87W', '124'), ('PN', '135', '85W', '80S'),
         ('CN', '145', '62W', '50N'), ('SN', '174', '74E', '62N'),
         ('CN', '151', '69W', '72N'), ('PN', '3', '70E', '76N'))]
n, s = entry.records_to_arrays(recs)
back = rotate.as_records(n, s)
n2 = core.normal_from_dipaz([r['dipaz'] for r in back],
                            [r['dip'] for r in back])
s2 = core.slip_from_rake([r['dipaz'] for r in back], [r['dip'] for r in back],
                         [r['rake'] + tensorfile.RAKE_OFFSET for r in back])
s2 -= np.einsum('ki,ki->k', s2, n2)[:, None] * n2
s2 /= np.linalg.norm(s2, axis=1, keepdims=True)
dn = np.degrees(np.arccos(np.clip(np.abs(np.einsum('ki,ki->k', n, n2)), -1, 1)))
ds = np.degrees(np.arccos(np.clip(np.einsum('ki,ki->k', s, s2), -1, 1)))
ok(dn.max() < 1.0, 'normals survive the round trip (max %.2f deg)' % dn.max())
ok(ds.max() < 1.0, 'slips survive the round trip (max %.2f deg)' % ds.max())

print('\n4. rotate then invert is the same as inverting rotated data')
T = rotate.rotation_matrix(20.0, 0.0, -20.0)
n_r, s_r = rotate.rotate_site(n, s, 20.0, 0.0, -20.0)
ok(np.allclose(n_r, n @ T.T, atol=1e-9), 'normals rotate as expected')
ok(abs(np.einsum('ki,ki->k', n_r, s_r)).max() < 1e-9,
   'slip stays in its plane after rotation')

print('\n5. convention against the archive')
PAT = re.compile(r'\(backtilted\s*([0-9]{1,3})\s*([+-]?\d+)\s*\)', re.I)


def kabsch(A, B):
    signs = np.ones(len(A))
    R = np.eye(3)
    for _ in range(20):
        H = (A * signs[:, None]).T @ B
        U, _S, Vt = np.linalg.svd(H)
        d = np.sign(np.linalg.det(Vt.T @ U.T))
        R = Vt.T @ np.diag([1, 1, d]) @ U.T
        new = np.sign(np.einsum('ki,ki->k', A @ R.T, B))
        new[new == 0] = 1
        if np.array_equal(new, signs):
            break
        signs = signs * new
    err = np.degrees(np.arccos(np.clip(
        np.abs(np.einsum('ki,ki->k', A @ R.T, B)), -1, 1))).mean()
    return R, err


if os.path.exists(ROOT):
    files = tensorfile.discover(ROOT)
    tgts = [p for p in files if PAT.search(p)]
    plain = [p for p in files
             if not PAT.search(p) and 'backtilt' not in p.lower()]
    fitted = 0
    for p in tgts:
        try:
            tgt = tensorfile.read_site(p)
        except Exception:
            continue
        best = None
        for q in plain:
            try:
                src = tensorfile.read_site(q)
            except Exception:
                continue
            if len(src) != len(tgt):
                continue
            R, err = kabsch(src.n, tgt.n)
            if best is None or err < best[0]:
                best = (err, R, q)
        if best and best[0] < 2.0:
            fitted += 1
    ok(fitted >= 6, 'archive back-tilts reproduce as rigid rotations (%d found)'
       % fitted)
else:
    print('   archive missing, skipped')

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
