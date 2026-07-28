# -*- coding: utf-8 -*-
"""Read (and write) the HPGL plot files that TENSOR produces.

HPGL is plain-text plotter vector language, so the HPGL file next to every run
is literally the picture Angelier's program drew, stroke by stroke. That makes
it the authoritative reference for the house drawing style, and it means
pyTENSOR can both display the originals and emit output in the same form.

Commands seen in the archive: IN, SP, PU, PD, PA, LT, CS, SI, DI, LB, PG.
"""
import re

import numpy as np

_CMD = re.compile(r'([A-Za-z]{2})([^;]*);?')


def parse(text):
    """Return (polylines, labels, pens_used).

    polylines : list of (pen, Nx2 array) in plotter units
    labels    : list of (pen, x, y, text)
    """
    polylines, labels = [], []
    pen, down, pos = 1, False, np.array([0.0, 0.0])
    cur = []
    cmds = set()

    i = 0
    while i < len(text):
        m = _CMD.match(text, i)
        if not m:
            i += 1
            continue
        op, arg = m.group(1).upper(), m.group(2)
        cmds.add(op)

        if op == 'LB':
            # label runs to the terminator (ETX, chr(3)) rather than ';'
            end = text.find('\x03', m.end(1))
            if end < 0:
                end = text.find(';', m.end(1))
            txt = text[m.end(1):end if end > 0 else len(text)]
            labels.append((pen, pos[0], pos[1], txt.strip()))
            i = (end + 1) if end > 0 else len(text)
            continue

        if op in ('PA', 'PD', 'PU', 'PR'):
            nums = [float(x) for x in re.findall(r'-?\d+\.?\d*', arg)]
            if op == 'PU':
                if len(cur) > 1:
                    polylines.append((pen, np.array(cur)))
                cur = []
                down = False
            elif op == 'PD':
                down = True
                if not cur:
                    cur = [pos.copy()]
            pts = np.array(nums).reshape(-1, 2) if nums else np.zeros((0, 2))
            for p in pts:
                if op == 'PR':
                    p = pos + p
                if down:
                    if not cur:
                        cur = [pos.copy()]
                    cur.append(p.copy())
                else:
                    if len(cur) > 1:
                        polylines.append((pen, np.array(cur)))
                    cur = []
                pos = np.asarray(p, float)
        elif op == 'SP':
            if len(cur) > 1:
                polylines.append((pen, np.array(cur)))
            cur = []
            nums = re.findall(r'\d+', arg)
            pen = int(nums[0]) if nums else pen
        elif op in ('IN', 'PG'):
            if len(cur) > 1:
                polylines.append((pen, np.array(cur)))
            cur = []
            down = False
        i = m.end()

    if len(cur) > 1:
        polylines.append((pen, np.array(cur)))
    return polylines, labels, cmds


def read(path):
    with open(path, 'r', errors='replace') as fh:
        return parse(fh.read())


def draw(ax, polylines, labels=None, lw=0.7, color='k', fontsize=7):
    """Render parsed HPGL onto a matplotlib axes, preserving aspect."""
    for pen, pts in polylines:
        ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw,
                solid_capstyle='round', solid_joinstyle='round')
    for item in (labels or []):
        _pen, x, y, txt = item
        if txt:
            ax.text(x, y, txt, fontsize=fontsize, color=color,
                    ha='left', va='bottom', family='monospace')
    ax.set_aspect('equal')
    ax.axis('off')


# ------------------------------------------------------------------ write ---
class Writer(object):
    """Emit HPGL in the same dialect TENSOR uses, so pyTENSOR output can be
    dropped into the same viewers and plotters as the originals."""

    def __init__(self, scale=2500.0, origin=(2910, 3164)):
        #: plotter units per unit radius of the stereogram, and the centre.
        #: Defaults reproduce the framing of the archive files.
        self.scale = scale
        self.origin = origin
        self.out = ['IN;', 'SP1;', 'CS0;', 'LT;']

    def _xy(self, x, y):
        return (int(round(self.origin[0] + x * self.scale)),
                int(round(self.origin[1] + y * self.scale)))

    def polyline(self, X, Y):
        if len(X) < 2:
            return
        x0, y0 = self._xy(X[0], Y[0])
        self.out.append('PU;PA%d,%d;' % (x0, y0))
        self.out.append('PD;')
        for x, y in zip(X[1:], Y[1:]):
            a, b = self._xy(x, y)
            self.out.append('PA%d,%d;' % (a, b))
        self.out.append('PU;')

    def label(self, x, y, text):
        a, b = self._xy(x, y)
        self.out.append('PU;PA%d,%d;LB%s\x03' % (a, b, text))

    def dumps(self):
        return '\n'.join(self.out + ['PU;', 'SP0;', 'PG;']) + '\n'

    def save(self, path):
        with open(path, 'w', newline='\n') as fh:
            fh.write(self.dumps())
