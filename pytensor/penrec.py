# -*- coding: utf-8 -*-
"""Record what plot.py draws, as vectors, for the plotter.

The HPGL export used to be a second, shorter drawing routine written beside
the matplotlib one. It drifted, as second implementations do: it emitted the
primitive and the fault planes and nothing else, so an exported plot had no
striae, no ticks, no centre cross, no N or M marks, no frame, no arrows and no
reference surfaces, and its scale did not match the archive files either.

There is no second implementation here. Recorder stands in for a matplotlib
Axes, plot.plot_site draws into it exactly as it draws on screen, and what
comes out the other side is the same picture as line segments. Anything added
to the drawing code from now on appears in the HPGL without being asked for.

The subset of the Axes API that plot.py touches is small: plot, fill,
add_patch, text, and the axis housekeeping. Unrecognised calls are recorded by
name in `ignored` rather than raising, so a stray Axes call cannot break an
export, and tests/test_ui_contract.py checks that set has not grown.
"""
import numpy as np

#: Marker sizes are in points, which mean nothing to a plotter. On the figure
#: sizes used here one data unit is roughly 100 points across, so a marker of
#: `ms` points has a radius of about ms/200 data units. Approximate on purpose:
#: it only affects the open rings, and only by a hair.
MARKER_SCALE = 1.0 / 200.0

#: A pen plotter fills a shape by drawing its outline again and again, each
#: pass a little smaller. The archive does about 26 passes for the heavy
#: arrows, which is what this matches.
FILL_PASSES = 26

_UNFILLED = ('none', 'white', '#ffffff', '#FFFFFF')


def _closed(x, y):
    p = np.column_stack([np.asarray(x, float), np.asarray(y, float)])
    if len(p) > 1 and not np.allclose(p[0], p[-1]):
        p = np.vstack([p, p[0]])
    return p


def _nest(p, passes=FILL_PASSES):
    """A solid shape as nested outlines, shrinking towards the centroid."""
    c = p[:-1].mean(0) if len(p) > 2 else p.mean(0)
    return [c + (p - c) * f
            for f in np.linspace(1.0, 0.0, passes + 1)[:-1]]


def _circle(cx, cy, r, points=48):
    t = np.linspace(0, 2 * np.pi, points + 1)
    return np.column_stack([cx + r * np.cos(t), cy + r * np.sin(t)])


class Recorder(object):
    """Quacks like an Axes, keeps the vectors."""

    def __init__(self):
        self.polylines = []                 # (N,2) arrays
        self.labels = []                    # (x, y, text, ha, va, fontsize)
        self.ignored = set()

    # ------------------------------------------------------------ drawing --
    def plot(self, *args, **kw):
        if len(args) < 2:
            return
        x, y = np.atleast_1d(args[0]), np.atleast_1d(args[1])
        if len(x) != len(y):
            return
        if str(kw.get('linestyle', '-')) == 'none' or kw.get('marker'):
            # a marker-only call: each point becomes a small ring
            r = float(kw.get('ms', 6.0)) * MARKER_SCALE
            face = str(kw.get('markerfacecolor', 'none')).lower()
            for px, py in zip(x, y):
                ring = _circle(float(px), float(py), r)
                if face in _UNFILLED:
                    self.polylines.append(ring)
                else:
                    self.polylines.extend(_nest(ring))
            if str(kw.get('linestyle', '-')) == 'none':
                return
        if len(x) > 1:
            self.polylines.append(np.column_stack([x, y]))

    def fill(self, x, y, **kw):
        p = _closed(x, y)
        face = str(kw.get('facecolor', kw.get('color', 'none'))).lower()
        if face in _UNFILLED:
            self.polylines.append(p)        # an outline, e.g. a stress star
        else:
            self.polylines.extend(_nest(p))
        return []

    def add_patch(self, patch):
        c = getattr(patch, 'center', None)
        r = getattr(patch, 'radius', None)
        if c is None or r is None:
            self.ignored.add('add_patch:' + type(patch).__name__)
            return patch
        self.polylines.extend(_nest(_circle(float(c[0]), float(c[1]),
                                            float(r)), passes=8))
        return patch

    def text(self, x, y, s, **kw):
        self.labels.append((float(x), float(y), str(s),
                            kw.get('ha', 'left'), kw.get('va', 'baseline'),
                            float(kw.get('fontsize', 8))))

    # ------------------------------------------------------ housekeeping --
    def set_xlim(self, *a, **k):
        pass

    def set_ylim(self, *a, **k):
        pass

    def set_aspect(self, *a, **k):
        pass

    def axis(self, *a, **k):
        pass

    def set_facecolor(self, *a, **k):
        pass

    def set_title(self, *a, **k):
        pass

    def __getattr__(self, name):
        # anything else is noted and skipped, so an export can never crash on
        # an Axes call that the drawing code picked up later
        def _noop(*_a, **_k):
            self.ignored.add(name)
        return _noop

    # ------------------------------------------------------------- output --
    def emit(self, writer):
        """Write everything recorded into an hpgl.Writer, in drawing order."""
        for p in self.polylines:
            writer.polyline(p[:, 0], p[:, 1])
        for x, y, s, ha, va, fontsize in self.labels:
            writer.label(x, y, s, ha=ha, size_cm=0.5 if fontsize >= 9 else 0.25)
        return writer
