# -*- coding: utf-8 -*-
"""Schmidt (equal area) lower hemisphere plotting in Angelier's own style.

The style is not inferred from the figure captions: it is copied from the HPGL
files the original program wrote, which are plain-text plotter vectors and so
record exactly what TENSOR drew. See pytensor.hpgl and render_hpgl.py.

What the originals do:

  * square frame box around the whole plot
  * primitive circle, ticks at N/E/S/W only, small cross at the centre
  * "N" and "M" marks at the top (geographic and magnetic north)
  * fault planes as thin great circles
  * slickenside lineations as filled dots with thin open arrows; outward
    directed means normal
  * stress axes as STAR POLYGON OUTLINES: five points for sigma1, four for
    sigma2, three for sigma3, drawn largest to smallest in that order
  * two pairs of heavy solid arrows outside the circle: pointing INWARD along
    the sigma1 trend (compression) and OUTWARD along the sigma3 trend
    (extension)
  * site code centred at the top, header string bottom left, program name
    bottom right

Monochrome throughout. No Qt import here, so this module works headless.
"""
import numpy as np

from .core import vec_from_trend_plunge

#: Star geometry, measured off the archive HPGL (see extract_glyphs.py).
#: sigma1 gets a 5-pointed star, sigma2 a 4-pointed one, sigma3 a 3-pointed
#: one. PHASE is the azimuth of one tip, in the plot frame, degrees CCW from
#: the +x axis: the 5- and 3-pointed stars have a tip pointing up, the
#: 4-pointed one is set diagonally.
STAR_POINTS = (5, 4, 3)
STAR_PHASE = (90.0, 45.0, 90.0)
STAR_INNER = (0.494, 0.395, 0.293)      # inner / outer radius

#: The size is not constant: TENSOR scales each star with its own eigenvalue.
#: Fitted over 21 archive plots (63 stars), rms 0.00063, max error 0.00162,
#: which is 1 per cent of the observed size range. At Phi = 0.5 all three come
#: out equal, which is why the size ORDER flips either side of it.
#:     size_i = STAR_BASE + STAR_GAIN * (0.5 - Phi) * lambda_i
STAR_BASE = 0.1004
STAR_GAIN = 0.0928

#: Heavy stress-direction arrow, measured off the archive. Radii are in units
#: of the primitive radius; the arrow lies outside the circle. The same
#: template serves both senses, run outwards or inwards.
ARROW_TAIL = 1.022      # blunt end
ARROW_BARB = 1.099      # where the barbs sit
ARROW_TIP = 1.201      # the point
ARROW_BARB_HALF = 0.102
ARROW_SHAFT_HALF = 0.051

#: Frame furniture, measured stroke by stroke off the archive HPGL
#: (see dump_first.py). All distances are in units of the primitive radius.
#: The box is a PORTRAIT RECTANGLE, not a square.
FRAME_W = 1.2528        # half width
FRAME_H = 1.4570        # half height
FRAME = FRAME_W         # kept for callers that want a single number

TICK_IN = 1.0000        # cardinal ticks run OUTWARD from the circle only
TICK_OUT = 1.1019
CROSS_ARM = 0.1019      # centre cross half-length

#: The letters are pen strokes, not typeset. Coordinates are relative to each
#: letter's own base point; both are 0.052 wide and 0.052 tall.
LETTER_BASE = 1.0974
LETTER_H = 0.0519
LETTER_HALF = 0.0260
#: "N": up the left stroke, diagonal down to bottom right, up the right stroke
LETTER_N = [(-1, 0), (-1, 1), (1, 0), (1, 1)]
#: "M": up the right, down to the middle, up the left, down
LETTER_M = [(1, 0), (1, 1), (0, 0.5), (-1, 1), (-1, 0)]

#: Magnetic north: the pointer leaves the primitive at this azimuth, rises
#: radially to an elbow, then doglegs across to sit under the M. The M letter
#: is parked at 5.18 deg so it clears the N.
MAGNETIC_OFFSET = 1.95
MAGNETIC_LETTER_X = 0.1019
MAGNETIC_ELBOW_R = 1.0474

#: One pen drew everything, so every stroke carries the same weight.
LW = 0.9

LABEL = (r'$\sigma_1$', r'$\sigma_2$', r'$\sigma_3$')

PROGRAM_TAG = 'pyTENSOR'

#: Ink and paper for everything drawn here. The originals are black on white,
#: which is the default. 1991 mode swaps in phosphor green on black; set these
#: two before drawing rather than threading a colour through every call.
PEN = 'k'
PAPER = 'white'

