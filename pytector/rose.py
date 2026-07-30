# -*- coding: utf-8 -*-
"""Rose diagrams and circular statistics for orientation data.

Angelier's own programs had no rose diagram: DIAGRA plots stereograms, and a
rose of one site's three stress axes would be three points. A rose earns its
place across MANY determinations, which is where the question "what direction
did this phase actually act in" gets asked.

Two decisions are built in, and both matter enough to state.

**Axial, not directional.** A stress axis and a fault strike have no
arrowhead: 020 and 200 are the same line. The ordinary circular mean is
therefore wrong here, because those two would cancel to nothing instead of
reinforcing. The fix is the doubled-angle method: work in 2*theta, where the
two ends of a line coincide, average there, and halve back. `axial_stats`
does this; feeding it 020 and 200 returns R = 1, not R = 0.

**A trend is only a direction if its axis is shallow.** For a steeply plunging
axis the trend is nearly arbitrary, and averaging it in adds noise that looks
like signal. `shallow_only` filters on plunge, and the drawing routine reports
how many it dropped rather than quietly thinning the sample. The default
threshold is the same 45 degrees that Angelier's own operators used when
deciding whether a plate got compression and extension arrows at all (see
plot.ARROW_PLUNGE_LIMIT).

One more trap, learned the hard way on real data: do not build a rose from
"whichever axis is shallowest at each station". sigma2 and sigma3 are
perpendicular, so mixing them cancels. On a 25-station set that mistake took
the resultant from 0.78 down to 0.13. Pick one axis for the whole group and
let `shallow_only` tell you whether that axis is usable.
"""
import math

#: Above this plunge a trend is not treated as a direction.
SHALLOW_LIMIT = 45.0


def axial_stats(trends):
    """Mean direction and concentration of axial (bidirectional) trends.

    trends   iterable of azimuths in degrees, any range
    returns  None for fewer than two values, else a dict with

        n      how many went in
        mean   mean trend in 0-180; the axis, so the other end is mean + 180
        R      resultant length of the doubled angles, 0 to 1. 1 means every
               axis parallel, 0 means no preferred direction
        sd     circular standard deviation of the axis in degrees, or None
               when R is too small for it to mean anything
    """
    vals = [float(t) % 360.0 for t in trends if t is not None]
    if len(vals) < 2:
        return None
    sx = sum(math.cos(math.radians(2 * t)) for t in vals)
    sy = sum(math.sin(math.radians(2 * t)) for t in vals)
    n = len(vals)
    R = math.hypot(sx, sy) / n
    mean = (math.degrees(math.atan2(sy, sx)) % 360.0) / 2.0 % 180.0
    # Below this the axes have no preferred direction and the formula runs
    # away: two perpendicular axes give R = 1e-17 and a "standard deviation"
    # of 247 degrees, which is not a number to put in a caption.
    if R < 0.05:
        sd = None
    else:
        sd = abs(math.degrees(math.sqrt(-2.0 * math.log(min(1.0, R)))) / 2.0)
    return dict(n=n, mean=mean, R=R, sd=sd)


