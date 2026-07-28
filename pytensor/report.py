# -*- coding: utf-8 -*-
"""Write INFO1 and MOHR1 in TENSOR's own layout.

Column positions were read character by character off the archive files and
are verified by tests/test_report.py, which regenerates L12 and 0406-7 from
their recorded solutions and diffs against the originals.

Per-fault line, INFO1 (0-based column spans):

     0- 6  record number, right aligned, followed by '.'
     7-13  weight, one decimal
    14-22  SIGMA  x100
    23-27  SIGMN  x100
    28-32  TAU    x100
    33-37  TAUST  x100
    38-47  RMU    per cent
    48-54  RUP    per cent
    55-56  RUP flag: '!!' over 75, '!' over 50, else blank
    57-62  OBL    degrees
    63-70  ANG    degrees
    71-72  ANG flag: '!!' from 45 up, '!' over 22.5, else blank

MOHR1:

    line 1   '02' then eigenvalues S1 S2 S3 and PHI, each %8.3f
    rows     SIGMN %10.3f then TAU, TAUST, RUP, ANG each %8.3f
    last     the same '03' result line that INFO1 carries

Identification: the banner names pyTENSOR rather than claiming to be
TENSOR 5.45. Everything a downstream reader parses (the fixed-width data
lines and the '03' record) keeps the original layout, so the files still
round-trip through pytensor.tensorfile.
"""
import numpy as np

from . import __version__
from .core import estimators, describe

HEAD = """\
 >>>>>>>>>>> FILE READY TO BE CREATED  : INFO1
 pyTENSOR, A PYTHON RECONSTRUCTION OF THE PROGRAMS BY JACQUES ANGELIER,
 QUANTITATIVE TECTONICS, UNIVERSITY P. M. CURIE, 75252 PARIS CEDEX 05, FRANCE.

              ****************************************************
              *** DATA BASE FOR TECTONIC ORIENTATIONS "TECTOR" ***
              ****************************************************

 >>>>>>>>>>> FILE READY TO BE CREATED  : MOHR1
               pyTENSOR {ver}, after Progr. TENSOR 5.45 (jan91)
               method and layout: J. Angelier, 1975-1991
               ++++++++++++++++++++++++++++++++++++++++++++++
               ++++  CALCUL DU  TENSEUR DES CONTRAINTES  ++++
               ++++    DETERMINATION OF STRESS TENSOR    ++++
               ++++++++++++++++++++++++++++++++++++++++++++++


 REFERENCES OF TENSOR DETERMINATION METHODS :
 INVDIR : DIRECT INVERSION. - the criterion minimises a
  function that depends on both the slip-shear angle and
  the shear, the function described as S4 by J. Angelier
  (1984) [Journal of Geophys.Res.,89,B7,5835-5848]. The
  method is described in detail in J. Angelier (1990),
  Geophysical J. International, 103, 363-376.
  pyTENSOR reproduces it in Angelier's own (alpha, beta,
  gamma, psi) parametrisation, so the LAMBDA adjustment
  and the PSIDIR step behave as in the original.
 MODE B : the same criterion, minimised globally with
  lambda held at its converged value sqrt(3)/2. It reaches
  a lower S4 than the original program does, because the
  original stops the lambda adjustment early. Use INVDIR
  to reproduce archive numbers and MODE B when the
  question is what the data support.
"""

TAIL = """\
 >>>>>>>>>>>> CLOSING OF FILE MODIFIED : {site:<42}
 >>>>>>>>>>>> CLOSING OF FILE CREATED  : MOHR1
 >>>>>>>>>>>> CLOSING OF FILE CREATED  : INFO1
"""


def _flag(value, hi, mid):
    if value > hi:
        return '!!'
    if value > mid:
        return '!'
    return ''


#: the archive indents the solution blocks by 20 columns; on screen that just
#: pushes everything to the right, so the compact form uses 2
INDENT_FILE = ' ' * 20
INDENT_SCREEN = ' ' * 2


def _axis_lines(res, indent=INDENT_FILE):
    """Trends are printed as rounded, NOT reduced modulo 360: the archive
    writes 'D= 360.' for a trend of 359.6."""
    out = []
    for i, key in enumerate(('sigma1', 'sigma2', 'sigma3')):
        tr, pl = res[key]
        out.append('%sAXIS SIGMA %d     D=%4d.     P=%4d.'
                   % (indent, i + 1, int(round(tr)), int(round(pl))))
    return out