#: Antialiasing. Off gives hard stair-stepped edges, which is how a 1991
#: display actually drew a line; it reads as pixellated rather than as a
#: blurred thick stroke.
AA = True
#: stroke weight, raised a little when aliased so the steps are visible
STROKE = LW


def set_palette(pen='k', paper='white', aa=True, stroke=None):
    global PEN, PAPER, AA, STROKE
    PEN, PAPER, AA = pen, paper, aa
    STROKE = LW if stroke is None else stroke


# ------------------------------------------------------------- projection ---
def schmidt(v):
    """Equal-area (Schmidt) projection onto the lower hemisphere.

    x = East, y = North, z = Up. Vertical plots at the centre, horizontal on
    the unit circle:  R = sqrt(1 - sin(plunge)).
    """
    v = np.atleast_2d(np.asarray(v, float))
    v = np.where((v[:, 2] > 0)[:, None], -v, v)
    R = np.sqrt(np.maximum(1.0 - (-v[:, 2]), 0.0))
    h = np.hypot(v[:, 0], v[:, 1])
    with np.errstate(invalid='ignore', divide='ignore'):
        ux = np.where(h > 1e-12, v[:, 0] / h, 0.0)
        uy = np.where(h > 1e-12, v[:, 1] / h, 0.0)
    return ux * R, uy * R


def great_circle(normal, n_pts=541):
    """Lower-hemisphere arc(s) of a plane, split at the primitive so no chord
    is drawn across the diagram."""
    nrm = np.asarray(normal, float)
    nrm = nrm / np.linalg.norm(nrm)
    a = np.array([0.0, 0.0, 1.0])
    if abs(float(nrm @ a)) > 0.95:
        a = np.array([1.0, 0.0, 0.0])
    u = np.cross(nrm, a)
    u /= np.linalg.norm(u)
    w = np.cross(nrm, u)
    t = np.linspace(0, 2 * np.pi, n_pts)
    pts = np.outer(np.cos(t), u) + np.outer(np.sin(t), w)
    keep = pts[:, 2] <= 1e-12
    X, Y = schmidt(pts)
    segs, cur = [], []
    for i in range(len(X)):
        if keep[i]:
            cur.append((X[i], Y[i]))
        elif len(cur) > 1:
            segs.append(np.array(cur))
            cur = []
        else:
            cur = []
    if len(cur) > 1:
        segs.append(np.array(cur))
    return segs


# ------------------------------------------------------------------ shapes --
def star_polygon(x, y, n_points, size, inner=0.40, phase_deg=90.0):
    """Vertices of an n-pointed star outline, as Angelier draws his axes."""
    k = np.arange(2 * n_points)
    ang = np.radians(phase_deg) + k * np.pi / n_points
    rad = np.where(k % 2 == 0, size, size * inner)
    return x + rad * np.cos(ang), y + rad * np.sin(ang)


def star_sizes(phi, eigenvalues):
    """The three star sizes TENSOR would draw for this solution."""
    lam = np.sort(np.asarray(eigenvalues, float))[::-1]      # s1, s2, s3
    return STAR_BASE + STAR_GAIN * (0.5 - float(phi)) * lam


def _draw_star(ax, x, y, index, size, lw=1.1, zorder=9):
    px, py = star_polygon(x, y, STAR_POINTS[index], size,
                          inner=STAR_INNER[index],
                          phase_deg=STAR_PHASE[index])
    ax.fill(np.append(px, px[0]), np.append(py, py[0]),
            facecolor=PAPER, edgecolor=PEN, lw=lw, zorder=zorder, antialiased=AA)


#: The striae symbol, measured over 94 examples in the archive HPGL.
#:
#: It is a SHEAR COUPLE, not a single arrow: a filled dot with two parallel
#: shafts, each offset sideways, running in opposite directions. The head on
#: each shaft carries Angelier's confidence letter, and the whole thing is
#: what makes dextral read differently from sinistral on the plot.
#:
#:   S  supposé    shaft only, no head at all
#:   P  probable   one barb line into the tip
#:   C  certain    a two-segment triangular head
#:
#: Which side everything sits on is set by the sign of the STRIKE-SLIP
#: COMPONENT of the movement: 89 of 89 heads agree with it. The movement
#: letter only manages 83 of 89, because the letter is a field judgement while
#: the drawing follows the geometry. There is no threshold, the side flips
#: exactly at pure dip-slip; the most nearly dip-slip datum in the archive is
#: still 11 degrees off it.
DOT_R = 0.0280
SHAFT_LEN = 0.1249
SHAFT_OFFSET = 0.0237       # perpendicular, on the same side as the barb
HEAD_C_INNER = 0.0259       # back along the shaft, on the axis
HEAD_C_BARB = (0.0514, 0.0244)   # back along the shaft, and out to the side
HEAD_P_BARB = (0.0486, 0.0248)

