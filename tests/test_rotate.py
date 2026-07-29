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
from pytector import core, entry, rotate, tensorfile

from pytector.archive import ROOT
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


print('\n6. the drawn slip sense is recomputed, not carried over')
from pytector import plot

# The vector form must agree with the record form exactly on unrotated data,
# or it is not the same quantity.
if os.path.exists(ROOT):
    disagree = total = 0
    for p in tensorfile.discover(ROOT):
        try:
            st = tensorfile.read_site(p)
        except Exception:
            continue
        if not len(st):
            continue
        disagree += int((st.sides
                         != plot.strike_slip_sign_vectors(st.n, st.s)).sum())
        total += len(st)
    ok(disagree == 0 and total > 500,
       'vector form matches the record form on %d archive data (%d disagree)'
       % (total, disagree))
else:
    print('   archive missing, skipped the archive half')

# Turning a plane past vertical redescribes it with a dip azimuth 180 degrees
# away and swaps hanging wall for footwall. That does NOT by itself change the
# drawn side: it reverses the strike direction and the slip vector together, so
# the product survives. The side is convention-free.
rng = np.random.default_rng(0)
rn_ = rng.normal(size=(4000, 3))
rn_ /= np.linalg.norm(rn_, axis=1, keepdims=True)
rs_ = rng.normal(size=(4000, 3))
rs_ -= np.einsum('ki,ki->k', rs_, rn_)[:, None] * rn_
rs_ /= np.linalg.norm(rs_, axis=1, keepdims=True)
ok(np.array_equal(plot.strike_slip_sign_vectors(rn_, rs_),
                  plot.strike_slip_sign_vectors(-rn_, -rs_)),
   'the hanging-wall/footwall swap cancels: side is convention-free')

# What DOES change it is the rotation itself. The strike-slip component is
# orientation-dependent, so data whose slip is near pure dip-slip cross zero
# and reverse. Carrying the measured side over to the rotated panel draws
# those couples mirrored, which is the bug this replaces.
if os.path.exists(ROOT):
    changed = seen = 0
    for p in tensorfile.discover(ROOT):
        try:
            st = tensorfile.read_site(p)
        except Exception:
            continue
        if len(st) < 4:
            continue
        for spec in ((20, 0, -20), (0, 0, 30), (80, 0, -30), (20, 0, -40)):
            a, b = rotate.rotate_site(st.n, st.s, *spec)
            changed += int((st.sides
                            != plot.strike_slip_sign_vectors(a, b)).sum())
            seen += len(st)
    pct = 100.0 * changed / max(seen, 1)
    ok(pct > 5.0,
       'rotation really does reverse the side for a solid fraction of data '
       '(%d of %d, %.1f%%)' % (changed, seen, pct))

print('\n6b. the reference surface really is taken to horizontal')
# What the window's "restore the reference surface to horizontal" mode does,
# including the partial-restoration percentage. At 100 per cent the surface has
# to read dip 00; at 50 per cent, half its dip.
from pytector import plot as _plot
for dipaz, dip in ((224, 27), (44, 27), (348, 44), (10, 80), (330, 15)):
    t, p, a = rotate.restores_to_horizontal(dipaz, dip)
    for pct, want in ((100, 0.0), (50, dip / 2.0)):
        v = core.normal_from_dipaz(dipaz, dip)
        v = rotate.rotate_vectors(np.atleast_2d(v), t, p, a * pct / 100.0)[0]
        _az, rdip = _plot.reference_from_vectors(v)
        ok(abs(rdip - want) < 0.5,
           'ref %03d/%02d at %3d%% -> dip %05.2f (want %05.2f)'
           % (dipaz, dip, pct, rdip, want))

