# -*- coding: utf-8 -*-
"""Build the paleostress database: one place that answers "where did this
number come from".

The material is in three piles that have never been joined up.

  103 TENSOR run folders on disk, 801 fault-slip data. Every one carries an
      INFO1 and an HPGL, 89 carry a MOHR1, and only 38 carry the Mesure_key.txt
      that holds the original field readings.
   47 adopted solutions in the thesis table, 368 data. So more than half the
      archive is sensitivity tests, back-tilt trials, alternate versions of the
      same site, and the 25 runs done for someone else's data.
   34 localities with coordinates, under names that do not always match the
      station names in the solution table.

The join is the point. A run folder is NOT automatically the run whose numbers
reached the thesis: site 0404-04C-1 holds 49.5/8.1, Phi 0.444, ANG 3.9, RUP
23.1, while the adopted table records 48/11, 0.457, 6, 25. Those are different
determinations of the same station. Until the two are matched, "the archive
says" and "the thesis says" are not the same claim, and neither is traceable.

So each adopted solution is matched back to the run that produced it by
comparing the recorded 03 result line, and anything that fails to match is
reported rather than quietly dropped.

Output is written to a directory given on the command line (default
F:\\古應力資料庫): a SQLite file for querying, plus a CSV of every table for
Excel and for Dataview, plus a README recording what was matched and what was
not. Nothing in the source folders is modified.

    python research/build_database.py [outdir]
"""
import csv
import io
import os
import re
import sqlite3
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from pytector import core, plot, tensorfile          # noqa: E402
from pytector.tensorfile import RAKE_OFFSET          # noqa: E402

ARCHIVE = os.environ.get(
    'PYTECTOR_ARCHIVE',
    r'<PYTECTOR_ARCHIVE>')
ADOPTED = r'<PYTECTOR_ADOPTED>'
LOCALITIES = (r'<PYTECTOR_LOCALITIES_DIR>'
              r'\localities 3.csv')
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else r'<PYTECTOR_DB_OUT>'

#: folder names record the trial rotation, e.g. "0404-04C(backtilted 020 -20)"
BACKTILT = re.compile(r'backtilt\w*\s*\(?\s*(\d{1,3})\s*[, ]\s*([+-]?\d{1,3})',
                      re.I)
ANYTILT = re.compile(r'backtilt', re.I)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding='utf-8-sig') as fh:
        return [{(k or '').strip(): (v.strip() if isinstance(v, str) else v)
                 for k, v in row.items()}
                for row in csv.DictReader(fh)]


def info_text(folder):
    for nm in ('INFO1', 'INFO2', 'INFO3'):
        p = os.path.join(folder, nm)
        if os.path.exists(p):
            with open(p, errors='replace') as fh:
                return fh.read()
    return ''


#: INFO prints the INVDIR determination and then the PSIDIR one, each closing
#: with its own RATIO PHI. They are different numbers, and which of the two
#: reached the thesis table is exactly the question this database exists to
#: answer, so both are kept.
_BLOCK = re.compile(r'SOLUTION (INVDIR|PSIDIR)(.*?)RATIO PHI=\s*([\d.]+)',
                    re.S)
_AXIS = re.compile(r'AXIS SIGMA\s*(\d)\s*D=\s*([\d.]+)\s*P=\s*([\d.]+)')
_LAMBDA = re.compile(r'LAMBDA=\s*([\d.]+)')


def info_blocks(txt):
    """Both determinations out of one INFO file.

    Note the trap this makes visible: the PSIDIR block prints
    'LAMBDA= 0.87' immediately above its RATIO PHI, and that 0.87 is the
    constant sqrt(3)/2, identical in every run ever made. It is not a shape
    ratio. Reading it as one puts a station at the far end of the Phi range on
    the strength of a number that carries no information about that station.
    """
    out = {}
    for kind, body, phi in _BLOCK.findall(txt):
        key = kind[:6].lower()
        rec = {key + '_phi': float(phi)}
        lam = _LAMBDA.search(body)
        if lam:
            rec[key + '_lambda'] = float(lam.group(1))
        for i, d, p in _AXIS.findall(body):
            rec['%s_s%s_trend' % (key, i)] = float(d)
            rec['%s_s%s_plunge' % (key, i)] = float(p)
        if kind == 'PSIDIR':
            rec['psidir_flag'] = ('PERMUTATION' if 'PERMUTATION' in body
                                  else 'AXES OK !')
        out.update(rec)
    return out


def tp(pair):
    """'117/74' -> (117.0, 74.0); blank or malformed -> (None, None)."""
    if not pair or '/' not in pair:
        return None, None
    a, b = pair.split('/', 1)
    try:
        return float(a), float(b)
    except ValueError:
        return None, None


