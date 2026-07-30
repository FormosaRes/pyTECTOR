# -*- coding: utf-8 -*-
"""Reader for Angelier TENSOR data files.

Format decoded 2026-07-28 by cross-checking the data file, MOHR1, INFO1 and
Mesure_key.txt of sites L12 (6 faults) and 0406-7 (29 faults). Verified on all
35 records: SIGMN, TAU and TAUST reproduce to the files' own precision.

A run lives in one folder. The main file has NO extension and is named after
the site. Alongside it:
    INFO1   human readable report, includes LAMBDA / TAUMAX and the per-fault table
    MOHR1   the same per-fault numbers at full precision, plus the eigenvalues
    PLOT1, HPGL   plotting output
    Mesure_key.txt, diagra_keys.txt   the keystrokes originally typed

Fixed width ASCII. Record layout:

    [0:2]    two independent digits, decoded 2026-07-28 and verified on all 35
             archive records:
               [0]  confidence in the striae:  1 = C, 2 = P, 3 = S
                    (Certain / Probable / Suppose, matching the human-readable
                    first letter of the sense code)
               [1]  which end of the strike line the rake was measured from:
                    1 = the canonical end at (dip azimuth - 90),
                    2 = the other end, in which case the stored rake is
                        180 - (the rake that was typed)
             The human-readable code is <confidence><movement>, where the
             movement letter is I inverse, N normal, S senestral, D dextral.
             The movement letter is descriptive only: the stored rake already
             carries the direction over a full 360 degrees.
    [2:5]    dip azimuth. This is the TRUE dip azimuth, already resolved using
             the quadrant letter; it is not blindly strike + 90.
             e.g. "SN 174 74E" -> 84, not 264.
    [5:7]    dip
    [7:10]   RAKE (pitch), measured from the strike end at (dip azimuth - 90)
    [47:61]  human readable echo of what was typed, e.g. "CS 122 87W 124".
             The last field there may be a rake (with a quadrant letter, "62N")
             or a trend (no letter, "124"), depending on how it was entered.

WARNING, a trap already fallen into: on a site whose planes all dip 85-89 deg,
sin(plunge) = sin(rake) sin(dip) makes rake and plunge agree to within a
degree, so [7:10] can be mistaken for a plunge. Site 0406-7 spans dips of
42-89 deg and settles it: the field is a rake.

WARNING 2: the movement direction is rake + 180. Using the stored value
directly swaps sigma1 and sigma3.
"""
import os
import re

import numpy as np

from .core import normal_from_dipaz, slip_from_rake

RAKE_OFFSET = 180.0

#: first digit of the [0:2] code -> confidence letter
CONFIDENCE = {'1': 'C', '2': 'P', '3': 'S'}
#: second letter of the human-readable code -> movement type
MOVEMENT = {'I': 'inverse', 'N': 'normal', 'S': 'senestral', 'D': 'dextral'}


class Site(object):
    def __init__(self, name, records, result_line=None, path=None,
                 code='01'):
        self.name = name
        self.records = records
        self.result_line = result_line
        self.path = path
        #: the two-character site code the file itself carries, which is what
        #: belongs in the fixed-width fields. Not the file name.
        self.code = code

    def __len__(self):
        return len(self.records)

    @property
    def n(self):
        return normal_from_dipaz([r['dipaz'] for r in self.records],
                                 [r['dip'] for r in self.records])

    @property
    def confidence(self):
        """Per-record 'C' / 'P' / 'S', for the arrow styles."""
        return [r.get('confidence', 'C') for r in self.records]

    @property
    def sides(self):
        """Per-record +1 / -1: which side the barb and the shaft offset sit
        on, from the sign of the strike-slip component."""
        from .plot import strike_slip_sign
        return strike_slip_sign([r['dipaz'] for r in self.records],
                                [r['dip'] for r in self.records],
                                [r['rake'] + RAKE_OFFSET
                                 for r in self.records])

    @property
    def s(self):
        s = slip_from_rake([r['dipaz'] for r in self.records],
                           [r['dip'] for r in self.records],
                           [r['rake'] + RAKE_OFFSET for r in self.records])
        n = self.n
        s = s - np.einsum('ki,ki->k', s, n)[:, None] * n     # force into plane
        return s / np.linalg.norm(s, axis=1, keepdims=True)


def read_site(path):
    """Read the main (extension-less) data file of a TENSOR run."""
    with open(path, 'r', errors='replace') as fh:
        lines = fh.read().splitlines()

    name = os.path.basename(path)
    records, result, site_code = [], None, '01'
    for ln in lines:
        if len(ln) < 10:
            continue
        head = ln[:2]
        if head in ('02',):                       # file header
            continue
        if head == '01':                          # site label line, e.g. 01PANG
            site_code = head
            continue
        if head == '03':                          # result line
            result = ln
            continue
        if ln.startswith(' 0*') or ln.startswith(' 9*'):
            break
        try:
            dipaz = int(ln[2:5])
            dip = int(ln[5:7])
            rake = int(ln[7:10])
        except ValueError:
            continue
        tail = ln[47:61].strip()
        records.append(dict(code=head, dipaz=dipaz, dip=dip, rake=rake,
                            tail=tail,
                            confidence=CONFIDENCE.get(head[0], 'C'),
                            movement=(tail[1:2].upper() if len(tail) > 1
                                      else '')))
        if len(ln) >= 63:
            site_code = ln[61:63].strip() or site_code
    site = Site(name, records, result, path)
    site.code = site_code
    return site


