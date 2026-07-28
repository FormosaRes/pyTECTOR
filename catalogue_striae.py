# -*- coding: utf-8 -*-
"""Extract the striae symbol cleanly: only the strokes that belong to it.

Also settles which side the barb sits on, measured in the frame of the shaft
that points ALONG the slip, rather than whichever shaft happened to be found
first (the two shafts are opposed, so the frame flips between them).
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import hpgl, plot, tensorfile

ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"
DOT_R = 0.028


def fit_circle(P):
    x, y = P[:, 0], P[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    sol, *_ = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    return np.array([cx, cy]), np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0))


def find_primitive(polys):
    best, bestcv = None, 9e9
    for _pen, p in polys:
        if len(p) < 40:
            continue
        ctr = p.mean(axis=0)
        r = np.hypot(p[:, 0] - ctr[0], p[:, 1] - ctr[1])
        cv = r.std() / max(r.mean(), 1e-9)
        if cv < bestcv:
            best, bestcv = p, cv
    return fit_circle(best)


def symbols_of(folder):
    d = os.path.join(ROOT, folder)
    hp = os.path.join(d, 'HPGL')
    data = [f for f in os.listdir(d)
            if '.' not in f and f not in ('INFO1', 'MOHR1', 'PLOT1', 'HPGL')]
    if not (os.path.exists(hp) and data):
        return []
    polys, _l, _ = hpgl.read(hp)
    site = tensorfile.read_site(os.path.join(d, data[0]))
    c, R = find_primitive(polys)
    uni = [((p - c) / R) for _pen, p in polys]
    twos = [q for q in uni if len(q) == 2]
    threes = [q for q in uni if len(q) == 3]

    s = site.s
    sl = np.where((s[:, 2] > 0)[:, None], -s, s)
    X, Y = plot.schmidt(sl)

    out = []
    for i, rec in enumerate(site.records):
        px, py = X[i], Y[i]
        hx, hy = s[i][0], s[i][1]
        h = np.hypot(hx, hy)
        if h < 1e-9:
            continue
        u = np.array([hx / h, hy / h])
        mine = []
        for q in twos:
            d0 = np.hypot(q[0][0] - px, q[0][1] - py)
            d1 = np.hypot(q[1][0] - px, q[1][1] - py)
            if not (0.015 < min(d0, d1) < 0.040 and 0.09 < max(d0, d1) < 0.20):
                continue
            near, far = (q[0], q[1]) if d0 < d1 else (q[1], q[0])
            mine.append((near, far))
        if len(mine) != 2:
            continue
        # the shaft that runs ALONG the slip direction
        along = [float((f - n) @ u) for n, f in mine]
        k = int(np.argmax(along))
        n_, f_ = mine[k]
        uu = (f_ - n_) / np.linalg.norm(f_ - n_)
        ww = np.array([-uu[1], uu[0]])
        head, side = None, None
        for q in threes:
            if np.hypot(q[-1][0] - f_[0], q[-1][1] - f_[1]) < 0.006:
                head = q
                side = float((q[1] - f_) @ ww)
                break
        if head is None:                      # probable: a 2-point barb
            for q in twos:
                if q is mine[0][0] is None:
                    continue
                d_end = np.hypot(q[-1][0] - f_[0], q[-1][1] - f_[1])
                d_end0 = np.hypot(q[0][0] - f_[0], q[0][1] - f_[1])
                if min(d_end, d_end0) > 0.006:
                    continue
                other = q[0] if d_end < d_end0 else q[-1]
                v = other - f_
                if 0.02 < np.linalg.norm(v) < 0.08:
                    head = np.array([other, f_])
                    side = float(v @ ww)
                    break
        out.append(dict(site=folder, i=i, rec=rec, conf=rec.get('confidence'),
                        mv=(rec['tail'][1:2] or '?').upper(),
                        px=px, py=py, u=u, shafts=mine, head=head, side=side,
                        X=X, Y=Y))
    return out


samples = []
for folder in sorted(os.listdir(ROOT)):
    if not os.path.isdir(os.path.join(ROOT, folder)):
        continue
    try:
        samples.extend(symbols_of(folder))
    except Exception:
        pass

have = [x for x in samples if x['side'] is not None]
print('%d symbols, %d with a measurable head\n' % (len(samples), len(have)))

print('barb side measured in the frame of the down-slip shaft:')
for mv in sorted({x['mv'] for x in have}):
    v = np.array([x['side'] for x in have if x['mv'] == mv])
    print('   %s  n=%3d   %3d positive, %3d negative   median %+.4f'
          % (mv, len(v), (v > 0).sum(), (v < 0).sum(), np.median(v)))

allside = np.array([x['side'] for x in have])
print('\n   overall: %d positive, %d negative'
      % ((allside > 0).sum(), (allside < 0).sum()))
if (allside > 0).all() or (allside < 0).all():
    print('   ==> the barb always sits on the SAME side of the slip direction;'
          '\n       the shear sense comes out of the double-ended symbol '
          'itself, not the barb side.')

# ------------------------------------------------------------- catalogue ---
want = [('S', 'N'), ('P', 'N'), ('P', 'S'), ('P', 'D'),
        ('C', 'N'), ('C', 'S'), ('C', 'D')]
picks = []
for conf, mv in want:
    best, bestd = None, -1
    for x in samples:
        if x['conf'] != conf or x['mv'] != mv:
            continue
        o = [np.hypot(x['X'][j] - x['px'], x['Y'][j] - x['py'])
             for j in range(len(x['X'])) if j != x['i']]
        m = min(o) if o else 9.9
        if m > bestd:
            best, bestd = x, m
    if best is not None:
        picks.append((conf, mv, best))

fig, axes = plt.subplots(1, len(picks), figsize=(2.1 * len(picks), 2.7))
for ax, (conf, mv, x) in zip(axes, picks):
    th = np.linspace(0, 2 * np.pi, 60)
    ax.fill(DOT_R * np.cos(th), DOT_R * np.sin(th), color='k', zorder=3)
    for n_, f_ in x['shafts']:
        ax.plot([n_[0] - x['px'], f_[0] - x['px']],
                [n_[1] - x['py'], f_[1] - x['py']],
                color='k', lw=1.8, solid_capstyle='round')
    if x['head'] is not None:
        h = np.asarray(x['head'])
        ax.plot(h[:, 0] - x['px'], h[:, 1] - x['py'],
                color='k', lw=1.8, solid_capstyle='round')
    u = x['u']
    ax.annotate('', xy=(u[0] * 0.19, u[1] * 0.19), xytext=(0, 0),
                arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.0))
    ax.set_xlim(-0.2, 0.2)
    ax.set_ylim(-0.2, 0.2)
    ax.set_aspect('equal')
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color('#cccccc')
    ax.set_title('%s  %s\n%s' % (conf, mv, x['rec']['tail'][:2]), fontsize=10)
fig.suptitle('striae symbols lifted from the archive HPGL   '
             '(red = slip direction, only that symbol\'s own strokes drawn)',
             fontsize=9, y=1.06)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'striae_catalogue.png')
fig.savefig(out, dpi=210, bbox_inches='tight', facecolor='white')
print('\nwritten:', out)