def sep(a, b):
    """Angle between two (trend, plunge) axes, in degrees. Axes, not vectors,
    so antipodal counts as identical."""
    if a[0] is None or b[0] is None:
        return None
    u = core.vec_from_trend_plunge(*a)
    v = core.vec_from_trend_plunge(*b)
    return float(np.degrees(np.arccos(min(abs(float(u @ v)), 1.0))))


# ----------------------------------------------------------------- runs ----
def collect_runs():
    rows, data = [], []
    for path in tensorfile.discover(ARCHIVE):
        folder = os.path.dirname(path)
        rel = os.path.relpath(folder, ARCHIVE)
        group = rel.split(os.sep)[0] if os.sep in rel else '(root)'
        # a folder can hold more than one site file (Juisui/HY1 holds four), so
        # the key has to be the file, not the folder
        run_id = os.path.relpath(path, ARCHIVE).replace(os.sep, '/')

        try:
            site = tensorfile.read_site(path)
        except Exception as exc:                      # keep the row, flag it
            rows.append(dict(run_id=run_id, folder=rel, grp=group,
                             site_file=os.path.basename(path),
                             read_error=str(exc)[:200]))
            continue

        txt = info_text(folder)
        lam = {}
        for nm in ('INFO1', 'INFO2', 'INFO3'):
            p = os.path.join(folder, nm)
            if os.path.exists(p):
                lam = tensorfile.read_info_lambda(p)
                break

        res = (tensorfile.parse_result_line(site.result_line)
               if site.result_line else None)

        m = BACKTILT.search(os.path.basename(folder))
        row = dict(
            run_id=run_id, folder=rel, grp=group,
            site_file=os.path.basename(path), site_name=site.name,
            site_code=site.code, n_data=len(site),
            has_info=bool(txt), has_mohr=os.path.exists(
                os.path.join(folder, 'MOHR1')),
            has_hpgl=os.path.exists(os.path.join(folder, 'HPGL')),
            has_mesure_key=os.path.exists(
                os.path.join(folder, 'Mesure_key.txt')),
            has_result=bool(res),
            is_backtilted=bool(ANYTILT.search(rel)),
            tilt_trend=float(m.group(1)) if m else None,
            tilt_angle=float(m.group(2)) if m else None,
            pass_no=lam.get('pass_no'),
            lambda_invdir=lam.get('lambda_invdir'),
            lambda_psidir=lam.get('lambda_psidir'),
            taumax=lam.get('taumax'),
            read_error=None)
        row.update(info_blocks(txt))
        if res:
            row.update(method=res['method'], acc=res['acc'], phi=res['phi'],
                       ang_mean=res['ANG_mean'], rup_mean=res['RUP_mean'],
                       s1_trend=res['sigma1'][0], s1_plunge=res['sigma1'][1],
                       s2_trend=res['sigma2'][0], s2_plunge=res['sigma2'][1],
                       s3_trend=res['sigma3'][0], s3_plunge=res['sigma3'][1])
        rows.append(row)

        # per-datum: the field reading, plus the Mohr numbers where the run
        # recorded them. MOHR1 rows are in file order, same order as the data.
        mohr = None
        mp = os.path.join(folder, 'MOHR1')
        if os.path.exists(mp):
            try:
                t = tensorfile.read_mohr(mp)['table']
                if len(t) == len(site):
                    mohr = t
            except Exception:
                mohr = None
        sides = plot.strike_slip_sign_vectors(site.n, site.s)
        for i, rec in enumerate(site.records):
            d = dict(run_id=run_id, idx=i + 1,
                     dipaz=rec['dipaz'], dip=rec['dip'], rake=rec['rake'],
                     slip_rake=(rec['rake'] + RAKE_OFFSET) % 360.0,
                     confidence=rec.get('confidence'),
                     sense=rec.get('sense'),
                     strike_slip_side=int(sides[i]))
            if mohr is not None:
                d.update(sigmn=float(mohr[i][0]), tau=float(mohr[i][1]),
                         taust=float(mohr[i][2]), rup=float(mohr[i][3]),
                         ang=float(mohr[i][4]))
            data.append(d)
    return rows, data


