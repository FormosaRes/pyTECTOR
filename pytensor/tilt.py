# -*- coding: utf-8 -*-
"""Back-tilt diagnostics, and the incremental restoration test.

Why this is not just "rotate the reference plane back to horizontal"
-------------------------------------------------------------------
That is only right when the faults formed BEFORE the tilting. If they formed
during it, part of the tilt post-dates them and only that part should be
removed; restoring the full amount then over-rotates the data and gives a
stress tensor that never existed. There is no way to tell which case you have
from a single rotation, so the useful thing is to sweep the restoration and
look at how the answer behaves.

Two criteria are offered, because they can disagree and the disagreement is
itself informative.

**Fit.** How well a common stress tensor explains the data, as mean ANG or S4.
This is the classical incremental tilt test: if the faults predate the tilting,
the fit improves as you restore and is best near full restoration.

**Andersonian misfit.** How far the solution is from having one principal axis
vertical and the other two horizontal, which is what a stress state in a
horizontal crust looks like. Reported as 90 minus the plunge of the steepest
axis, so zero is Andersonian. Which axis ends up vertical names the regime:
sigma1 normal, sigma2 strike-slip, sigma3 thrust.

Neither is proof. A fault set can fit well at a restoration that is
geologically wrong, and an Andersonian result can be a coincidence. They are
diagnostics to look at, not a solver for the angle.
"""
import numpy as np

from . import core, rotate


def andersonian(result):
    """How far a solution is from one vertical and two horizontal axes.

    Returns (misfit_degrees, regime, steep_axis). Misfit is 90 minus the
    plunge of the steepest axis; the other two follow by orthogonality.
    """
    plunges = [result[k][1] for k in ('sigma1', 'sigma2', 'sigma3')]
    i = int(np.argmax(plunges))
    regime = {0: 'normal', 1: 'strike-slip', 2: 'thrust'}[i]
    return 90.0 - float(plunges[i]), regime, ('sigma1', 'sigma2', 'sigma3')[i]


def sweep(n, s, trend, plunge, angle, runner, fractions=None):
    """Invert at a series of partial restorations of the same rotation.

    fraction 0.0 leaves the data as measured, 1.0 applies the whole rotation.
    Values above 1.0 are allowed and worth looking at: a best fit beyond full
    restoration says the reference surface does not carry the whole story.

    runner(n, s) -> tensor, so the caller decides INVDIR or S4MIN.
    """
    if fractions is None:
        fractions = np.linspace(0.0, 1.25, 26)
    out = []
    for f in fractions:
        nr, sr = (rotate.rotate_site(n, s, trend, plunge, angle * f)
                  if f else (np.asarray(n, float), np.asarray(s, float)))
        T = runner(nr, sr)
        res = core.summary(T, nr, sr)
        mis, regime, steep = andersonian(res)
        out.append(dict(fraction=float(f), angle=float(angle * f),
                        T=T, result=res,
                        ANG=res['ANG_mean'], RUP=res['RUP_mean'],
                        S4=res['S4'], phi=res['phi'],
                        sigma1=res['sigma1'], sigma2=res['sigma2'],
                        sigma3=res['sigma3'],
                        andersonian=mis, regime=regime, steep=steep))
    return out


def best(sweep_rows, key='ANG'):
    """The restoration that optimises a criterion.

    'ANG', 'RUP', 'S4' and 'andersonian' are all minimised.
    """
    return min(sweep_rows, key=lambda r: r[key])


def summarise(sweep_rows):
    """A short reading of the sweep, for printing or for the interface."""
    b_fit = best(sweep_rows, 'ANG')
    b_and = best(sweep_rows, 'andersonian')
    zero = sweep_rows[0]
    full = min(sweep_rows, key=lambda r: abs(r['fraction'] - 1.0))
    lines = [
        'as measured        ANG %5.1f   Andersonian misfit %5.1f   %s'
        % (zero['ANG'], zero['andersonian'], zero['regime']),
        'fully restored     ANG %5.1f   Andersonian misfit %5.1f   %s'
        % (full['ANG'], full['andersonian'], full['regime']),
        'best fit at        %3.0f %% of the rotation   ANG %5.1f'
        % (100 * b_fit['fraction'], b_fit['ANG']),
        'most Andersonian   %3.0f %% of the rotation   misfit %5.1f   %s'
        % (100 * b_and['fraction'], b_and['andersonian'], b_and['regime']),
    ]
    gap = abs(b_fit['fraction'] - b_and['fraction'])
    if gap > 0.2:
        lines.append(
            'the two criteria disagree by %.0f %% of the rotation, which is '
            'worth explaining before trusting either' % (100 * gap))
    if b_fit['fraction'] < 0.8:
        lines.append(
            'best fit well short of full restoration is what syn-tilt '
            'faulting looks like: part of the tilt post-dates the faults')
    return lines
