# -*- coding: utf-8 -*-
"""How well did each historical run actually converge?

Every archive run records the stress tensor it settled on. Feed that tensor
back through the criterion and you get its S4: how well that answer fits the
data, on the scale both programs minimise. Compare it with the lowest S4 the
same data can reach and you have a direct measure of whether that run finished
the job.

    gap = S4(recorded) / S4(best reachable) - 1

A gap near zero means the run converged. A large gap means the recorded axes
and Phi came from a solution that was not at the minimum, so those numbers are
suspect regardless of what pyTECTOR does.

Sites flagged by the cheap screen are then re-run properly, adopting the
LAMBDA that site's own INFO1 records, to see whether the discrepancy is the
old run's or ours.

    python audit_archive.py [out.csv]
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytector import core, invdir, modern, tensorfile
from pytector.archive import ROOT, require

FLAG_GAP = 0.05          # 5 per cent above the floor is worth a look
FLAG_AXIS = 10.0         # degrees


def recorded_tensor(site, mohr, arch):
    V = np.column_stack([core.vec_from_trend_plunge(*arch[k])
                         for k in ('sigma1', 'sigma2', 'sigma3')])
    U, _, Wt = np.linalg.svd(V)
    return (U @ Wt) @ np.diag(mohr['eigenvalues']) @ (U @ Wt).T


def main(out_csv):
    require('audit_archive.py')
    paths = tensorfile.discover(ROOT)
    rows = []
    print('screening %d runs\n' % len(paths))
    for p in paths:
        rel = os.path.relpath(p, ROOT)
        d = os.path.dirname(p)
        try:
            site = tensorfile.read_site(p)
            if len(site) < 4:
                continue
            mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
            arch = tensorfile.parse_result_line(site.result_line)
            if mohr['eigenvalues'] is None or arch is None:
                continue
        except Exception:
            continue
        n, s = site.n, site.s
        try:
            T_rec = recorded_tensor(site, mohr, arch)
            s4_rec = core.S4(T_rec, n, s)
            best = modern.run(n, s, n_starts=250)
            s4_min = core.S4(best['T'], n, s)
        except Exception as exc:
            print('   %-44s failed: %s' % (rel[:44], exc))
            continue

        gap = s4_rec / s4_min - 1.0 if s4_min > 0 else 0.0
        va = core.vec_from_trend_plunge(*arch['sigma1'])
        vb = core.vec_from_trend_plunge(*core.describe(best['T'])['sigma1'])
        dev = float(np.degrees(np.arccos(min(abs(float(va @ vb)), 1.0))))

        info = {}
        ip = os.path.join(d, 'INFO1')
        if os.path.exists(ip):
            info = tensorfile.read_info_lambda(ip)

        rows.append(dict(site=rel, n=len(site), phi_rec=arch['phi'],
                         s4_rec=s4_rec, s4_min=s4_min, gap=gap,
                         axis_dev=dev,
                         pass_no=info.get('pass_no', ''),
                         lam=info.get('lambda_invdir', '')))
        print('   %-44s n=%2d  gap %+6.1f%%  sigma1 off %5.1f deg'
              % (rel[:44], len(site), 100 * gap, dev))

    rows.sort(key=lambda r: -r['gap'])
    flagged = [r for r in rows
               if r['gap'] > FLAG_GAP or r['axis_dev'] > FLAG_AXIS]

    print('\n' + '=' * 78)
    print('%d runs screened, %d flagged' % (len(rows), len(flagged)))
    g = np.array([r['gap'] for r in rows])
    print('gap above the reachable minimum: median %+.1f%%, p90 %+.1f%%'
          % (100 * np.median(g), 100 * np.percentile(g, 90)))

    print('\nworst 15 by gap (the recorded answer sits this far above the '
          'best the data allow)')
    print('%-44s %3s %8s %8s %7s %6s' % ('site', 'n', 'S4 rec', 'S4 min',
                                         'gap', 'ax off'))
    for r in rows[:15]:
        print('%-44s %3d %8.3f %8.3f %+6.1f%% %6.1f'
              % (r['site'][:44], r['n'], r['s4_rec'], r['s4_min'],
                 100 * r['gap'], r['axis_dev']))

    print('\nre-running the flagged ones with their own recorded LAMBDA')
    print('%-40s %7s %7s %8s %8s' % ('site', 'ax rec', 'ax new', 'S4 rec',
                                     'S4 new'))
    for r in flagged[:20]:
        p = os.path.join(ROOT, r['site'])
        d = os.path.dirname(p)
        try:
            site = tensorfile.read_site(p)
            mohr = tensorfile.read_mohr(os.path.join(d, 'MOHR1'))
            arch = tensorfile.parse_result_line(site.result_line)
            n, s = site.n, site.s
            lam = r['lam'] if r['lam'] else None
            rr = invdir.run(n, s, n_pass=r['pass_no'] or 1,
                            lam_printed=lam)
            res = core.describe(rr['T'])
            va = core.vec_from_trend_plunge(*arch['sigma1'])
            vb = core.vec_from_trend_plunge(*res['sigma1'])
            dev = float(np.degrees(np.arccos(min(abs(float(va @ vb)), 1.0))))
            print('%-40s %7.1f %7.1f %8.3f %8.3f   sigma1 moved %.1f deg'
                  % (r['site'][:40], arch['sigma1'][0], res['sigma1'][0],
                     r['s4_rec'], core.S4(rr['T'], n, s), dev))
            r['s4_invd'] = core.S4(rr['T'], n, s)
            r['invd_dev'] = dev
        except Exception as exc:
            print('%-40s failed: %s' % (r['site'][:40], exc))

    keys = ['site', 'n', 'pass_no', 'lam', 'phi_rec', 's4_rec', 's4_min',
            'gap', 'axis_dev', 's4_invd', 'invd_dev']
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('\nwritten %s' % out_csv)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'archive_audit.csv')
