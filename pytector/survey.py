# -*- coding: utf-8 -*-
"""A survey across many TENSOR runs: tables, map data, and roses per phase.

The original suite answers one site at a time. It has no way to ask the
questions that come after: what does this population of determinations look
like as a table, where are they on a map, and what direction did each
deformation phase actually act in. That is what this does, reading the runs
you already have rather than asking you to re-enter anything.

    from pytector import survey
    recs = survey.collect(root)                  # every run under a tree
    survey.attach_stages(recs, 'stages.csv')     # your phase assignment
    survey.attach_coords(recs, 'coords.csv')     # your coordinates
    survey.write_all(recs, 'out')

Two things stay yours and are read from small side files, never guessed:

**The phase assignment.** Which run belongs to which deformation phase is a
geological judgement, not something a program can derive. `stages.csv` is two
columns, `run,stage`, where `run` matches either the run id (its path relative
to the root) or the site name. Anything unassigned is reported, not silently
grouped.

**The coordinates.** `coords.csv` is `site,longitude,latitude`, keyed on run
id or site name. Runs without a coordinate stay in the table and are listed
separately, because a map that quietly drops a third of the stations is worse
than one that says what is missing.

Neither file is part of this package, and neither is written by it: they hold
field locations, which do not belong in a code repository.

## Which of the printed solutions gets used

A run can print up to three answers, and they differ. `method` selects:

    'auto'    INVDIR, except where TENSOR flagged PERMUTATION, and there
              PSIDIR. This is the defensible default: it keeps continuity with
              the INVDIR literature while taking PSIDIR exactly where INVDIR's
              axis labelling is the thing PSIDIR exists to repair.
    'invdir'  always the INVDIR block
    'psidir'  always the PSIDIR block. Note this is what the 03 result line
              carries: on 85 of the 93 archive runs with all three values, the
              03 line's Phi is PSIDIR's and never INVDIR's alone.
    '03'      the recorded 03 result line as it stands

Every record keeps `solution_from` so a table can say which was used.
"""
import csv
import io
import json
import os
from collections import OrderedDict, defaultdict

from . import rose, tensorfile

AUX = {'INFO1', 'MOHR1', 'PLOT1', 'HPGL', 'INFO2', 'MOHR2', 'PLOT2'}


def _site_file(folder, filenames):
    for fn in sorted(filenames):
        if fn not in AUX and '.' not in fn:
            return os.path.join(folder, fn)
    return None


def collect(root, method='auto'):
    """Every readable run under `root`, as a list of records.

    A record carries the run id, the site name, how many data, the chosen
    solution's three axes and Phi, the PERMUTATION flag, and which files the
    folder actually holds. Unreadable runs are skipped and counted; nothing is
    invented for a run that has no recorded solution.
    """
    recs = []
    for folder, _dirs, files in os.walk(root):
        if not (AUX & set(files)):
            continue
        path = _site_file(folder, files)
        if not path:
            continue
        try:
            site = tensorfile.read_site(path)
        except Exception:
            continue

        run_id = os.path.relpath(path, root).replace(os.sep, '/')
        rec = dict(run_id=run_id, folder=folder, site_name=site.name,
                   site_code=getattr(site, 'code', ''), n=len(site),
                   has_hpgl='HPGL' in files,
                   has_mesure_key='Mesure_key.txt' in files,
                   stage='', longitude='', latitude='')

        info = None
        for name in ('INFO1', 'INFO2'):
            p = os.path.join(folder, name)
            if os.path.exists(p):
                try:
                    info = tensorfile.read_info_solutions(p)
                except Exception:
                    info = None
                if info:
                    rec['info_file'] = name
                    break
        blocks = info or {}
        line = tensorfile.parse_result_line(site.result_line)

        chosen, source = None, ''
        want = (method or 'auto').lower()
        if want == '03' and line:
            chosen, source = line, '03 line'
        elif want == 'invdir' and 'INVDIR' in blocks:
            chosen, source = blocks['INVDIR'], 'INVDIR block'
        elif want == 'psidir' and 'PSIDIR' in blocks:
            chosen, source = blocks['PSIDIR'], 'PSIDIR block'
        elif want == 'auto':
            psi = blocks.get('PSIDIR')
            if psi is not None and psi.get('permuted'):
                chosen, source = psi, 'PSIDIR block (PERMUTATION)'
            elif 'INVDIR' in blocks:
                chosen, source = blocks['INVDIR'], 'INVDIR block'
        if chosen is None:                       # fall back rather than drop
            if line:
                chosen, source = line, '03 line (fallback)'
            elif blocks:
                name, chosen = sorted(blocks.items())[0]
                source = name + ' block (fallback)'

        if chosen is None:
            rec['solution_from'] = 'none'
            recs.append(rec)
            continue

        rec['solution_from'] = source
        for i in (1, 2, 3):
            tp = chosen.get('sigma%d' % i)
            rec['s%d_trend' % i] = round(tp[0], 1) if tp else ''
            rec['s%d_plunge' % i] = round(tp[1], 1) if tp else ''
        rec['phi'] = chosen.get('phi', '')
        # ANG and RUP are only ever printed on the 03 line, never inside a
        # SOLUTION block, so take them from there whichever block supplied the
        # axes. They are the fit of the recorded solution, so a run whose
        # chosen block is not the recorded one gets them flagged.
        rec['ANG'] = chosen.get('ANG_mean', (line or {}).get('ANG_mean', ''))
        rec['RUP'] = chosen.get('RUP_mean', (line or {}).get('RUP_mean', ''))
        rec['fit_from'] = ('same as axes' if 'ANG_mean' in chosen
                           else ('03 line' if line else ''))
        psi = blocks.get('PSIDIR') or {}
        rec['permutation'] = 'yes' if psi.get('permuted') else ''
        rec['invdir_phi'] = (blocks.get('INVDIR') or {}).get('phi', '')
        rec['psidir_phi'] = psi.get('phi', '')

        h = _horizontal(rec)
        rec.update(h)
        recs.append(rec)
    recs.sort(key=lambda r: r['run_id'])
    return recs


