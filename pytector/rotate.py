# -*- coding: utf-8 -*-
"""Back-tilting: rotate fault-slip data before inversion.

Why this exists, and what it deliberately does NOT do
-----------------------------------------------------
TENSOR has no back-tilt of its own. The archive was rotated by hand elsewhere
and re-run, which is why the folders carry names like

    0404-04C(backtilted 020 -20)

meaning a rotation about a horizontal axis trending 020 by -20 degrees. All 37
trial rotations recovered from the .stnt files use a horizontal axis.

The rotation ANGLE is not something this module computes. There is no
analytical solution for it: the angle is found by trying values and looking at
the result. What the code does is make trying fast and unambiguous, and record
what was tried. Choosing the reference surface, which is the last foliation
rather than bedding or an early fabric, and choosing the angle, are the user's
calls.

Conventions
-----------
Right-hand rule about the axis vector as given by its trend and plunge: a
POSITIVE angle turns anticlockwise when you look along the axis from its tail
towards its head. Both the fault normals and the slip vectors are rotated, so
rakes and senses are carried through correctly.
"""
import numpy as np

from .core import normal_from_dipaz, trend_plunge, vec_from_trend_plunge


def rotation_matrix(trend_deg, plunge_deg, angle_deg):
    """Rodrigues rotation about the axis at the given trend and plunge."""
    k = vec_from_trend_plunge(trend_deg, plunge_deg)
    k = k / np.linalg.norm(k)
    a = np.radians(angle_deg)
    K = np.array([[0.0, -k[2], k[1]],
                  [k[2], 0.0, -k[0]],
                  [-k[1], k[0], 0.0]])
    return np.eye(3) + np.sin(a) * K + (1.0 - np.cos(a)) * (K @ K)


def rotate_vectors(v, trend_deg, plunge_deg, angle_deg):
    R = rotation_matrix(trend_deg, plunge_deg, angle_deg)
    return np.atleast_2d(np.asarray(v, float)) @ R.T


def axis_from_plane(dipaz_deg, dip_deg, sense=+1):
    """Rotation that restores a reference plane to horizontal.

    The axis is the plane's strike line, horizontal, and the angle is its dip.
    Returns (trend, plunge, angle); plunge is 0 by construction.
    """
    trend = (float(dipaz_deg) - 90.0) % 360.0
    return trend, 0.0, sense * float(dip_deg)


def axis_from_pole(trend_deg, plunge_deg, sense=+1):
    """Same, given the reference plane by its pole instead.

    A pole at (trend, plunge) belongs to a plane dipping (90 - plunge) towards
    (trend + 180).
    """
    dipaz = (float(trend_deg) + 180.0) % 360.0
    dip = 90.0 - float(plunge_deg)
    return axis_from_plane(dipaz, dip, sense=sense)


def restores_to_horizontal(dipaz_deg, dip_deg):
    """Which sign of the rotation actually flattens the plane.

    Rather than reason about handedness, try both and keep the one whose pole
    ends up vertical. Returns (trend, plunge, angle).
    """
    n = normal_from_dipaz(dipaz_deg, dip_deg)
    n = np.atleast_2d(n)[0]
    best = None
    for sense in (+1, -1):
        t, p, a = axis_from_plane(dipaz_deg, dip_deg, sense=sense)
        m = rotate_vectors(n[None, :], t, p, a)[0]
        vertical = abs(m[2])
        if best is None or vertical > best[0]:
            best = (vertical, (t, p, a))
    return best[1]


def rotate_site(n, s, trend_deg, plunge_deg, angle_deg):
    """Rotate a whole data set. Returns new (n, s), both re-normalised."""
    R = rotation_matrix(trend_deg, plunge_deg, angle_deg)
    n2 = np.atleast_2d(np.asarray(n, float)) @ R.T
    s2 = np.atleast_2d(np.asarray(s, float)) @ R.T
    n2 /= np.linalg.norm(n2, axis=1, keepdims=True)
    s2 -= np.einsum('ki,ki->k', s2, n2)[:, None] * n2
    s2 /= np.linalg.norm(s2, axis=1, keepdims=True)
    return n2, s2


def canonicalise(n, s):
    """Flip pairs so the normal points up. For WRITING a site file, not for
    drawing.

    A rotation carries the normal and the slip vector rigidly, so (n, s) and
    (-n, -s) are the same datum and the inversion cannot tell them apart. The
    drawing can, because plot_site takes the symbol's direction from the raw
    slip vector, and 71 per cent of archive slip vectors point into the upper
    hemisphere, so this is not an edge case.

    ⚠️ Do NOT apply this before drawing rotated data. It was, briefly, on the
    reasoning that turning a plane through the vertical swaps hanging wall for
    footwall and so must reverse the drawn sense. The archive says otherwise
    and the archive is the authority: across the twelve back-tilt pairs the
    original program produced, the slip vectors in the back-tilted file agree
    in sign with the parent's rotated slip vectors in 74 of 76 data. The
    original kept the rotated vector as it came, so the plots it drew are the
    un-canonicalised ones, and canonicalising first reversed five of the six
    striae at L12.

    What it is still for is the file format, where dip azimuth, dip and rake
    have to be expressed against an upward normal. as_records() does this step
    itself for exactly that reason.
    """
    n = np.atleast_2d(np.asarray(n, float))
    s = np.atleast_2d(np.asarray(s, float))
    up = np.where(n[:, 2] >= 0, 1.0, -1.0)[:, None]
    return n * up, s * up


def crossed_over(n, rn):
    """Per datum: did this plane turn through the vertical during the rotation.

    True where the pole changed hemisphere, which is exactly where
    canonicalise() has to flip the pair.
    """
    n = np.atleast_2d(np.asarray(n, float))
    rn = np.atleast_2d(np.asarray(rn, float))
    return (n[:, 2] >= 0) != (rn[:, 2] >= 0)


def as_records(n, s):
    """Turn rotated vectors back into dip azimuth / dip / rake, so the result
    can be written out as an ordinary TENSOR site file."""
    from .tensorfile import RAKE_OFFSET
    n = np.atleast_2d(np.asarray(n, float))
    s = np.atleast_2d(np.asarray(s, float))
    out = []
    for i in range(len(n)):
        v = n[i] if n[i][2] >= 0 else -n[i]      # upward normal
        dip = np.degrees(np.arccos(np.clip(v[2], -1, 1)))
        dipaz = np.degrees(np.arctan2(v[0], v[1])) % 360.0
        A, d = np.radians(dipaz), np.radians(dip)
        strike = np.array([np.sin(A - np.pi / 2), np.cos(A - np.pi / 2), 0.0])
        downdip = np.array([np.sin(A) * np.cos(d), np.cos(A) * np.cos(d),
                            -np.sin(d)])
        si = s[i] if n[i][2] >= 0 else -s[i]
        rake = np.degrees(np.arctan2(si @ downdip, si @ strike)) % 360.0
        out.append(dict(dipaz=int(round(dipaz)) % 360, dip=int(round(dip)),
                        rake=(rake - RAKE_OFFSET) % 360.0))
    return out


def describe(trend_deg, plunge_deg, angle_deg):
    """The label the archive uses, e.g. '(backtilted 020 -20)'."""
    if abs(plunge_deg) < 0.5:
        return '(backtilted %03d %+d)' % (round(trend_deg) % 360,
                                          round(angle_deg))
    return '(backtilted %03d/%02d %+d)' % (round(trend_deg) % 360,
                                           round(plunge_deg),
                                           round(angle_deg))
