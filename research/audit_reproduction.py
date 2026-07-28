# -*- coding: utf-8 -*-
"""The right question: which archive runs does pyTENSOR fail to reproduce?

An earlier screen ranked sites by S4(recorded) / S4(global minimum). That was a
bad metric: with four faults and four unknowns the global minimum can be driven
to nearly zero, so the ratio explodes on every small site and flagged 78 of 87.
It measures sample size, not whether the old run converged.

What matters is simpler. Re-run each site the way the original did, adopting
the LAMBDA its own INFO1 records, and ask how far the answer moves. Small
movement means pyTENSOR reproduces that run and the recorded numbers stand.
Large movement is worth investigating.
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytensor import core, invdir, tensorfile
from pytensor.archive import ROOT, require


def main(out_csv):
    require('audit_reproduction.py')
    rows = []
    for p in tensorfile.discover(ROOT):
        rel = os.path.relpath(p, ROOT)
        d = os.path.dirname(p)
        try:
            site = tensorfile.read_site(p)
            if len(site) < 4:
                continue
            mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
            arch = tensorfile.parse_result_line(site.result_line)
            info = tensorfile.read_info_lambda(os.path.join(d, 'INFO1'))
            if mohr['eigenvalues'] is None or arch is None:
                continue
        except Exception:
            continue
        n, s = site.n, site.s
        V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                             for k in ('sigma1', 'sigma2', 'sigma3')])
        U, _, Wt = np.linalg.svd(V)
        T_rec = (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T
        s4_rec = core.S4(T_rec, n, s)

        try:
            r = invdir.run(n, s, n_pass=info.get('pass_no', 1),
                           lam_printed=info.get('lambda_invdir'))
        except Exception as exc:
            print('%-46s failed: %s' % (rel[:46], exc))
            continue
        res = core.describe(r['T'])
        s4_new = core.S4(r['T'], n, s)

        devs = []
        for k in ('sigma1', 'sigma2', 'sigma3'):
            va = core.vec_from_trend_plunge(*arch[k])
            vb = core.vec_from_trend_plunge(*res[k])
            devs.append(float(np.degrees(np.arccos(
                min(abs(float(va @ vb)), 1.0)))))
        rows.append(dict(site=rel, n=len(site),
                         pass_no=info.get('pass_no', ''),
                         lam=info.get('lambda_invdir', ''),
                         phi_rec=arch['phi'], phi_new=res['phi'],
                         d_phi=res['phi'] - arch['phi'],
                         s1=devs[0], s2=devs[1], s3=devs[2],
                         worst=max(devs),
                         s4_rec=s4_rec, s4_new=s4_new,
                         d_s4=s4_new - s4_rec))
        print('   %-46s n=%2d  sigma1 %5.1f deg  dPhi %+.3f'
              % (rel[:46], len(site), devs[0], res['phi'] - arch['phi']))

    rows.sort(key=lambda r: -r['s1'])
    d1 = np.array([r['s1'] for r in rows])
    dp = np.array([abs(r['d_phi']) for r in rows])
    print('\n' + '=' * 78)
    print('%d runs re-run with their own recorded LAMBDA' % len(rows))
    print('sigma1 movement: median %.2f deg, p90 %.2f, max %.2f'
          % (np.median(d1), np.percentile(d1, 90), d1.max()))
    print('|dPhi|:          median %.3f, p90 %.3f' % (np.median(dp),
                                                      np.percentile(dp, 90)))
    for thr in (1, 2, 5, 10):
        print('   reproduced within %2d deg: %3d of %d (%.0f%%)'
              % (thr, (d1 <= thr).sum(), len(d1),
                 100.0 * (d1 <= thr).sum() / len(d1)))

    bad = [r for r in rows if r['s1'] > 5.0]
    print('\n%d runs pyTENSOR does NOT reproduce within 5 deg' % len(bad))
    if bad:
        print('%-46s %3s %4s %6s %7s %8s %8s'
              % ('site', 'n', 'NO', 'sig1', 'dPhi', 'S4 rec', 'S4 new'))
        for r in bad:
            print('%-46s %3d %4s %6.1f %+7.3f %8.3f %8.3f'
                  % (r['site'][:46], r['n'], r['pass_no'], r['s1'],
                     r['d_phi'], r['s4_rec'], r['s4_new']))

    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('\nwritten %s' % out_csv)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1
         else os.path.join(os.path.dirname(os.path.dirname(
             os.path.abspath(__file__))), 'archive_reproduction.csv'))