#: field widths of the '03' result line, after the 8-character prefix
#: "03" + method(4) + ACC(2). The numbers are packed with NO separators, so
#: they must be sliced, not split. Confirmed on both archive sites:
#:   03INVD09359.668.5116.410.1209.918.80.13820.9 54.1...
#:   03INVD09 81.035.9331.125.1214.643.60.413 8.7 23.1...
_RESULT_FIELDS = [('s1_trend', 0, 5), ('s1_plunge', 5, 9),
                  ('s2_trend', 9, 14), ('s2_plunge', 14, 18),
                  ('s3_trend', 18, 23), ('s3_plunge', 23, 27),
                  ('phi', 27, 32), ('ANG_mean', 32, 36),
                  ('RUP_mean', 36, 41)]


def parse_result_line(ln):
    """Decode a '03INVD...' / '03PSID...' result line (fixed width)."""
    if ln is None or len(ln) < 49:
        return None
    body = ln[8:]
    try:
        v = {k: float(body[a:b]) for k, a, b in _RESULT_FIELDS}
    except ValueError:
        return None
    return dict(method=ln[2:6].strip(), acc=ln[6:8].strip(),
                sigma1=(v['s1_trend'], v['s1_plunge']),
                sigma2=(v['s2_trend'], v['s2_plunge']),
                sigma3=(v['s3_trend'], v['s3_plunge']),
                phi=v['phi'], ANG_mean=v['ANG_mean'], RUP_mean=v['RUP_mean'])


def read_mohr(path):
    """MOHR1: eigenvalues + Phi on line 1, then SIGMN TAU TAUST RUP ANG."""
    with open(path, 'r', errors='replace') as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    eig, phi, rows = None, None, []
    for ln in lines:
        if ln[:2] == '02':
            v = [float(x) for x in ln[2:].split()]
            eig, phi = np.array(v[:3]), v[3]
            continue
        if ln[:2] == '03':
            continue
        parts = ln.split()
        if len(parts) == 5:
            rows.append([float(x) for x in parts])
    return dict(eigenvalues=eig, phi=phi, table=np.array(rows))


def read_info_lambda(path):
    """Pull the INVDIR pass number and the LAMBDA / TAUMAX that INFO1 prints."""
    with open(path, 'r', errors='replace') as fh:
        txt = fh.read()
    out = {}
    m = re.search(r'SOLUTION INVDIR \(NO\s*(\d+)\)\s*LAMBDA=\s*([\d.]+)', txt)
    if m:
        out['pass_no'] = int(m.group(1))
        out['lambda_invdir'] = float(m.group(2))
    m = re.search(r'LAMBDA=\s*([\d.]+)\s*TAUMAX=\s*([\d.]+)', txt)
    if m:
        out['lambda_psidir'] = float(m.group(1))
        out['taumax'] = float(m.group(2))
    return out


#: One printed solution block: a header, three axes, then the ratio.
#:     SOLUTION INVDIR (NO 2)  LAMBDA= 0.45
#:     AXIS SIGMA 1     D=  17.     P=  48.
#:     ...
#:     RATIO PHI= 0.490   [(S2-S3)/(S1-S3)]
_BLOCK = re.compile(
    r'SOLUTION\s+(INVDIR|PSIDIR)([^\n]*)\n'      # 1 name, 2 rest of header
    r'(.*?)'                                      # 3 whatever sits between
    r'RATIO\s+PHI=\s*([\d.]+)',                   # 4 the ratio
    re.S)
_AXIS = re.compile(
    r'AXIS\s+SIGMA\s*([123])\s+D=\s*([\d.]+)\.?\s+P=\s*([\d.]+)')


def read_info_solutions(path):
    """Both solution blocks INFO1 prints, with their axes.

    Returns {'INVDIR': block, 'PSIDIR': block} for whichever are present:

        sigma1/2/3  (trend, plunge)
        phi         that block's RATIO PHI
        flag        the text after the block name, e.g. 'PERMUTATION',
                    'AXES OK !', or '(NO 2)  LAMBDA= 0.45'
        permuted    True when the header says PERMUTATION

    Why this is needed at all. `parse_result_line` reads the 03 line, and on
    85 of the 93 archive runs carrying all three values that line's Phi is
    PSIDIR's, never INVDIR's alone. So the 03 line cannot tell you what INVDIR
    said, and anything that records INVDIR values has to come from here.
    """
    with open(path, 'r', errors='replace') as fh:
        txt = fh.read()
    out = {}
    for m in _BLOCK.finditer(txt):
        name, rest, middle, phi = m.groups()
        block = dict(phi=float(phi), flag=rest.strip(),
                     permuted='PERMUT' in rest.upper())
        for a in _AXIS.finditer(rest + '\n' + middle):
            idx, trend, plunge = a.groups()
            block['sigma%s' % idx] = (float(trend) % 360.0, float(plunge))
        if all(('sigma%d' % i) in block for i in (1, 2, 3)):
            out[name] = block
    return out


def discover(root):
    """Find every TENSOR run under a directory tree.

    A run is a folder containing an INFO1 (or MOHR1) plus one extension-less
    file that is not one of the known auxiliary names.
    """
    aux = {'INFO1', 'MOHR1', 'PLOT1', 'HPGL'}
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        if not (aux & set(filenames)):
            continue
        for fn in filenames:
            if fn in aux or '.' in fn:
                continue
            found.append(os.path.join(dirpath, fn))
    return sorted(found)
