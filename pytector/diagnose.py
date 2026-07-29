# -*- coding: utf-8 -*-
"""Which data are badly fitted, and which data are actually deciding the answer.

These are two different questions and they have different answers, which is the
reason for this module.

MISFIT asks how far a datum sits from what the solution predicts. Angelier
already answers it and TENSOR already prints it: ANG, the angle between the
observed striation and the predicted shear, and RUP, the departure in slip
magnitude. INFO1 even bands them with ! and !! against fixed thresholds. A
badly fitted datum is visible in the output as it stands.

INFLUENCE asks something the output does not show: if this datum were not
there, would the answer be different. A datum can fit badly and change nothing,
because eight others outvote it. A datum can fit well and still be holding the
whole solution in place, because it is the only one of its orientation. It is
the second kind that decides whether a station's stress axes mean anything, and
the only honest way to find them is to leave each one out and re-invert.

That is cheap here. INVDIR is a few milliseconds, so a station of thirty faults
is well under a second, and nothing about it needs approximating.
"""
import numpy as np

from . import core

#: Angelier's own bands, the ones INFO1 marks with ! and !!, recovered from the
#: MOHR retention thresholds in the program: RUP 200/75/50 and ANG 180/45/22.5.
ANG_BANDS = (22.5, 45.0)
RUP_BANDS = (50.0, 75.0)


def band(value, bands):
    """'' for clean, '!' for the middle band, '!!' for the worst."""
    if value is None or not np.isfinite(value):
        return ''
    return '' if value < bands[0] else ('!' if value < bands[1] else '!!')


def misfit(res):
    """Per-datum ANG and RUP with Angelier's flags. Nothing recomputed: these
    are the columns the solution already carries."""
    ang = np.asarray(res['ANG'], float)
    rup = np.asarray(res['RUP'], float)
    return [dict(i=i + 1, ANG=float(ang[i]), RUP=float(rup[i]),
                 ang_flag=band(ang[i], ANG_BANDS),
                 rup_flag=band(rup[i], RUP_BANDS))
            for i in range(len(ang))]


def influence(n, s, solver, base=None):
    """Leave one out. How far does the answer move without each datum.

    solver(n, s) -> tensor. Returns one dict per datum with the movement of
    each principal axis in degrees and the change in Phi.

    Reported on sigma1 and sigma3 separately because they are not equally well
    determined: at Phi near 0 sigma2 and sigma3 are nearly interchangeable and
    a large sigma3 movement means very little, while the same movement on
    sigma1 would be serious. Phi is given alongside so that can be judged.
    """
    n = np.atleast_2d(np.asarray(n, float))
    s = np.atleast_2d(np.asarray(s, float))
    k = len(n)
    if k < 5:            # dropping one would leave too few to invert
        return []
    if base is None:
        base = core.describe(solver(n, s))
    out = []
    for i in range(k):
        keep = np.ones(k, bool)
        keep[i] = False
        try:
            T = solver(n[keep], s[keep])
            d = core.describe(T)
        except Exception:
            out.append(dict(i=i + 1, s1=None, s2=None, s3=None, dphi=None,
                            worst=None, ang_out=None, rup_out=None))
            continue
        moves = []
        for key in ('sigma1', 'sigma2', 'sigma3'):
            u = core.vec_from_trend_plunge(*base[key])
            v = core.vec_from_trend_plunge(*d[key])
            moves.append(float(np.degrees(np.arccos(
                min(abs(float(u @ v)), 1.0)))))
        # The DELETED residual: this datum measured against the tensor fitted
        # WITHOUT it. The ordinary ANG is contaminated, because an influential
        # datum drags the solution towards itself and so flatters its own
        # misfit. The deleted one is what the other faults say about it, and it
        # is the number that belongs in a decision to set it aside.
        e = core.estimators(T, n[i:i + 1], s[i:i + 1])
        out.append(dict(i=i + 1, s1=moves[0], s2=moves[1], s3=moves[2],
                        dphi=float(d['phi'] - base['phi']),
                        worst=max(moves[0], moves[2]),
                        ang_out=float(e['ANG'][0]), rup_out=float(e['RUP'][0])))
    return out