CONFIDENCE_ORDER = ('S', 'P', 'C')


def _striae_symbol(ax, x, y, dx, dy, side=1.0, conf='C', lw=STROKE, zorder=5):
    """One striae: filled dot, two offset shafts, and the heads.

    dx, dy   unit horizontal direction of the hanging-wall motion
    side     +1 or -1, from the sign of the strike-slip component
    """
    ax.add_patch(plt_circle(x, y, DOT_R, zorder=zorder + 1))

    c = (conf or 'C').upper()
    for sgn in (1.0, -1.0):
        u = np.array([dx, dy]) * sgn
        w = np.array([-u[1], u[0]]) * (1.0 if side >= 0 else -1.0)
        base = np.array([x, y]) + w * SHAFT_OFFSET
        tip = base + u * SHAFT_LEN
        ax.plot([base[0], tip[0]], [base[1], tip[1]], color=PEN, lw=lw,
                solid_capstyle='round', zorder=zorder, antialiased=AA)
        if c == 'S':
            continue
        if c == 'P':
            p = tip - u * HEAD_P_BARB[0] + w * HEAD_P_BARB[1]
            ax.plot([p[0], tip[0]], [p[1], tip[1]], color=PEN, lw=lw,
                    solid_capstyle='round', zorder=zorder, antialiased=AA)
        else:
            a = tip - u * HEAD_C_INNER
            b = tip - u * HEAD_C_BARB[0] + w * HEAD_C_BARB[1]
            ax.plot([a[0], b[0], tip[0]], [a[1], b[1], tip[1]], color=PEN,
                    lw=lw, solid_capstyle='round', solid_joinstyle='round',
                    zorder=zorder, antialiased=AA)


def plt_circle(x, y, r, zorder=6):
    from matplotlib.patches import Circle
    return Circle((x, y), r, facecolor=PEN, edgecolor='none', zorder=zorder)


def strike_slip_sign(dipaz_deg, dip_deg, rake_deg):
    """Sign of the strike-slip component, taking the strike at
    (dip azimuth - 90) and the movement at (stored rake + 180)."""
    from .core import strike_and_downdip, slip_from_rake, normal_from_dipaz
    s = np.atleast_2d(slip_from_rake(dipaz_deg, dip_deg, rake_deg))
    strike, _dd = strike_and_downdip(dipaz_deg, dip_deg)
    strike = np.atleast_2d(strike)
    v = np.einsum('ki,ki->k', s, strike)
    return np.where(v >= 0, 1.0, -1.0)


#: an axis only gets its heavy arrow pair if it is shallow enough for a
#: horizontal direction to mean anything. Checked against the originals:
#: L12 draws both pairs (sigma1 36 deg, sigma3 44 deg), 0406-7 draws only the
#: extension pair (sigma1 68 deg is too steep, sigma3 19 deg is fine).
ARROW_PLUNGE_LIMIT = 45.0


def arrow_polygon(azimuth_deg, outward=True):
    """The exact filled arrow TENSOR draws outside the primitive.

    Seven vertices: a blunt tail of half-width ARROW_SHAFT_HALF, barbs of
    half-width ARROW_BARB_HALF, and a point. Measured off the archive HPGL,
    where the shape is filled by nesting ~26 progressively smaller outlines,
    which is how a pen plotter fills a polygon.
    """
    t_barb = ARROW_BARB - ARROW_TAIL           # 0.077
    t_tip = ARROW_TIP - ARROW_TAIL             # 0.179
    local = [(0.0, +ARROW_SHAFT_HALF),
             (t_barb, +ARROW_SHAFT_HALF),
             (t_barb, +ARROW_BARB_HALF),
             (t_tip, 0.0),
             (t_barb, -ARROW_BARB_HALF),
             (t_barb, -ARROW_SHAFT_HALF),
             (0.0, -ARROW_SHAFT_HALF)]
    a = np.radians(azimuth_deg)
    u = np.array([np.sin(a), np.cos(a)])       # radial, along the trend
    w = np.array([u[1], -u[0]])                # across
    base = ARROW_TAIL if outward else ARROW_TIP
    sgn = 1.0 if outward else -1.0
    pts = [(base + sgn * t) * u + lat * w for t, lat in local]
    return np.array(pts)