# ------------------------------------------------------------- adopted ----
def match_adopted(adopted, runs):
    """Tie each thesis solution to the run that produced it.

    Matched on axes, mean ANG and mean RUP, which agree to the precision the
    table carries wherever a match exists at all. Axis agreement alone is not
    enough, because a back-tilted run and its parent often share an axis.

    Phi is deliberately NOT part of the test. It agrees for most stations
    (median difference 0.025) but is far out on a handful whose axes, ANG and
    RUP all match to the last digit, so it cannot be what identifies a run.
    It is recorded instead as phi_delta / phi_flag, i.e. as a finding.
    """
    # A run offers up to three published answers, and the thesis may have taken
    # any of them: the 03 result line, the INVDIR block, or the PSIDIR block.
    # Matching only the 03 line leaves five solutions looking unsourced when in
    # fact they were read off one of the other two.
    cands = []
    for r in runs:
        if r.get('has_result'):
            cands.append((r, '03 line',
                          [(r.get('s1_trend'), r.get('s1_plunge')),
                           (r.get('s2_trend'), r.get('s2_plunge')),
                           (r.get('s3_trend'), r.get('s3_plunge'))],
                          r.get('phi'), r.get('ang_mean'), r.get('rup_mean')))
        for key, lab in (('invdir', 'INVDIR block'), ('psidir', 'PSIDIR block')):
            ax = [(r.get('%s_s%d_trend' % (key, i)),
                   r.get('%s_s%d_plunge' % (key, i))) for i in (1, 2, 3)]
            if all(a[0] is not None for a in ax):
                # the blocks print no ANG/RUP of their own; those belong to the
                # data table and are shared with the 03 line
                cands.append((r, lab, ax, r.get('%s_phi' % key),
                              r.get('ang_mean'), r.get('rup_mean')))

    out = []
    for sol in adopted:
        want = [tp(sol.get('s1_trend_plunge')), tp(sol.get('s2_trend_plunge')),
                tp(sol.get('s3_trend_plunge'))]
        best = None
        for r, lab, got, cphi, cang, crup in cands:
            devs = [sep(a, b) for a, b in zip(want, got)]
            if any(d is None for d in devs):
                continue
            axis = max(devs)
            try:
                dphi = abs(float(sol['RAP']) - cphi)
            except (TypeError, ValueError, KeyError):
                dphi = float('inf')
            try:
                dang = abs(float(sol['ANG']) - cang)
                drup = abs(float(sol['RUP']) - crup)
            except (TypeError, ValueError, KeyError):
                dang = drup = float('inf')
            score = (axis, dang, drup, dphi)
            if best is None or score < best[0]:
                best = (score, r, lab)
        # Independent of any archive: three principal axes are mutually
        # perpendicular, so the recorded triple has to be orthogonal to within
        # rounding. This catches a mistyped digit without needing to find the
        # run at all. LY-11-2 is recorded as 210/69, 326/19, 060/18, and no
        # orthogonal triple has those plunges: sin^2 sums to 1.073.
        rec = dict(sol)
        if all(a[0] is not None for a in want):
            v = [core.vec_from_trend_plunge(*a) for a in want]
            worst = max(abs(90.0 - float(np.degrees(np.arccos(
                min(abs(float(v[i] @ v[j])), 1.0)))))
                for i, j in ((0, 1), (0, 2), (1, 2)))
            rec['orthogonality_err_deg'] = round(worst, 2)
            rec['orthogonality_flag'] = ('' if worst <= 1.5
                                         else ('check' if worst <= 4
                                               else 'IMPOSSIBLE'))
        if best is None:
            rec.update(matched_run=None, match_axis_deg=None, match='none')
            out.append(rec)
            continue
        (axis, dang, drup, dphi), r, lab = best
        if axis <= 1.5 and dang <= 0.6 and drup <= 0.6:
            q = 'exact'
        elif axis <= 1.5:
            q = 'axes only'         # same axes, different determination
        elif axis <= 6.0:
            q = 'near'
        else:
            q = 'none'
        # Which of the numbers the run actually printed is the table's RAP?
        # Candidates, in the order they appear in INFO: the INVDIR ratio, the
        # PSIDIR ratio, and the constant on the PSIDIR LAMBDA line.
        try:
            rap = float(sol['RAP'])
        except (TypeError, ValueError, KeyError):
            rap = None
        src, best_d = None, None
        if rap is not None:
            for name, val in (('INVDIR PHI', r.get('invdir_phi')),
                              ('PSIDIR PHI', r.get('psidir_phi')),
                              ('03 line', r.get('phi')),
                              ('LAMBDA (not a ratio)',
                               r.get('psidir_lambda'))):
                if val is None:
                    continue
                d = abs(rap - val)
                if best_d is None or d < best_d:
                    src, best_d = name, d

        ok = q != 'none'
        rec.update(matched_run=r['run_id'] if ok else None,
                   matched_block=lab if ok else None,
                   run_phi=r.get('phi') if ok else None,
                   run_ang=r.get('ang_mean') if ok else None,
                   run_rup=r.get('rup_mean') if ok else None,
                   run_n=r.get('n_data') if ok else None,
                   run_invdir_phi=r.get('invdir_phi') if ok else None,
                   run_psidir_phi=r.get('psidir_phi') if ok else None,
                   run_psidir_flag=r.get('psidir_flag') if ok else None,
                   match_axis_deg=round(axis, 2),
                   match_dang=round(dang, 2), match_drup=round(drup, 2),
                   rap_source=src,
                   rap_source_delta=(None if best_d is None
                                     else round(best_d, 4)),
                   phi_delta=(None if dphi == float('inf')
                              else round(dphi, 4)),
                   phi_flag=('' if dphi <= 0.05
                             else ('check' if dphi <= 0.15 else 'CHECK')),
                   match=q)
        out.append(rec)
    return out