def histogram(trends, bin_deg=10.0):
    """Counts per bin over the full circle, both ends of every axis added.

    Returns (edges, counts), edges in degrees. Both ends are counted so the
    rose is symmetric, which is how an axial rose is drawn; the counts
    therefore sum to twice the number of input values.
    """
    nb = int(round(360.0 / bin_deg))
    counts = [0] * nb
    for t in trends:
        if t is None:
            continue
        for a in (float(t) % 360.0, (float(t) + 180.0) % 360.0):
            counts[int(a // bin_deg) % nb] += 1
    return [i * bin_deg for i in range(nb)], counts


def shallow_only(axes, limit=SHALLOW_LIMIT):
    """Split (trend, plunge) pairs into the usable trends and a dropped count.

    Returns (trends, n_dropped). A pair whose plunge is at or beyond `limit`
    is dropped, because its trend is not a direction.
    """
    keep, dropped = [], 0
    for a in axes:
        if not a:
            continue
        trend, plunge = a
        if plunge < limit:
            keep.append(trend)
        else:
            dropped += 1
    return keep, dropped


#: house palette, matching the stereograms rather than competing with them
INK = '#1E1E1C'
FILL = '#B9B2A0'
MEAN_INK = '#23324A'
FAINT = '#7A776F'


def plot_rose(ax, axes, bin_deg=10.0, limit=SHALLOW_LIMIT, title=None,
              emphasis=False, show_mean=True):
    """Draw an axial rose on a polar Axes and return its statistics.

    ax        a matplotlib polar Axes
    axes      iterable of (trend, plunge) pairs, or of bare trends
    limit     plunge beyond which a trend is dropped; None keeps everything
    emphasis  draw the title bold, for marking the panel worth reading
    returns   the axial_stats dict, or None

    The subtitle always states n and how many were dropped, so a thinned
    sample cannot be mistaken for a complete one.
    """
    import numpy as np

    pairs = []
    for a in axes:
        if a is None:
            continue
        if isinstance(a, (int, float)):
            pairs.append((float(a), 0.0))
        else:
            pairs.append((float(a[0]), float(a[1])))
    if limit is None:
        trends, dropped = [t for t, _p in pairs], 0
    else:
        trends, dropped = shallow_only(pairs, limit)

    edges, counts = histogram(trends, bin_deg)
    st = axial_stats(trends)

    ax.set_theta_zero_location('N')       # geographic: north up
    ax.set_theta_direction(-1)            # and clockwise
    ax.set_thetagrids(range(0, 360, 30),
                      labels=['%03d' % d for d in range(0, 360, 30)],
                      fontsize=7)
    ax.tick_params(pad=1)

    top = max(counts) if counts else 0
    if top > 0:
        width = math.radians(bin_deg)
        theta = np.radians(np.asarray(edges, float))
        ax.bar(theta + width / 2, counts, width=width * 0.92, bottom=0.0,
               color=FILL, edgecolor=INK, linewidth=0.6, zorder=3)
        ax.set_ylim(0, top * 1.15)
        ax.set_yticks(range(0, top + 1, max(1, top // 3)))
        ax.tick_params(axis='y', labelsize=6, colors=FAINT)
        if show_mean and st:
            for a in (st['mean'], st['mean'] + 180.0):
                ax.plot([math.radians(a)] * 2, [0, top * 1.12],
                        color=MEAN_INK, lw=1.8, zorder=5)
    else:
        ax.text(0, 0, 'no usable axis', ha='center', va='center',
                fontsize=8, color='#A9A59C')
        ax.set_ylim(0, 1)
        ax.set_yticks([])

    if title is not None:
        sub = 'n = %d' % len(trends)
        if dropped:
            sub += ', %d too steep' % dropped
        if st:
            sub += '\nmean %03.0f, R %.2f' % (st['mean'], st['R'])
            if st['sd'] is not None:
                sub += ', sd %.0f deg' % st['sd']
        ax.set_title('%s\n%s' % (title, sub), fontsize=8.5, color=INK,
                     pad=24, linespacing=1.5,
                     fontweight='600' if emphasis else 'normal')
    return st


def pick_readable(groups):
    """Of several candidate axes for one group, which rose is worth reading.

    groups   dict of label -> list of (trend, plunge)
    returns  the label with the most usable axes, R breaking a tie

    Written because the answer changes between phases and getting it wrong is
    silent: a set whose sigma1 all plunge steeply has an empty compression
    rose and a perfectly good extension one.
    """
    best, best_key = None, None
    for label, axs in groups.items():
        trends, _d = shallow_only(axs)
        st = axial_stats(trends)
        key = (len(trends), (st or {}).get('R', 0.0))
        if best_key is None or key > best_key:
            best, best_key = label, key
    return best