def _heavy_arrow(ax, azimuth_deg, outward, color=None, zorder=7):
    color = PEN if color is None else color
    p = arrow_polygon(azimuth_deg, outward)
    ax.fill(np.append(p[:, 0], p[0, 0]), np.append(p[:, 1], p[0, 1]),
            facecolor=color, edgecolor=color, lw=0.8, zorder=zorder, antialiased=AA)


# ------------------------------------------------------------------- frame ---
def _letter(ax, strokes, cx, base=LETTER_BASE):
    """Draw one of the plotter's stroke letters."""
    xs = [cx + u * LETTER_HALF for u, _v in strokes]
    ys = [base + v * LETTER_H for _u, v in strokes]
    ax.plot(xs, ys, color=PEN, lw=STROKE, solid_capstyle='round', zorder=6, antialiased=AA)


def draw_frame(ax, declination=None, box=True):
    """Primitive circle, N/E/S/W ticks, centre cross, N and M marks, box.

    Every dimension here was measured off the archive HPGL; see dump_first.py.
    """
    t = np.linspace(0, 2 * np.pi, 721)
    ax.plot(np.cos(t), np.sin(t), color=PEN, lw=STROKE, zorder=6, antialiased=AA)

    for a in (0, 90, 180, 270):                 # cardinal ticks, outward only
        r = np.radians(a)
        x, y = np.sin(r), np.cos(r)
        ax.plot([x * TICK_IN, x * TICK_OUT], [y * TICK_IN, y * TICK_OUT],
                color=PEN, lw=STROKE, zorder=6, antialiased=AA)

    ax.plot([-CROSS_ARM, CROSS_ARM], [0, 0], color=PEN, lw=STROKE, zorder=6, antialiased=AA)
    ax.plot([0, 0], [-CROSS_ARM, CROSS_ARM], color=PEN, lw=STROKE, zorder=6, antialiased=AA)

    # geographic north letter sits straight above the north tick
    _letter(ax, LETTER_N, 0.0)

    # magnetic north: a dogleg from the primitive up to under the M
    if declination is None:
        declination = MAGNETIC_OFFSET
    a = np.radians(declination)
    x0, y0 = np.sin(a), np.cos(a)
    ax.plot([x0, x0 * MAGNETIC_ELBOW_R, MAGNETIC_LETTER_X],
            [y0, y0 * MAGNETIC_ELBOW_R, LETTER_BASE],
            color=PEN, lw=STROKE, solid_capstyle='round', zorder=6, antialiased=AA)
    _letter(ax, LETTER_M, MAGNETIC_LETTER_X)

    if box:
        ax.plot([-FRAME_W, FRAME_W, FRAME_W, -FRAME_W, -FRAME_W],
                [-FRAME_H, -FRAME_H, FRAME_H, FRAME_H, -FRAME_H],
                color=PEN, lw=STROKE, zorder=6, antialiased=AA)

    ax.set_xlim(-FRAME_W * 1.03, FRAME_W * 1.03)
    ax.set_ylim(-FRAME_H * 1.03, FRAME_H * 1.03)
    ax.set_aspect('equal')
    ax.axis('off')


def _regime_arrows(ax, result):
    """Heavy solid arrows outside the circle: inward along the sigma1 trend
    (compression), outward along the sigma3 trend (extension). The originals
    draw both pairs."""
    for key, outward in (('sigma1', False), ('sigma3', True)):
        trend, plunge = result[key]
        if plunge > ARROW_PLUNGE_LIMIT:
            continue          # too steep for a horizontal direction to mean anything
        for az in (trend, trend + 180.0):
            _heavy_arrow(ax, az, outward)


