# -*- coding: utf-8 -*-
"""Parsing of the Mesure-style four-field record, kept free of Qt.

The original data-entry program takes a record as four fields:

        SS - TTT - DDQ - RRQ
        |     |     |     |
        |     |     |     +-- rake (pitch) + quadrant letter, e.g. 62N
        |     |     |         OR a bare trend with no letter, e.g. 124
        |     |     +-------- dip + quadrant letter, e.g. 87W
        |     +-------------- strike, 000-360
        +-------------------- movement-sense code, e.g. CS PN SN CN

Both trailing forms occur in the archive: sites entered as rakes carry a
quadrant letter (0406-7), sites entered as trends do not (L12).

Quadrant handling for the rake, deduced from the archive and verified on all
29 records of site 0406-7: the letter says which END of the strike line the
rake was measured from. TENSOR stores it against its own canonical end, which
is the azimuth (dip azimuth - 90); if the letter points at the other end, the
stored value is 180 - rake.

    SN 174 74E 62N  -> dip az 84, canonical end 354, "N" end is 354  -> 62
    CN 163 76W 62N  -> dip az 253, canonical end 163, "N" end is 343 -> 118
    CN 165 88W 62S  -> dip az 255, canonical end 165, "S" end is 165 -> 62

And the movement direction is the stored rake + 180 (see tensorfile).
"""
import numpy as np

FIELD_WIDTHS = (2, 3, 3, 4)     # sense, strike, dip+quad, rake/trend+quad
QUADRANTS = 'NSEW'


class RecordError(ValueError):
    pass


def _split_num_quad(text, what):
    t = text.strip().upper()
    if not t:
        raise RecordError('%s is empty' % what)
    quad = None
    if t[-1] in QUADRANTS:
        quad, t = t[-1], t[:-1]
    if not t.isdigit():
        raise RecordError('%s: "%s" is not a number' % (what, text))
    return int(t), quad


def _end_matching(quad, a, b):
    """Of the two strike-line ends a and b (azimuths), the one the quadrant
    letter refers to."""
    def score(az):
        r = np.radians(az)
        return {'N': np.cos(r), 'S': -np.cos(r),
                'E': np.sin(r), 'W': -np.sin(r)}[quad]
    return a if score(a) >= score(b) else b


def dip_azimuth(strike, dip_quad):
    """Resolve the true dip azimuth from strike + the dip's quadrant letter."""
    a, b = (strike + 90) % 360, (strike - 90) % 360
    if dip_quad is None:
        return a
    return _end_matching(dip_quad, a, b)


def rake_from_trend(dipaz, dip, trend):
    """Rake of the line in the plane that has the given trend, measured from
    the canonical strike end at (dipaz - 90). Two lines share a trend only if
    they are antipodal, so the magnitude is unique."""
    A, d = np.radians(dipaz), np.radians(dip)
    n = np.array([np.sin(d) * np.sin(A), np.sin(d) * np.cos(A), np.cos(d)])
    T = np.radians(trend)
    hx, hy = np.sin(T), np.cos(T)
    # line (hx cosP, hy cosP, -sinP) lying in the plane -> solve n.l = 0
    P = np.arctan2(hx * n[0] + hy * n[1], n[2])
    l = np.array([hx * np.cos(P), hy * np.cos(P), -np.sin(P)])
    strike = np.array([np.sin(A - np.pi / 2), np.cos(A - np.pi / 2), 0.0])
    downdip = np.array([np.sin(A) * np.cos(d), np.cos(A) * np.cos(d),
                        -np.sin(d)])
    return float(np.degrees(np.arctan2(l @ downdip, l @ strike)) % 360.0)


def parse_record(sense, strike_s, dip_s, rake_s):
    """Turn the four typed fields into the canonical stored record.

    Returns dict(sense, strike, dip, dipaz, rake, entered_as).
    'rake' is TENSOR's stored rake; the movement direction is rake + 180.
    """
    sense = (sense or '').strip().upper()
    if len(sense) not in (1, 2):
        raise RecordError('sense code should be 1 or 2 characters')

    st = (strike_s or '').strip()
    if not st.isdigit():
        raise RecordError('strike: "%s" is not a number' % strike_s)
    strike = int(st) % 360

    dip, dq = _split_num_quad(dip_s, 'dip')
    if not 0 <= dip <= 90:
        raise RecordError('dip must be 0-90, got %d' % dip)
    dipaz = dip_azimuth(strike, dq)

    val, rq = _split_num_quad(rake_s, 'rake/trend')
    if rq is None:
        entered_as = 'trend'
        if not 0 <= val <= 360:
            raise RecordError('trend must be 0-360, got %d' % val)
        rake = rake_from_trend(dipaz, dip, val)
    else:
        entered_as = 'rake'
        if not 0 <= val <= 180:
            raise RecordError('rake must be 0-180, got %d' % val)
        canon = (dipaz - 90) % 360
        other = (dipaz + 90) % 360
        end = _end_matching(rq, canon, other)
        rake = float(val if end == canon else (180 - val) % 360)

    return dict(sense=sense, strike=strike, dip=dip, dipaz=dipaz,
                rake=rake, entered_as=entered_as,
                tail='%-2s %03d %02d%s %s' % (sense, strike, dip, dq or '',
                                              rake_s.strip().upper()))


def parse_line(text):
    """Accept a whole record typed on one line, e.g. 'CS 122 87W 124'."""
    parts = text.replace('-', ' ').split()
    if len(parts) != 4:
        raise RecordError('expected 4 fields, got %d' % len(parts))
    return parse_record(*parts)


def records_to_arrays(records):
    """(K,3) normals and slip vectors from parsed records."""
    from .core import normal_from_dipaz, slip_from_rake
    from .tensorfile import RAKE_OFFSET
    if not records:
        return np.zeros((0, 3)), np.zeros((0, 3))
    dipaz = [r['dipaz'] for r in records]
    dip = [r['dip'] for r in records]
    rake = [r['rake'] + RAKE_OFFSET for r in records]
    n = normal_from_dipaz(dipaz, dip)
    s = slip_from_rake(dipaz, dip, rake)
    s = s - np.einsum('ki,ki->k', s, n)[:, None] * n
    return n, s / np.linalg.norm(s, axis=1, keepdims=True)