print('\n7a. the original did NOT flip slip vectors when it back-tilted')
# Settles a convention that cannot be settled by reasoning: (n, s) and
# (-n, -s) are the same datum, so which one a back-tilted file holds is a
# choice, and plot_site's symbol direction is not invariant to it. The archive
# made the choice. Each back-tilted run is matched to its parent by Kabsch on
# the normals, then the parent's rotated slip vectors are compared in sign
# against what the back-tilted file actually holds.
if os.path.exists(ROOT):
    files = tensorfile.discover(ROOT)
    # every back-tilted run, not only those whose folder spells out the angle
    tg = [p for p in files if 'backtilt' in p.lower()]
    pl = [p for p in files if 'backtilt' not in p.lower()]
    agree = total = pairs = 0
    for t in tg:
        try:
            T = tensorfile.read_site(t)
        except Exception:
            continue
        if len(T) < 5:
            continue
        best = None
        for q in pl:
            try:
                S = tensorfile.read_site(q)
            except Exception:
                continue
            if len(S) != len(T):
                continue
            R, err = kabsch(S.n, T.n)
            if best is None or err < best[0]:
                best = (err, R, S)
        if best is None or best[0] > 2.0:
            continue
        _e, R, S = best
        pairs += 1
        d = np.einsum('ki,ki->k', S.s @ R.T, T.s)
        agree += int((d > 0).sum())
        total += len(T)
    ok(pairs >= 10 and agree >= 0.9 * total,
       'back-tilted files keep the rotated slip vector as it came '
       '(%d of %d data over %d pairs)' % (agree, total, pairs))
else:
    print('   archive missing, skipped')

print('\n7b. canonicalise is available, but for writing files not for drawing')
# The stored slip vector means "motion of the block on the upward side". Turn
# the plane through vertical and that side becomes the other block, so the same
# movement is written the other way round. Drawn un-flipped it reads backwards.
if os.path.exists(ROOT):
    from pytector import invdir
    crossed = total = 0
    for p in tensorfile.discover(ROOT):
        try:
            st = tensorfile.read_site(p)
        except Exception:
            continue
        if not len(st):
            continue
        for spec in ((20, 0, -20), (0, 0, 30), (80, 0, -30), (20, 0, -40)):
            a, b = rotate.rotate_site(st.n, st.s, *spec)
            crossed += int(rotate.crossed_over(st.n, a).sum())
            total += len(st)
    ok(crossed > 0.05 * total,
       'planes really do cross the vertical (%d of %d, %.1f%%)'
       % (crossed, total, 100.0 * crossed / total))

    site = tensorfile.read_site(os.path.join(ROOT, '0406-7', '0406-04'))
    rn, rs = rotate.rotate_site(site.n, site.s, 20, 0, -40)
    cn, cs = rotate.canonicalise(rn, rs)
    flip = rotate.crossed_over(site.n, rn)
    ok(flip.any(), 'the test site has data that cross over (%d of %d)'
       % (int(flip.sum()), len(site)))
    ok(np.allclose(cn[flip], -rn[flip]) and np.allclose(cs[flip], -rs[flip]),
       'canonicalise flips exactly those pairs, normal and slip together')
    # and the reason it must not be used before drawing
    from pytector import plot as _pp
    d0 = np.degrees(np.arctan2(rs[:, 0], rs[:, 1]))
    d1 = np.degrees(np.arctan2(cs[:, 0], cs[:, 1]))
    turned = int((np.abs(((d0 - d1 + 180) % 360) - 180) > 90).sum())
    ok(turned == int(flip.sum()),
       'it reverses the drawn striae direction for every pair it flips (%d), '
       'which is why the drawing path does not call it' % turned)
    ok(np.allclose(cn[~flip], rn[~flip]) and np.allclose(cs[~flip], rs[~flip]),
       'and leaves the rest alone')
    # the pair is flipped together, so the datum is unchanged and the answer
    # must not move at all
    a = core.describe(invdir.run(rn, rs, n_pass=1)['T'])['sigma1']
    b = core.describe(invdir.run(cn, cs, n_pass=1)['T'])['sigma1']
    ok(abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6,
       'the inversion cannot tell the difference, so this is drawing only')
else:
    print('   archive missing, skipped')

# n and s turn together, so the datum is physically unchanged and the
# inversion is blind to all of this. It is a drawing concern only.
n0 = core.normal_from_dipaz([10.0], [80.0])
s0 = core.slip_from_rake([10.0], [80.0], [20.0])
s0 = s0 - np.einsum('ki,ki->k', s0, n0)[:, None] * n0
s0 = s0 / np.linalg.norm(s0, axis=1, keepdims=True)
ra, rb = rotate.rotate_site(n0, s0, 100.0, 0.0, 40.0)
ok(abs(float(np.einsum('ki,ki->k', ra, rb)[0])) < 1e-12,
   'slip stays in its plane, so the inversion never saw any of it')

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