# --------------------------------------------------------------- write ----
def write_table(cur, name, rows, extra_cols=()):
    cols, seen = [], set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    for k in extra_cols:
        if k not in seen:
            seen.add(k)
            cols.append(k)
    if not cols:
        return []
    cur.execute('DROP TABLE IF EXISTS "%s"' % name)
    cur.execute('CREATE TABLE "%s" (%s)'
                % (name, ', '.join('"%s"' % c for c in cols)))
    cur.executemany(
        'INSERT INTO "%s" VALUES (%s)' % (name, ','.join('?' * len(cols))),
        [[r.get(c) for c in cols] for r in rows])
    return cols


def dump_csv(path, cols, rows):
    with io.open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in cols})


def main():
    if not os.path.isdir(ARCHIVE):
        print('archive not found:', ARCHIVE)
        return 1
    os.makedirs(OUTDIR, exist_ok=True)

    print('reading %d run folders ...' % len(tensorfile.discover(ARCHIVE)))
    runs, data = collect_runs()
    adopted = match_adopted(read_csv(ADOPTED), runs)
    localities = read_csv(LOCALITIES)

    db = os.path.join(OUTDIR, 'paleostress.db')
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    cur = con.cursor()
    tables = [('run', runs), ('datum', data),
              ('solution', adopted), ('locality', localities)]
    for name, rows in tables:
        cols = write_table(cur, name, rows)
        dump_csv(os.path.join(OUTDIR, name + '.csv'), cols, rows)
        print('  %-10s %4d rows, %2d columns' % (name, len(rows), len(cols)))
    con.commit()

    # ---- what the join actually achieved, which is the useful output ----
    q = {}
    for r in adopted:
        q[r.get('match')] = q.get(r.get('match'), 0) + 1
    print('\nadopted solutions matched back to a run:')
    for k in ('exact', 'axes only', 'near', 'none'):
        if q.get(k):
            print('   %-10s %d' % (k, q[k]))

    unresolved = [r for r in adopted if r.get('match') != 'exact']
    if unresolved:
        print('\nno run reproduces these, so their provenance is open:')
        for r in unresolved:
            print('   %-4s %-22s %-9s axes %s  dANG %s dRUP %s'
                  % (r.get('New_NO'), r.get('site'), r.get('match'),
                     r.get('match_axis_deg'), r.get('match_dang'),
                     r.get('match_drup')))

    src = {}
    for r in adopted:
        if r.get('rap_source'):
            src[r['rap_source']] = src.get(r['rap_source'], 0) + 1
    print('\nwhere each table RAP came from, matched against what the run '
          'printed:')
    for k, v in sorted(src.items(), key=lambda kv: -kv[1]):
        print('   %-24s %d' % (k, v))

    odd = [r for r in adopted
           if r.get('rap_source') not in (None, 'INVDIR PHI', 'PSIDIR PHI',
                                          '03 line')
           or (r.get('rap_source_delta') or 0) > 0.02]
    if odd:
        print('\nRAP values that do not reproduce any number the run printed:')
        print('   %-4s %-22s %7s %8s %8s %8s  %s'
              % ('NO', 'site', 'RAP', 'INVDIR', 'PSIDIR', 'delta', 'nearest'))
        for r in sorted(odd, key=lambda r: -(r.get('rap_source_delta') or 0)):
            print('   %-4s %-22s %7s %8s %8s %8s  %s'
                  % (r.get('New_NO'), r.get('site'), r.get('RAP'),
                     r.get('run_invdir_phi'), r.get('run_psidir_phi'),
                     r.get('rap_source_delta'), r.get('rap_source')))

    used = set(r['matched_run'] for r in adopted if r.get('matched_run'))
    print('\nruns: %d total, %d referenced by the thesis, %d not'
          % (len(runs), len(used), len(runs) - len(used)))
    print('data: %d fault slips on disk, %d in the adopted solutions'
          % (len(data),
             sum(int(r['n'] or 0) for r in adopted if (r.get('n') or '').strip()
                 .isdigit())))
    con.close()
    print('\nwritten to', OUTDIR)
    return 0


if __name__ == '__main__':
    sys.exit(main())