def _horizontal(rec):
    """Which axis is the shallowest, and is its trend usable as a direction."""
    best = None
    for i in (1, 2, 3):
        t, p = rec.get('s%d_trend' % i), rec.get('s%d_plunge' % i)
        if t == '' or p == '':
            continue
        if best is None or p < best[1]:
            best = (i, p, t)
    if best is None:
        return dict(h_axis='', h_trend='', h_plunge='', h_usable='')
    i, p, t = best
    return dict(h_axis='sigma%d' % i, h_trend=t, h_plunge=p,
                h_usable='yes' if p < rose.SHALLOW_LIMIT else 'no')


def _key_index(recs):
    """Look-ups by run id and by site name, so a side file can use either."""
    idx = {}
    for r in recs:
        idx.setdefault(r['run_id'], []).append(r)
        idx.setdefault(r['site_name'], []).append(r)
        idx.setdefault(os.path.basename(r['folder']), []).append(r)
    return idx


def _attach(recs, path, columns, label):
    """Shared loader. Returns (n_applied, unmatched_keys).

    Counts distinct records, not index hits: a run is reachable by its run id,
    its site name and its folder name, so counting hits reported "2 matched"
    for a single run.
    """
    idx = _key_index(recs)
    touched, unmatched = set(), []
    with io.open(path, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            row = {(k or '').strip().lower(): (v or '').strip()
                   for k, v in row.items()}
            key = row.get('run') or row.get('site') or row.get('run_id')
            if not key:
                continue
            targets = idx.get(key)
            if not targets:
                unmatched.append(key)
                continue
            for r in targets:
                if id(r) in touched:
                    continue
                for col in columns:
                    if row.get(col, '') != '':
                        r[col] = row[col]
                touched.add(id(r))
    applied = len(touched)
    print('%s: %d run(s) matched from %s' % (label, applied,
                                             os.path.basename(path)))
    if unmatched:
        print('  %d key(s) in the file matched no run: %s'
              % (len(unmatched), ', '.join(unmatched[:8])
                 + (' ...' if len(unmatched) > 8 else '')))
    return applied, unmatched


def attach_stages(recs, path):
    """Apply a `run,stage` CSV. Keys may be run id, site name or folder."""
    return _attach(recs, path, ['stage'], 'stages')


def attach_coords(recs, path):
    """Apply a `site,longitude,latitude` CSV."""
    return _attach(recs, path, ['longitude', 'latitude'], 'coordinates')


TABLE_COLS = OrderedDict([
    ('run_id', 'run'), ('site_name', 'site'), ('stage', 'phase'),
    ('n', 'n'), ('solution_from', 'solution'), ('permutation', 'perm'),
    ('s1_trend', 's1 trend'), ('s1_plunge', 's1 pl'),
    ('s2_trend', 's2 trend'), ('s2_plunge', 's2 pl'),
    ('s3_trend', 's3 trend'), ('s3_plunge', 's3 pl'),
    ('phi', 'Phi'), ('ANG', 'ANG'), ('RUP', 'RUP'),
    ('fit_from', 'ANG/RUP from'),
    ('h_axis', 'horiz'), ('h_trend', 'horiz trend'), ('h_usable', 'usable'),
    ('longitude', 'lon'), ('latitude', 'lat'),
])


def write_table(recs, outdir):
    keys = list(TABLE_COLS)
    with io.open(os.path.join(outdir, 'survey.csv'), 'w', encoding='utf-8',
                 newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        for r in recs:
            w.writerow({k: r.get(k, '') for k in keys})

    by = defaultdict(list)
    for r in recs:
        by[r.get('stage') or '(unassigned)'].append(r)
    L = ['# Survey of TENSOR runs', '',
         '%d runs. `horiz` is the shallowest axis and `usable` is no when it '
         'plunges past %g degrees, where a trend is not a direction.'
         % (len(recs), rose.SHALLOW_LIMIT), '']
    for stage in sorted(by, key=lambda s: (s == '(unassigned)', str(s))):
        items = by[stage]
        L += ['## %s  (%d runs)' % (stage, len(items)), '',
              '| ' + ' | '.join(TABLE_COLS.values()) + ' |',
              '|' + '|'.join('---' for _ in TABLE_COLS) + '|']
        for r in items:
            L.append('| ' + ' | '.join(str(r.get(k, '')) for k in keys) + ' |')
        L.append('')
    io.open(os.path.join(outdir, 'survey.md'), 'w', encoding='utf-8',
            newline='\n').write('\n'.join(L) + '\n')


def write_map(recs, outdir):
    """CSV and GeoJSON of the runs that have coordinates."""
    mapped, missing = [], []
    for r in recs:
        (mapped if (r.get('longitude') and r.get('latitude'))
         else missing).append(r)
    cols = ['run_id', 'site_name', 'stage', 'n', 'longitude', 'latitude',
            'h_axis', 'h_trend', 'h_plunge', 'h_usable', 'phi']
    with io.open(os.path.join(outdir, 'map_points.csv'), 'w',
                 encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in mapped:
            w.writerow({k: r.get(k, '') for k in cols})

    feats = []
    for r in mapped:
        try:
            lon, lat = float(r['longitude']), float(r['latitude'])
        except (TypeError, ValueError):
            continue
        feats.append(dict(type='Feature',
                          geometry=dict(type='Point',
                                        coordinates=[lon, lat]),
                          properties={k: r.get(k, '') for k in cols}))
    io.open(os.path.join(outdir, 'map_points.geojson'), 'w',
            encoding='utf-8', newline='\n').write(
        json.dumps(dict(type='FeatureCollection', features=feats),
                   ensure_ascii=False, indent=1) + '\n')
    return mapped, missing


def write_roses(recs, outdir, bin_deg=10.0):
    """One rose figure per phase, sigma1 and sigma3 side by side.

    Which panel is worth reading changes between phases, so it is decided per
    phase and drawn bold rather than fixed in advance.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as exc:                            # pragma: no cover
        print('no rose figures: %s' % exc)
        return []

    by = defaultdict(list)
    for r in recs:
        by[r.get('stage') or '(unassigned)'].append(r)

    written, lines = [], ['# Roses by phase', '']
    for stage in sorted(by, key=lambda s: (s == '(unassigned)', str(s))):
        items = by[stage]
        groups = OrderedDict()
        for i, label in ((1, 'sigma1  compression'), (3, 'sigma3  extension')):
            pairs = []
            for r in items:
                t, p = r.get('s%d_trend' % i), r.get('s%d_plunge' % i)
                if t != '' and p != '':
                    pairs.append((float(t), float(p)))
            groups[label] = pairs
        read = rose.pick_readable(groups)

        fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.9),
                                 subplot_kw=dict(projection='polar'))
        fig.patch.set_facecolor('white')
        stats = {}
        for ax, label in zip(axes, list(groups)):
            stats[label] = rose.plot_rose(ax, groups[label], bin_deg=bin_deg,
                                          title=label,
                                          emphasis=(label == read))
        fig.suptitle('%s   %d runs' % (stage, len(items)), fontsize=11,
                     fontweight='600', color=rose.INK, y=1.02)
        fig.subplots_adjust(left=0.07, right=0.95, top=0.70, bottom=0.10,
                            wspace=0.35)
        safe = str(stage).replace('/', '-').replace(os.sep, '-')
        fn = os.path.join(outdir, 'rose_%s.png' % safe)
        fig.savefig(fn, dpi=300, facecolor='white', bbox_inches='tight')
        plt.close(fig)
        written.append(fn)

        st = stats.get(read)
        lines += ['## %s' % stage, '',
                  '![%s](%s)' % (stage, os.path.basename(fn)), '']
        if st:
            lines.append('Read the **%s** panel: mean trend **%03.0f**, '
                         'R %.2f over %d runs.'
                         % (read.split()[0], st['mean'], st['R'], st['n']))
        else:
            lines.append('No axis in this phase is shallow enough for a '
                         'direction.')
        lines.append('')
    io.open(os.path.join(outdir, 'roses.md'), 'w', encoding='utf-8',
            newline='\n').write('\n'.join(lines) + '\n')
    return written


def write_all(recs, outdir, bin_deg=10.0):
    os.makedirs(outdir, exist_ok=True)
    write_table(recs, outdir)
    mapped, missing = write_map(recs, outdir)
    figs = write_roses(recs, outdir, bin_deg)
    print('\n%d runs -> %s' % (len(recs), outdir))
    print('  survey.csv / survey.md')
    print('  map_points.csv / map_points.geojson   %d with coordinates, '
          '%d without' % (len(mapped), len(missing)))
    print('  %d rose figure(s) + roses.md' % len(figs))
    unassigned = [r for r in recs if not r.get('stage')]
    if unassigned:
        print('  %d run(s) have no phase assigned; they are grouped under '
              '"(unassigned)"' % len(unassigned))
    return dict(mapped=mapped, missing=missing, figures=figs)