# ------------------------------------------------------------------- main ---
def plot_site(ax, n, s, result=None, certainty=None, sides=None,
              declination=None, site_code=None, header=None,
              program=PROGRAM_TAG, show_axes=True, box=True):
    """Angelier-style stereogram of a fault-slip data set.

    certainty  per-datum 'C' / 'P' / 'S'; defaults to 'C'
    sides      per-datum +1 / -1 from strike_slip_sign(); defaults to +1
    """
    draw_frame(ax, declination=declination, box=box)
    n = np.atleast_2d(np.asarray(n, float))
    s = np.atleast_2d(np.asarray(s, float))

    for i in range(len(n)):
        for seg in great_circle(n[i]):
            ax.plot(seg[:, 0], seg[:, 1], color=PEN, lw=STROKE, zorder=3, antialiased=AA)

    for i in range(len(s)):
        v = s[i] if s[i][2] <= 0 else -s[i]
        X, Y = schmidt(v[None, :])
        x, y = float(X[0]), float(Y[0])

        # the symbol runs along the horizontal component of hanging-wall
        # motion; the side comes from the strike-slip component
        hx, hy = float(s[i][0]), float(s[i][1])
        h = np.hypot(hx, hy)
        if h < 1e-9:
            ax.add_patch(plt_circle(x, y, DOT_R))
            continue
        conf = 'C' if certainty is None else certainty[i]
        sd = 1.0 if sides is None else float(sides[i])
        _striae_symbol(ax, x, y, hx / h, hy / h, side=sd, conf=conf)

    if result is not None and show_axes:
        if 'eigenvalues' in result:
            sizes = star_sizes(result['phi'], result['eigenvalues'])
        else:
            sizes = np.full(3, STAR_BASE)
        for i, key in enumerate(('sigma1', 'sigma2', 'sigma3')):
            v = vec_from_trend_plunge(*result[key])
            X, Y = schmidt(v[None, :])
            _draw_star(ax, float(X[0]), float(Y[0]), i, float(sizes[i]))
        _regime_arrows(ax, result)

    if site_code:
        ax.text(0, FRAME_H * 0.90, str(site_code), ha='center', va='center',
                fontsize=9, family='monospace')
    if header:
        ax.text(-FRAME_W, -FRAME_H * 1.05, str(header), ha='left', va='top',
                fontsize=8, family='monospace')
    if program:
        ax.text(FRAME_W, -FRAME_H * 1.05, str(program), ha='right', va='top',
                fontsize=8, family='monospace')


def plot_fitted(ax, n, T, **kw):
    """Angelier's right-hand panel: the same planes carrying the shear stress
    predicted by the solution, i.e. a perfect artificial data set. Comparing it
    with the observed panel is how he displays the quality of a fit."""
    n = np.atleast_2d(np.asarray(n, float))
    sig = n @ np.asarray(T, float).T
    sn = np.einsum('ki,ki->k', n, sig)
    tau = sig - sn[:, None] * n
    tau = tau / np.maximum(np.linalg.norm(tau, axis=1, keepdims=True), 1e-300)
    plot_site(ax, n, tau, **kw)


def annotate_result(ax, result, n_data=None, method=''):
    """The numerical block Angelier prints beside each diagram. Two lines, so
    it stays inside the panel when several are shown side by side."""
    axes_txt = '  '.join(
        '%s %03d/%02d' % (nm, int(round(result[key][0])) % 360,
                          int(round(result[key][1])))
        for key, nm in (('sigma1', 'S1'), ('sigma2', 'S2'), ('sigma3', 'S3')))
    second = ['PHI %.3f' % result['phi']]
    if 'ANG_mean' in result:
        second.append('ANG %.1f' % result['ANG_mean'])
        second.append('RUP %.0f%%' % result['RUP_mean'])
    if n_data is not None:
        second.append('N %d' % n_data)
    if method:
        second.insert(0, method)
    # sits below the header / program line so the three never collide
    ax.text(0, -FRAME_H * 1.13, axes_txt, fontsize=7.5, family='monospace',
            ha='center', va='top', color=PEN)
    ax.text(0, -FRAME_H * 1.22, '  '.join(second), fontsize=7.5,
            family='monospace', ha='center', va='top', color=PEN)


def plot_mohr(ax, result):
    """Mohr diagram of the reduced tensor with the data on it."""
    w = np.sort(np.asarray(result['eigenvalues'], float))[::-1]
    s1, s2, s3 = w
    t = np.linspace(0, np.pi, 240)
    for lo, hi, lw in ((s3, s1, 1.0), (s3, s2, 0.7), (s2, s1, 0.7)):
        c, r = 0.5 * (lo + hi), 0.5 * (hi - lo)
        ax.plot(c + r * np.cos(t), r * np.sin(t), color=PEN, lw=lw, antialiased=AA)
    if 'SIGMN' in result:
        ax.plot(result['SIGMN'], result['TAU'], 'o', ms=3.6,
                markerfacecolor=PAPER, markeredgecolor=PEN, mew=0.9, zorder=4, antialiased=AA)
    ax.axhline(0, color=PEN, lw=0.7)
    for v, nm in ((s1, r'$\sigma_1$'), (s2, r'$\sigma_2$'), (s3, r'$\sigma_3$')):
        ax.plot([v], [0], marker='|', ms=8, color=PEN, antialiased=AA)
        ax.annotate(nm, xy=(v, 0), xytext=(0, -14),
                    textcoords='offset points', ha='center', fontsize=8)
    ax.set_xlabel(r'$\sigma_n$', fontsize=9)
    ax.set_ylabel(r'$\tau$', fontsize=9)
    ax.set_aspect('equal')
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