#: A datum that moves a well-constrained axis by more than this is worth
#: looking at before the station is used. Not a rejection rule: Angelier's own
#: field error on a striation is 5 to 15 degrees, so movement below that is
#: inside the noise the data were collected with.
INFLUENCE_DEG = 10.0


def combine(res, n, s, solver):
    """Both diagnostics per datum, plus a single flag for the ones to look at.

    flag is '!!' if the datum is both badly fitted and load-bearing, '!' if it
    is one or the other, '' otherwise. Being merely badly fitted is common and
    mostly harmless; being load-bearing AND badly fitted is what to check.
    """
    m = misfit(res)
    inf = {d['i']: d for d in influence(n, s, solver)}
    out = []
    for d in m:
        g = inf.get(d['i'], {})
        bad = bool(d['ang_flag'] or d['rup_flag'])
        heavy = (g.get('worst') is not None and g['worst'] > INFLUENCE_DEG)
        row = dict(d)
        # severe = the far band, the one INFO1 marks '!!'
        severe = d['ang_flag'] == '!!' or d['rup_flag'] == '!!'
        row.update(s1_move=g.get('s1'), s3_move=g.get('s3'),
                   worst_move=g.get('worst'), dphi=g.get('dphi'),
                   ANG_out=g.get('ang_out'), RUP_out=g.get('rup_out'),
                   badly_fitted=bad, load_bearing=heavy, severe=severe,
                   flag=('!!' if bad and heavy else ('!' if bad or heavy
                                                     else '')),
                   # What goes on the diagram, which is a stricter question
                   # than what goes in the table. Merely fitting imperfectly is
                   # the normal condition of field data -- at site 0406-7 it is
                   # 18 of 29 -- and ringing all of them says nothing. The
                   # diagram marks the ones that change the answer, and the
                   # ones so far out that they are probably not the same event.
                   plot_mark=('!!' if heavy else ('!' if severe else '')))
        out.append(row)
    return out


def disclosure(rows, n, s, solver, drop=None):
    """What to put in the paper when one striation is unlike the others.

    Setting a datum aside is a legitimate thing to do and a silent thing to
    hide. The difference is entirely in what gets reported, so this produces
    the block that makes it honest: the solution with everything in, the
    solution without the data being set aside, and the movement between them.
    If excluding one fault swings sigma1 by twenty degrees, that belongs on the
    page next to the number, not behind it.

    This is also Angelier's own habit. INFO1 never prints a single mean: it
    prints the statistic over all data AND over the subset inside the
    threshold, with the counts in each band, so a reader can see how much of
    the quality came from trimming.

    drop  1-based indices to exclude; defaults to everything flagged for the
          diagram, i.e. load-bearing or far outside the bands.
    """
    n = np.atleast_2d(np.asarray(n, float))
    s = np.atleast_2d(np.asarray(s, float))
    if drop is None:
        drop = [r['i'] for r in rows if r['plot_mark']]
    drop = sorted(set(int(i) for i in drop))
    keep = np.ones(len(n), bool)
    for i in drop:
        if 1 <= i <= len(n):
            keep[i - 1] = False

    full = core.describe(solver(n, s))
    out = dict(n_total=len(n), dropped=drop, n_kept=int(keep.sum()),
               full=full, trimmed=None, moves=None)
    if not drop or keep.sum() < 4:
        return out
    trim = core.describe(solver(n[keep], s[keep]))
    moves = []
    for key in ('sigma1', 'sigma2', 'sigma3'):
        u = core.vec_from_trend_plunge(*full[key])
        v = core.vec_from_trend_plunge(*trim[key])
        moves.append(float(np.degrees(np.arccos(min(abs(float(u @ v)), 1.0)))))
    out.update(trimmed=trim, moves=moves)
    return out


