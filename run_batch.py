# -*- coding: utf-8 -*-
"""Run every TENSOR site in a folder tree through both modes and tabulate the
difference. The output table is the method-uncertainty estimate.

Also writes an axial rose of the batch's sigma1 and sigma3 trends, which is
the multi-site question a single stereogram cannot answer: what direction did
this population of determinations actually act in.

    python run_batch.py [root_folder] [out.csv]
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytector import core, invdir, modern, rose, tensorfile

from pytector.archive import ROOT

DEFAULT_ROOT = ROOT
def axis_gap(a, b):
    va = core.vec_from_trend_plunge(*a)
    vb = core.vec_from_trend_plunge(*b)
    return float(np.degrees(np.arccos(min(abs(float(va @ vb)), 1.0))))


def main(root, out_csv):
    paths = tensorfile.discover(root)
    print('%d runs found under %s\n' % (len(paths), root))
    rows = []
    for p in paths:
        rel = os.path.relpath(p, root)
        try:
            site = tensorfile.read_site(p)
        except Exception as exc:
            print('  %-28s  unreadable: %s' % (rel, exc))
            continue
        if len(site) < 4:
            print('  %-28s  only %d faults, skipped' % (rel, len(site)))
            continue

        n, s = site.n, site.s
        folder = os.path.dirname(p)
        info_p = os.path.join(folder, 'INFO1')
        info = tensorfile.read_info_lambda(info_p) if os.path.exists(info_p) else {}
        arch = tensorfile.parse_result_line(site.result_line)

        try:
            ra = invdir.run(n, s, n_pass=info.get('pass_no', 1))
            A = core.summary(ra['T'], n, s)
            B = modern.run(n, s, n_starts=300)
            Bs = core.summary(B['T'], n, s)
        except Exception as exc:
            print('  %-28s  inversion failed: %s' % (rel, exc))
            continue

        row = dict(
            site=rel, n=len(site), pass_no=info.get('pass_no', ''),
            A_s1_trend=A['sigma1'][0], A_s1_plunge=A['sigma1'][1],
            A_s3_trend=A['sigma3'][0], A_s3_plunge=A['sigma3'][1],
            A_phi=A['phi'], A_ANG=A['ANG_mean'], A_RUP=A['RUP_mean'], A_S4=A['S4'],
            B_s1_trend=Bs['sigma1'][0], B_s1_plunge=Bs['sigma1'][1],
            B_s3_trend=Bs['sigma3'][0], B_s3_plunge=Bs['sigma3'][1],
            B_phi=Bs['phi'], B_ANG=Bs['ANG_mean'], B_RUP=Bs['RUP_mean'], B_S4=Bs['S4'],
            d_s1=axis_gap(A['sigma1'], Bs['sigma1']),
            d_s2=axis_gap(A['sigma2'], Bs['sigma2']),
            d_s3=axis_gap(A['sigma3'], Bs['sigma3']),
            d_phi=Bs['phi'] - A['phi'], d_S4=Bs['S4'] - A['S4'])
        if arch:
            row['archive_s1_trend'] = arch['sigma1'][0]
            row['archive_s1_plunge'] = arch['sigma1'][1]
            row['archive_phi'] = arch['phi']
            row['A_vs_archive_s1'] = axis_gap(A['sigma1'], arch['sigma1'])
        rows.append(row)
        print('  %-28s n=%2d  A s1 %5.1f/%4.1f Phi %.3f | B s1 %5.1f/%4.1f Phi %.3f'
              ' | ds1 %5.1f  dPhi %+.3f'
              % (rel, len(site), A['sigma1'][0], A['sigma1'][1], A['phi'],
                 Bs['sigma1'][0], Bs['sigma1'][1], Bs['phi'],
                 row['d_s1'], row['d_phi']))

    if not rows:
        print('\nnothing to write')
        return
    keys = sorted({k for r in rows for k in r})
    keys = ['site', 'n', 'pass_no'] + [k for k in keys
                                       if k not in ('site', 'n', 'pass_no')]
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    d1 = np.array([r['d_s1'] for r in rows])
    dp = np.array([abs(r['d_phi']) for r in rows])
    print('\n%d sites written to %s' % (len(rows), out_csv))
    print('  sigma1 A vs B : median %.1f deg, 90th pct %.1f deg, max %.1f deg'
          % (np.median(d1), np.percentile(d1, 90), d1.max()))
    print('  |dPhi|        : median %.3f, max %.3f' % (np.median(dp), dp.max()))

    _roses(rows, out_csv)


def _roses(rows, out_csv):
    """Axial roses of sigma1 and sigma3 over the whole batch.

    A rose of one site would be three points; it earns its place across many
    determinations. Which of the two panels is worth reading is not fixed: a
    population whose sigma1 all plunge steeply has an empty compression rose
    and a perfectly good extension one, so rose.pick_readable decides and the
    readable panel is drawn bold.
    """
    groups = {
        'sigma1  compression': [(r['A_s1_trend'], r['A_s1_plunge'])
                                for r in rows],
        'sigma3  extension': [(r['A_s3_trend'], r['A_s3_plunge'])
                              for r in rows],
    }
    read = rose.pick_readable(groups)
    print('\n  rose, INVDIR solutions (axes plunging under %g deg only):'
          % rose.SHALLOW_LIMIT)
    for label, axs in groups.items():
        trends, dropped = rose.shallow_only(axs)
        st = rose.axial_stats(trends)
        note = '   <- read this' if label == read else ''
        if st:
            print('    %-22s n=%-3d mean %03.0f  R %.2f%s'
                  % (label, len(trends), st['mean'], st['R'], note))
        else:
            print('    %-22s n=%-3d no usable axis, %d too steep%s'
                  % (label, len(trends), dropped, note))

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as exc:                        # pragma: no cover
        print('    (no figure: %s)' % exc)
        return
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.9),
                             subplot_kw=dict(projection='polar'))
    fig.patch.set_facecolor('white')
    for ax, label in zip(axes, list(groups)):
        rose.plot_rose(ax, groups[label], title=label,
                       emphasis=(label == read))
    fig.suptitle('%d sites' % len(rows), fontsize=11, fontweight='600',
                 color=rose.INK, y=1.02)
    fig.subplots_adjust(left=0.07, right=0.95, top=0.70, bottom=0.10,
                        wspace=0.35)
    png = os.path.splitext(out_csv)[0] + '_rose.png'
    fig.savefig(png, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('    figure: %s' % png)


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    out = sys.argv[2] if len(sys.argv) > 2 else 'pytector_AB_comparison.csv'
    main(root, out)
