# -*- coding: utf-8 -*-
"""Run every TENSOR site in a folder tree through both modes and tabulate the
difference. The output table is the method-uncertainty estimate.

    python run_batch.py [root_folder] [out.csv]
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytensor import core, invdir, modern, tensorfile

DEFAULT_ROOT = r"C:\Users\龐麒修\iCloudDrive\博士論文\Paper\清水溪\清水溪應力"


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


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    out = sys.argv[2] if len(sys.argv) > 2 else 'pytensor_AB_comparison.csv'
    main(root, out)