def disclosure_text(d, rows=None):
    """The block above, written out."""
    L = []
    f = d['full']
    L.append('%-26s %-9s %-9s %-9s %s'
             % ('', 'sigma1', 'sigma2', 'sigma3', 'Phi'))
    L.append('%-26s %-9s %-9s %-9s %.3f'
             % ('all %d data' % d['n_total'],
                '%03.0f/%02.0f' % f['sigma1'], '%03.0f/%02.0f' % f['sigma2'],
                '%03.0f/%02.0f' % f['sigma3'], f['phi']))
    if d['trimmed'] is None:
        L.append('nothing set aside.')
        return '\n'.join(L)
    t = d['trimmed']
    L.append('%-26s %-9s %-9s %-9s %.3f'
             % ('without %s' % ','.join(str(i) for i in d['dropped']),
                '%03.0f/%02.0f' % t['sigma1'], '%03.0f/%02.0f' % t['sigma2'],
                '%03.0f/%02.0f' % t['sigma3'], t['phi']))
    m = d['moves']
    L.append('%-26s %-9s %-9s %-9s %+.3f'
             % ('the axes move', '%.1f deg' % m[0], '%.1f deg' % m[1],
                '%.1f deg' % m[2], t['phi'] - f['phi']))
    L.append('')
    if rows:
        by_i = {r['i']: r for r in rows}
        L.append('%-4s %8s %8s %9s %9s  %s'
                 % ('n', 'ANG', 'ANG*', 'RUP', 'RUP*', 'what it is'))
        for i in d['dropped']:
            r = by_i.get(i)
            if not r:
                continue
            why = []
            if r.get('load_bearing'):
                why.append('moves an axis %.1f deg' % (r['worst_move'] or 0))
            if r.get('severe'):
                why.append('outside the far band')
            L.append('%-4d %8.1f %8s %9.1f %9s  %s'
                     % (i, r['ANG'],
                        '-' if r.get('ANG_out') is None
                        else '%.1f' % r['ANG_out'],
                        r['RUP'],
                        '-' if r.get('RUP_out') is None
                        else '%.1f' % r['RUP_out'],
                        '; '.join(why)))
        L.append('ANG* and RUP* are measured against the solution fitted '
                 'WITHOUT that datum, so they are not')
        L.append('flattered by its own pull on the answer. Report those, not '
                 'the plain ANG and RUP.')
    return '\n'.join(L)


def text_table(rows, limit=None):
    """The rows worth reading, as fixed-width text for the report pane."""
    if not rows:
        return ''
    hot = [r for r in rows if r['flag']]
    hot.sort(key=lambda r: (-(r['worst_move'] or 0), -r['ANG']))
    if limit:
        hot = hot[:limit]
    L = ['%-4s %7s %7s %9s %9s %8s  %s'
         % ('n', 'ANG', 'RUP', 'd sigma1', 'd sigma3', 'd Phi', 'why')]
    for r in hot:
        why = []
        if r['badly_fitted']:
            why.append('fits badly')
        if r['load_bearing']:
            why.append('holds the answer')
        L.append('%-4d %6.1f%-2s %5.1f%-2s %9s %9s %8s  %s'
                 % (r['i'], r['ANG'], r['ang_flag'], r['RUP'], r['rup_flag'],
                    '-' if r['s1_move'] is None else '%.1f' % r['s1_move'],
                    '-' if r['s3_move'] is None else '%.1f' % r['s3_move'],
                    '-' if r['dphi'] is None else '%+.3f' % r['dphi'],
                    ' and '.join(why)))
    if not hot:
        return 'every datum fits inside Angelier\'s bands and none of them ' \
               'moves an axis by more than %.0f degrees.' % INFLUENCE_DEG
    return '\n'.join(L)
