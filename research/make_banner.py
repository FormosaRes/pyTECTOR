# -*- coding: utf-8 -*-
"""Draw the README banner from the program's own output.

Deliberately not an illustration. Every stereogram in it is produced by
pytector from tests/fixtures/L12-2, the public fixture, so the banner is
reproducible by anyone who clones the repository and it cannot drift away from
what the program actually draws.

    python research/make_banner.py        -> docs/img/banner.png
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt                                   # noqa: E402
from matplotlib.patches import FancyBboxPatch                     # noqa: E402
import numpy as np                                                # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from pytector import core, invdir, plot, rotate, tensorfile        # noqa: E402

INK, ACC = '#1E1E1C', '#1F4E6B'
ROT = (20.0, 0.0, -30.0)

#: Kept honest against the archive numbers: 92 readable sites, 90 with a PSIDIR
#: line, 85 of those reproduced to under 3 degrees on sigma1. "Byte-identical"
#: is true of INFO1/MOHR1, not of the whole archive, so it is not claimed here.
STRAP = ('照論文重寫，不反譯 exe   ·   原程式 90 個 run 重現 85 個'
         '   ·   圖由公開 fixture 產生')


def main():
    site = os.path.join(ROOT, 'tests', 'fixtures', 'L12-2', 'L12-2')
    st = tensorfile.read_site(site)
    n, s, conf = st.n, st.s, st.confidence
    A = core.summary(invdir.run(n, s, n_pass=1)['T'], n, s)
    rn, rs = rotate.rotate_site(n, s, *ROT)
    R = core.summary(invdir.run(rn, rs, n_pass=1)['T'], rn, rs)
    car = {}
    for k in ('sigma1', 'sigma2', 'sigma3'):
        v = core.vec_from_trend_plunge(*A[k])
        car[k] = core.trend_plunge(
            rotate.rotate_vectors(np.atleast_2d(v), *ROT)[0])
    car['phi'] = A['phi']
    car['eigenvalues'] = A.get('eigenvalues')

    fig = plt.figure(figsize=(14.0, 7.0), facecolor='white')

    tb = fig.add_axes([0, 0.815, 1, 0.185])
    tb.axis('off')
    tb.add_patch(FancyBboxPatch(
        (0.345, 0.40), 0.31, 0.40,
        boxstyle='round,pad=0.010,rounding_size=0.02',
        facecolor=ACC, edgecolor='#0F2C3E', lw=2, transform=tb.transAxes))
    tb.text(0.5, 0.605, 'pyTECTOR', ha='center', va='center', fontsize=40,
            fontweight='bold', color='white', family='DejaVu Sans')
    tb.text(0.5, 0.16,
            'ANGELIER 古應力反演的 PYTHON 重建版  —  TENSOR 5.45 (jan91)',
            ha='center', va='center', fontsize=15, fontweight='bold',
            color=INK)

    stages = [('1. 野外記錄', 'MESURE 四欄輸入\n斷層面 · 擦痕 · 信心度', 'data'),
              ('2. 反演', 'INVDIR 忠實復刻\nS4MIN 同準則精確解', 'inv'),
              ('3. 回轉', 'back-tilt 與 tilt test\n原程式沒有的功能', 'bt')]
    cw, x0, gap = 0.235, 0.055, 0.075
    for i, (head, sub, kind) in enumerate(stages):
        x = x0 + i * (cw + gap)
        ax = fig.add_axes([x, 0.335, cw, 0.44])
        if kind == 'data':
            plot.plot_site(ax, n, s, None, certainty=conf,
                           sides=plot.strike_slip_sign_vectors(n, s),
                           site_code='L12-2', header='observed')
        elif kind == 'inv':
            plot.plot_site(ax, n, s, A, certainty=conf,
                           sides=plot.strike_slip_sign_vectors(n, s),
                           site_code='L12-2', header='INVDIR')
        else:
            plot.plot_site(ax, rn, rs, R, certainty=conf,
                           sides=plot.strike_slip_sign_vectors(rn, rs),
                           site_code='L12-2', header='BACK-TILTED')
            plot.plot_carried_axes(ax, car, R)
        t = fig.add_axes([x, 0.775, cw, 0.045])
        t.axis('off')
        t.text(0.5, 0.4, head, ha='center', va='center', fontsize=15,
               fontweight='bold', color=INK)
        b = fig.add_axes([x, 0.225, cw, 0.10])
        b.axis('off')
        b.text(0.5, 0.92, sub, ha='center', va='top', fontsize=11.5,
               color='#4A4A46', linespacing=1.6)
    for i in range(2):
        a = fig.add_axes([x0 + cw + i * (cw + gap), 0.335, gap, 0.44])
        a.axis('off')
        a.annotate('', xy=(0.80, 0.5), xytext=(0.20, 0.5),
                   arrowprops=dict(
                       arrowstyle='-|>,head_width=0.40,head_length=0.75',
                       color=ACC, lw=3.2))

    o = fig.add_axes([x0, 0.115, 3 * cw + 2 * gap, 0.105])
    o.axis('off')
    o.set_xlim(0, 1)
    o.set_ylim(0, 1)
    outs = [('INFO1 / MOHR1', '與原檔逐位元組相同'),
            ('HPGL', '重播畫圖程式本身'),
            ('Session .tec', '存檔只存張量'),
            ('診斷', 'leave-one-out + ANG*')]
    w = 1.0 / len(outs)
    for j, (nm, d) in enumerate(outs):
        cx = (j + 0.5) * w
        o.add_patch(FancyBboxPatch(
            (j * w + 0.008, 0.06), w - 0.016, 0.86,
            boxstyle='round,pad=0.004,rounding_size=0.02',
            facecolor='#F2F5F7', edgecolor='#C9D6DE', lw=1.1,
            transform=o.transAxes))
        o.text(cx, 0.66, nm, ha='center', va='center', fontsize=12,
               fontweight='bold', color=ACC)
        o.text(cx, 0.28, d, ha='center', va='center', fontsize=10,
               color='#5A5A56')
    o2 = fig.add_axes([x0, 0.222, 3 * cw + 2 * gap, 0.03])
    o2.axis('off')
    o2.text(0.5, 0.0, '4. 原格式輸出', ha='center', va='bottom', fontsize=13,
            fontweight='bold', color=INK)

    f = fig.add_axes([0, 0, 1, 0.108])
    f.axis('off')
    f.set_xlim(0, 1)
    f.set_ylim(0, 1)
    f.text(0.055, 0.80, 'A PROJECT BY', fontsize=9, color='#7A776F',
           fontweight='bold', va='center')
    f.text(0.055, 0.46, 'FORMOSARES', fontsize=19, color=ACC,
           fontweight='bold', va='center', family='DejaVu Sans')
    f.text(0.055, 0.13, 'github.com/FormosaRes/pyTECTOR', fontsize=10,
           color='#4A4A46', va='center', family='DejaVu Sans')
    f.text(0.945, 0.46, STRAP, ha='right', va='center', fontsize=11.5,
           fontweight='bold', color=INK)

    out = os.path.join(ROOT, 'docs', 'img', 'banner.png')
    fig.savefig(out, dpi=100, facecolor='white')
    print('wrote %s (%d bytes)' % (out, os.path.getsize(out)))


if __name__ == '__main__':
    main()