def result_line(res, n, method='INVD', acc=9, site='01', record=1,
                total=None):
    """The fixed-width '03' line that both files end with."""
    total = float(n if total is None else total)
    s1, s2, s3 = res['sigma1'], res['sigma2'], res['sigma3']
    return ('03%-4s%02d%5.1f%4.1f%5.1f%4.1f%5.1f%4.1f%5.3f%4.1f%5.1f'
            '%02d%02d%4d.%3d%2s%9d'
            % (method, acc,
               s1[0], s1[1], s2[0], s2[1], s3[0], s3[1],
               res['phi'], res['ANG_mean'], res['RUP_mean'],
               acc, 19, int(round(total)), n, site, record))


def mohr1_text(res, n_data, method='INVD', site='01', record=1):
    """MOHR1: eigenvalues, then one row per datum at full precision."""
    w = np.sort(np.asarray(res['eigenvalues'], float))[::-1]
    lines = ['02%8.3f%8.3f%8.3f%8.3f' % (w[0], w[1], w[2], res['phi'])]
    for i in range(n_data):
        lines.append('%10.3f%8.3f%8.3f%8.3f%8.3f'
                     % (res['SIGMN'][i], res['TAU'][i], res['TAUST'][i],
                        res['RUP'][i], res['ANG'][i]))
    lines.append(result_line(res, n_data, method=method, site=site,
                             record=record))
    return '\n'.join(lines) + '\n'


def info1_text(site_file, res, n_data, invdir=None, lam_invdir=None,
               pass_no=1, weights=None, site='01', method='INVD',
               acc=9, record=1, full_header=True, compact=False):
    """INFO1, in the original layout.

    res           the final (PSIDIR) solution, from core.summary
    invdir        the INVDIR solution before PSIDIR, if there was one
    full_header   the reference banner at the top of the file
    compact       drop the banner and the file-handling furniture and keep
                  only the substance: the two solution blocks, the per-fault
                  table, the summary and the result line. This is what the
                  interface shows; exported files get the full thing.
    """
    L = []
    if compact:
        L.append('  SITE %-10s  %2d fault slips  %s, pass NO %d'
                 % (site, n_data, method, pass_no))
        L.append('')
    else:
        if full_header:
            L.extend(HEAD.format(ver=__version__).rstrip('\n').split('\n'))
            L.append('')
        L.append(' >>>>>>>>>>> FILE READY TO BE MODIFIED : %-42s' % site_file)
        L.append(' -----> SITE FOUND : %-12s' % site)
        L.append('  %3d FAULT SLIP DATA RETAINED !' % n_data)
        L.append('')
        bar = ' ' + '*' * 72

        def boxed(text):
            """' * ' + 69 columns + '*' keeps the frame exactly 73 wide."""
            return ' * ' + text[:69].ljust(69) + '*'

        L.append(bar)
        L.append(boxed('PROGRAM pyTENSOR, OPTION %-4s  ACC=%d PON=1   REF.  1'
                       '   AFTER ANGELIER' % (method, acc)))
        L.append(boxed('SITE %-14s SEL=CPS WEI=0-9 AGE=9****(9)   NBR=%3d'
                       ' TOT=%3d.' % (site, n_data, n_data)))
        L.append(bar)
        L.append('')
        L.append('')

    ind = INDENT_SCREEN if compact else INDENT_FILE

    if invdir is not None:
        L.append('%sSOLUTION INVDIR (NO %d)  LAMBDA=%5.2f'
                 % (ind, pass_no,
                    0.0 if lam_invdir is None else lam_invdir))
        L.extend(_axis_lines(invdir, ind))
        L.append('%sRATIO PHI=%6.3f   [(S2-S3)/(S1-S3)]'
                 % (ind, invdir['phi']))
        L.append('')

    w = np.sort(np.asarray(res['eigenvalues'], float))[::-1]
    L.append('%sSOLUTION PSIDIR            AXES OK !' % ind)
    L.append('%sLAMBDA=%5.2f            TAUMAX=%5.2f'
             % (ind, np.sqrt(3) / 2, (w[0] - w[2]) / 2))
    L.append('%sS1=%5.2f      S2=%5.2f      S3=%5.2f'
             % (ind, w[0], w[1], w[2]))
    L.extend(_axis_lines(res, ind))
    L.append('%sRATIO PHI=%6.3f   [(S2-S3)/(S1-S3)]' % (ind, res['phi']))
    L.append('')

    L.append(' NUMERO  POIDS     SIGMA SIGMN TAU TAUST     RMU     RUP'
             '     OBL     ANG ')
    L.append(' NUMBER WEIGHT      <------ x100 ----->      (%)     (%)'
             '    (deg)   (deg) ')
    wts = [1.0] * n_data if weights is None else list(weights)
    for i in range(n_data):
        rup, ang = res['RUP'][i], res['ANG'][i]
        # the two flag fields are two characters wide and RIGHT aligned, so
        # '!!' butts against the number and a single '!' gets a space first
        L.append('%6d.%7.1f%9d%5d%5d%5d%10d%7d%2s%6d%8d%2s'
                 % (i + 1, wts[i],
                    round(res['SIGMA'][i] * 100), round(res['SIGMN'][i] * 100),
                    round(res['TAU'][i] * 100), round(res['TAUST'][i] * 100),
                    round(res['RMU'][i]), round(rup),
                    _flag(rup, 75, 50),
                    round(res['OBL'][i]), round(ang),
                    _flag(ang, 45 - 1e-9, 22.5)))
    L.append('')

    def m(key, scale=1.0, mask=None):
        v = np.asarray(res[key], float) * scale
        if mask is not None:
            v = v[mask]
        if not len(v):
            return 0, 0
        return round(v.mean()), round(v.std())

    # the columns headed "<75" and "<45" are the SAME statistic taken over the
    # subset that passes the threshold, not a repeat of the previous column.
    # 0406-7: mean ANG is 21 over all 29, but 15 over the 28 below 45, the
    # difference being the one datum at 174 degrees.
    rup_ok = np.asarray(res['RUP'], float) < 75
    ang_ok = np.asarray(res['ANG'], float) < 45

    L.append(' n=%3d             SIGMA SIGMN TAU TAUST     RMU   RUP <75'
             '  OBL   ANG <45 ' % n_data)
    L.append(' t=%3d.             <------ x100 ----->      (%%)   <-(%%)->'
             ' (deg)  <-deg-> ' % n_data)
    cols = [m('SIGMA', 100), m('SIGMN', 100), m('TAU', 100), m('TAUST', 100),
            m('RMU'), m('RUP'), m('RUP', mask=rup_ok), m('OBL'),
            m('ANG'), m('ANG', mask=ang_ok)]
    for k, tag in ((0, '       MOYENNE/MEAN'), (1, '       ECART-/S.DEV')):
        L.append('%s%4d%5d%5d%5d%10d%6d%4d%5d%6d%4d'
                 % (tag, cols[0][k], cols[1][k], cols[2][k], cols[3][k],
                    cols[4][k], cols[5][k], cols[6][k], cols[7][k],
                    cols[8][k], cols[9][k]))

    ang = np.asarray(res['ANG'], float)
    rup = np.asarray(res['RUP'], float)
    n0a, n1a, n2a = (ang < 45).sum(), (ang >= 45).sum(), \
        ((ang < 45) & (ang > 22.5)).sum()
    n0r, n1r, n2r = (rup < 75).sum(), (rup > 75).sum(), \
        ((rup <= 75) & (rup > 50)).sum()
    L.append(' ang: (<45) n0,t0=%4d%4d     (!!) n1,t1=%4d%4d'
             '     (!) n2,t2=%4d%4d' % (n0a, n0a, n1a, n1a, n2a, n2a))
    L.append(' rup: (<75) n0,t0=%4d%4d     (!!) n1,t1=%4d%4d'
             '     (!) n2,t2=%4d%4d' % (n0r, n0r, n1r, n1r, n2r, n2r))
    # INFO1 indents the result line by one space; MOHR1 and the data file
    # do not.
    L.append(' ' + result_line(res, n_data, method=method, acc=acc, site=site,
                               record=record))
    if not compact:
        L.append('')
        L.append('          -----> END OF SITE %-12s' % site)
        L.append('')
        L.extend(TAIL.format(site=site_file).rstrip('\n').split('\n'))
    return '\n'.join(L) + '\n'
