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
import math
import os
import re
from collections import OrderedDict, defaultdict

from . import rose, tensorfile

AUX = {'INFO1', 'MOHR1', 'PLOT1', 'HPGL', 'INFO2', 'MOHR2', 'PLOT2'}

#: The suite's output files are extension-less too, and it numbers them when a
#: previous one exists: INFO1, INFO2, PLOT1, PLOT12. Matching a fixed set is
#: therefore not enough. Getting this wrong is silent and expensive: a build
#: whose exclusion list stopped at the "1" names read INFO2, MOHR2, PLOT2 and
#: PLOT12 as though they were fault data, and reported 103 runs where the
#: archive holds 92. Four of the eleven even carried a Phi, because a MOHR file
#: opens with an 02 line and ends with the 03 result line, so the site reader
#: found something that looked like a solution.
_OUTPUT = re.compile(r'^(INFO|MOHR|PLOT|HPGL|DESSIN|TRA|VISION)\d*$', re.I)


def _site_file(folder, filenames):
    """The one fault-data file in a run folder, or None.

    A site file has no extension and is not one of the suite's own outputs.
    """
    for fn in sorted(filenames):
        if '.' in fn or fn in AUX or _OUTPUT.match(fn):
            continue
        return os.path.join(folder, fn)
    return None


def _num(value):
    """A float, or None. Blank cells, None and unparseable text all become
    None, so callers need one guard instead of three. Real archives contain
    all three cases; a one-run fixture contains none of them."""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
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
        # The FOLDER is the station, not the file inside it. On a real archive
        # those disagree on 57 of 92 runs: a file called PANG is the author,
        # BOUNDARY is a description, LL-11 is a typo for LY-11, and several
        # files carry the original field number rather than the station name.
        # Worse, the file name is not unique: LL-3b-1 and LL-3b-2 both hold a
        # file called LL-3B, so keying on it merges two distinct runs.
        rec = dict(run_id=run_id, folder=folder,
                   site=os.path.basename(folder),
                   file_name=site.name,
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
            rec['_records'] = site.records
            recs.append(rec)
            continue

        rec['solution_from'] = source
        rec['_records'] = site.records
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
        t = _num(rec.get('s%d_trend' % i))
        p = _num(rec.get('s%d_plunge' % i))
        if t is None or p is None:
            continue
        if best is None or p < best[1]:
            best = (i, p, t)
    if best is None:
        return dict(h_axis='', h_trend='', h_plunge='', h_usable='')
    i, p, t = best
    return dict(h_axis='sigma%d' % i, h_trend=t, h_plunge=p,
                h_usable='yes' if p < rose.SHALLOW_LIMIT else 'no')


def _key_index(recs):
    """Look-ups by name, in two tiers.

    Returns (primary, secondary). The primary index is keyed on the run id and
    the station (folder) name, both of which identify a run. The secondary is
    keyed on the file name inside the folder, which does not: `MY1` and `MY`
    both hold a file called MY, and `LY-15`, `LY-15-1` and `LY-15-2` all hold
    one called LY-15.

    Callers must try the primary first and only fall back to the secondary.
    Merging the two and taking whatever matched meant a row keyed `MY` landed
    on the station MY1 as well, and the values only came out right because
    MY1's own row happened to be read first. Nothing should depend on the
    order of rows in a CSV.

    A run is also reachable by three names of which two are very often the
    same string, so each tier de-duplicates: without that, every such key
    reported itself as ambiguous, which on a 47-station folder was 18 warnings
    about conflicts that did not exist.
    """
    primary, secondary = {}, {}
    for r in recs:
        for key in {r['run_id'], r['site']}:
            if key:
                primary.setdefault(str(key), []).append(r)
    for r in recs:
        key = r.get('file_name')
        if key and str(key) not in primary:
            secondary.setdefault(str(key), []).append(r)
    return primary, secondary


def _attach(recs, path, columns, label):
    """Shared loader. Returns (n_applied, unmatched_keys).

    Counts distinct records, not index hits: a run is reachable by its run id,
    its site name and its folder name, so counting hits reported "2 matched"
    for a single run.
    """
    primary, secondary = _key_index(recs)
    touched, unmatched, ambiguous = set(), [], []
    with io.open(path, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            row = {(k or '').strip().lower(): (v or '').strip()
                   for k, v in row.items()}
            key = row.get('run') or row.get('site') or row.get('run_id')
            if not key:
                continue
            # run id and station name first; the file name only when neither
            # names anything, because it is not unique
            targets = primary.get(key) or secondary.get(key)
            if not targets:
                unmatched.append(key)
                continue
            if len(targets) > 1:
                ambiguous.append((key, [t['run_id'] for t in targets]))
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
    for key, runs in ambiguous:
        print('  ambiguous key %r matched %d runs, applied to all: %s'
              % (key, len(runs), ', '.join(runs)))
        print('    use the station (folder) name or the run id to be precise')
    return applied, unmatched


#: columns read_solutions understands. Only site is required.
IMPORT_COLS = {
    'site': 'site', 'station': 'site', 'no': 'site', 'name': 'site',
    'stage': 'stage', 'phase': 'stage',
    'type': 'type', 'regime': 'type',
    'n': 'n', 'phi': 'phi', 'rap': 'phi',
    'ang': 'ANG', 'rup': 'RUP',
    'longitude': 'longitude', 'lon': 'longitude',
    'latitude': 'latitude', 'lat': 'latitude',
    's1_trend': 's1_trend', 's1_plunge': 's1_plunge',
    's2_trend': 's2_trend', 's2_plunge': 's2_plunge',
    's3_trend': 's3_trend', 's3_plunge': 's3_plunge',
    'source': 'source', 'note': 'note',
}


def read_solutions(path, source=None):
    """Solutions from a CSV, for data that has no run folder behind it.

    Published determinations arrive as a table, not as a TENSOR archive, and
    comparing them against one's own is an ordinary thing to want. Rows here
    carry the same keys `collect` produces, so the table, the roses, the map
    and the export all treat them the same way.

    What they do NOT carry is a run. `solution_from` is set to 'imported' and
    the fault data is absent, so nothing downstream can claim these numbers
    are traceable to an inversion this program can repeat. That distinction
    is the whole reason for the separate field.
    """
    label = source or os.path.splitext(os.path.basename(path))[0]
    out = []
    with io.open(path, encoding='utf-8-sig', newline='') as fh:
        for i, row in enumerate(csv.DictReader(
                l for l in fh if not l.lstrip().startswith('#'))):
            rec = dict(run_id='%s/%d' % (label, i + 1), folder='',
                       file_name='', site_code='', n='',
                       has_hpgl=False, has_mesure_key=False,
                       stage='', type='', longitude='', latitude='',
                       solution_from='imported', source=label,
                       permutation='', fit_from='')
            for key, value in row.items():
                k = IMPORT_COLS.get((key or '').strip().lower())
                if k:
                    rec[k] = (value or '').strip()
            if not str(rec.get('site', '')).strip():
                continue
            rec.update(_horizontal(rec))
            out.append(rec)
    print('%s: %d solution(s) imported from %s'
          % (label, len(out), os.path.basename(path)))
    return out


def attach_stages(recs, path):
    """Apply a `run,stage` CSV. Keys may be run id, site name or folder."""
    return _attach(recs, path, ['stage'], 'stages')


def attach_coords(recs, path):
    """Apply a `site,longitude,latitude` CSV."""
    return _attach(recs, path, ['longitude', 'latitude'], 'coordinates')


TABLE_COLS = OrderedDict([
    ('site', 'station'), ('stage', 'phase'), ('run_id', 'run'),
    ('file_name', 'file'),
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


FAULT_COLS = OrderedDict([
    ('site', 'station'), ('stage', 'phase'), ('run_id', 'run'),
    ('idx', 'no'), ('code', 'code'), ('confidence', 'conf'),
    ('sense', 'sense'), ('strike', 'strike'), ('dip', 'dip'),
    ('dipaz', 'dip az'), ('rake', 'rake'),
    ('as_typed', 'as typed'),
])


def write_faults(recs, outdir):
    """One row per fault datum, across every run.

    This is the other half of what the archive holds: the solutions say what
    the stress was, these say what was measured. Strike is given as well as
    dip azimuth because the field convention is strike and the file stores dip
    azimuth, and mixing those up rotates every plane by 90 degrees.

    `rake` is as stored, which is TENSOR's convention; the movement direction
    is rake + 180 (see tensorfile.RAKE_OFFSET). Left as stored rather than
    silently converted, so the column means the same thing as the file.

    There is deliberately no computed dip-quadrant letter. The letter is not
    unique: for strike 115 both W and S resolve to dip azimuth 205, so a
    canonical one disagreed with what the observer wrote on 80 of 800 archive
    data while describing the same plane. `dipaz` is unambiguous and
    `as_typed` preserves the original notation; a third, differently derived
    letter would only invite the confusion it caused here.
    """
    rows = []
    for r in recs:
        for i, d in enumerate(r.get('_records') or [], start=1):
            dipaz = d.get('dipaz')
            rows.append({
                'run_id': r['run_id'], 'site': r['site'],
                'stage': r.get('stage', ''), 'idx': i,
                'code': d.get('code', ''),
                'confidence': d.get('confidence', ''),
                'sense': d.get('sense', d.get('movement', '')),
                'strike': ('%03.0f' % ((dipaz - 90.0) % 360.0)
                           if dipaz is not None else ''),
                'dip': d.get('dip', ''),
                'dipaz': dipaz if dipaz is not None else '',
                'rake': (round(d['rake'], 1) if d.get('rake') is not None
                         else ''),
                'as_typed': (d.get('tail') or '').strip(),
            })
    keys = list(FAULT_COLS)
    with io.open(os.path.join(outdir, 'faults.csv'), 'w', encoding='utf-8',
                 newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, '') for k in keys})
    return rows


def write_map(recs, outdir):
    """CSV and GeoJSON of the runs that have coordinates."""
    mapped, missing = [], []
    for r in recs:
        (mapped if (r.get('longitude') and r.get('latitude'))
         else missing).append(r)
    cols = ['site', 'stage', 'run_id', 'n', 'longitude', 'latitude',
            'h_axis', 'h_trend', 'h_plunge', 'h_usable', 'phi']
    with io.open(os.path.join(outdir, 'map_points.csv'), 'w',
                 encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in mapped:
            w.writerow({k: r.get(k, '') for k in cols})

    feats = []
    for r in mapped:
        lon, lat = _num(r.get('longitude')), _num(r.get('latitude'))
        if lon is None or lat is None:
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


#: half-length of a plotted stress axis, in metres on the ground
AXIS_HALF_LENGTH_M = 700.0
#: metres per degree of latitude, near enough anywhere for a map symbol
_M_PER_DEG = 111320.0


def write_stress_axes(recs, outdir, half_m=AXIS_HALF_LENGTH_M,
                      axes=('sigma1', 'sigma3')):
    """GeoJSON of the stress axes as LINES, for a GIS to draw directly.

    map_points.geojson carries the trend as an attribute, which leaves the
    reader to set up a rotated marker before anything points anywhere. This
    writes the geometry itself: a segment centred on the station and lying
    along the axis, so the layer draws as a stress map the moment it is opened.

    The segment runs both ways from the station because a stress axis has no
    arrowhead. 020 and 200 are the same line, and a half-line would assert a
    direction the data does not contain.

    Only shallow axes are drawn. The trend of a steeply plunging axis is
    close to arbitrary, and a map full of confident little lines that mean
    nothing is worse than a gap. Which ones were dropped is returned.
    """
    feats, drawn, skipped = [], 0, []
    for r in recs:
        lon, lat = _num(r.get('longitude')), _num(r.get('latitude'))
        if lon is None or lat is None:
            continue
        for label in axes:
            i = int(label[-1])
            trend = _num(r.get('s%d_trend' % i))
            plunge = _num(r.get('s%d_plunge' % i))
            if trend is None or plunge is None:
                continue
            if plunge >= rose.SHALLOW_LIMIT:
                skipped.append((r.get('site', ''), label, plunge))
                continue
            # trend is measured clockwise from north, so north is +lat and
            # east is +lon; longitude degrees shrink with latitude
            th = math.radians(trend)
            dlat = (half_m * math.cos(th)) / _M_PER_DEG
            dlon = (half_m * math.sin(th)) / (
                _M_PER_DEG * max(0.05, math.cos(math.radians(lat))))
            feats.append(dict(
                type='Feature',
                geometry=dict(type='LineString', coordinates=[
                    [lon - dlon, lat - dlat], [lon + dlon, lat + dlat]]),
                properties=dict(
                    site=r.get('site', ''), stage=r.get('stage', ''),
                    type=r.get('type', ''), axis=label,
                    trend=round(trend), plunge=round(plunge),
                    n=r.get('n', ''), phi=r.get('phi', ''),
                    run_id=r.get('run_id', ''))))
            drawn += 1

    path = os.path.join(outdir, 'stress_axes.geojson')
    io.open(path, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(dict(type='FeatureCollection', features=feats),
                   ensure_ascii=False, indent=1) + '\n')
    return drawn, skipped


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
                t = _num(r.get('s%d_trend' % i))
                p = _num(r.get('s%d_plunge' % i))
                if t is not None and p is not None:
                    pairs.append((t, p))
            groups[label] = pairs

        # Decide on the regime where the fault type is recorded, and fall back
        # to counting only when it is not. Counting cannot separate two axes
        # that are both horizontal, which is every strike-slip phase; see
        # rose.axis_for_regime for the case that exposed it.
        by_sigma = {'sigma1': groups['sigma1  compression'],
                    'sigma3': groups['sigma3  extension']}
        pick, _why = rose.axis_for_regime([r.get('type') for r in items],
                                          by_sigma)
        read = ({'sigma1': 'sigma1  compression',
                 'sigma3': 'sigma3  extension'}.get(pick)
                or rose.pick_readable(groups))

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


#: the columns a palaeostress table carries in this literature, in this order.
#: Position sits next to the site name because that is where a reader looks
#: for it, and four decimal places is about 11 m, which is finer than any of
#: these stations is actually known to.
_PUB = [('site', 'Site'),
        ('longitude', 'Long.'), ('latitude', 'Lat.'),
        ('stage', 'Stage'), ('n', 'N'),
        ('s1_trend', 'D'), ('s1_plunge', 'P'),
        ('s2_trend', 'D'), ('s2_plunge', 'P'),
        ('s3_trend', 'D'), ('s3_plunge', 'P'),
        ('phi', 'RAP'), ('ANG', 'ANG'), ('RUP', 'RUP'), ('q', 'Q')]

#: where the three spanning headers sit: (label, first column, last column)
_PUB_SPANS = [('Axe $\\sigma_1$', 5, 6), ('Axe $\\sigma_2$', 7, 8),
              ('Axe $\\sigma_3$', 9, 10)]


def _pub_rows(recs):
    """Values formatted as the printed table wants them, strings throughout."""
    rows = []
    for r in sorted(recs, key=lambda x: (str(x.get('stage', '')),
                                         str(x.get('site', '')))):
        out = []
        for key, _head in _PUB:
            v = r.get(key, '')
            if key in ('longitude', 'latitude'):
                v = '' if _num(v) is None else '%.4f' % _num(v)
            elif key == 'phi':
                v = '' if _num(v) is None else '%.2f' % _num(v)
            elif key in ('ANG', 'RUP') or key.endswith(('_trend', '_plunge')):
                v = '' if _num(v) is None else '%.0f' % _num(v)
            out.append('' if v is None else str(v))
        rows.append(out)
    return rows


def write_publication_table(recs, outdir, caption=None):
    """The solution table in the three shapes a paper actually needs.

    Journals in this field print one table and it always has the same shape:
    site, stage, N, then D and P for each of the three axes under a spanning
    header, then the ratio, the two fit measures and a quality letter. That
    layout is reproduced rather than invented, because a reader of this
    literature knows where to look on it.

    LaTeX with booktabs for a manuscript, HTML because pasting it into Word
    keeps the merged header that a CSV cannot carry, and Markdown for notes.
    None of the three is a spreadsheet: survey.csv is already that, and a
    table meant for print has different needs from one meant for sorting.
    """
    rows = _pub_rows(recs)
    cap = caption or 'Results of palaeostress determination'
    # by name, not by position. Inserting the two coordinate columns moved
    # every index after Site, and the phase count silently became a count of
    # distinct longitudes: 30 where there were five phases.
    col = {k: i for i, (k, _h) in enumerate(_PUB)}
    n_stage = len({r[col['stage']] for r in rows if r[col['stage']]})

    tex = ['% requires \\usepackage{booktabs}',
           '\\begin{table}[htbp]', '\\centering', '\\small',
           '\\caption{%s}' % cap,
           '\\begin{tabular}{l rr l r rr rr rr rrr c}', '\\toprule',
           '& & & & & '
           + ' & '.join('\\multicolumn{2}{c}{%s}' % lab
                        for lab, _a, _b in _PUB_SPANS)
           + ' & & & & \\\\',
           ''.join('\\cmidrule(lr){%d-%d}' % (a + 1, b + 1)
                   for _lab, a, b in _PUB_SPANS),
           'Site & Long. & Lat. & Stage & $N$ & $D$ & $P$ & $D$ & $P$'
           ' & $D$ & $P$ & RAP $\\Phi$ & ANG & RUP & $Q$ \\\\', '\\midrule']
    for r in rows:
        tex.append(' & '.join(v.replace('&', '\\&') for v in r) + ' \\\\')
    tex += ['\\bottomrule', '\\end{tabular}', '\\end{table}']
    io.open(os.path.join(outdir, 'table_publication.tex'), 'w',
            encoding='utf-8', newline='\n').write('\n'.join(tex) + '\n')

    html = ['<meta charset="utf-8">',
            '<table cellspacing="0" style="border-collapse:collapse;'
            'font-family:Times New Roman,serif;font-size:10pt">',
            '<caption style="text-align:left;padding:4px 0">%s</caption>'
            % cap,
            '<tr><td colspan="5" style="border-top:1.2pt solid #000"></td>'
            + ''.join(
                '<td colspan="2" style="border-top:1.2pt solid #000;'
                'border-bottom:0.5pt solid #000;text-align:center">'
                'Axe &sigma;<sub>%d</sub></td>' % i for i in (1, 2, 3))
            + '<td colspan="4" style="border-top:1.2pt solid #000"></td></tr>',
            '<tr>' + ''.join(
                '<th style="border-bottom:0.5pt solid #000;padding:2px 7px;'
                'text-align:%s;font-weight:normal;font-style:%s">%s</th>'
                % ('left' if i == 0 else 'right',
                   'italic' if h in ('D', 'P', 'N', 'Q') else 'normal',
                   'RAP &Phi;' if h == 'RAP' else h)
                for i, (_k, h) in enumerate(_PUB)) + '</tr>']
    for r in rows:
        html.append('<tr>' + ''.join(
            '<td style="padding:2px 7px;text-align:%s">%s</td>'
            % ('left' if i == 0 else 'right', v)
            for i, v in enumerate(r)) + '</tr>')
    html += ['<tr><td colspan="%d" style="border-bottom:1.2pt solid #000">'
             '</td></tr>' % len(_PUB), '</table>']
    io.open(os.path.join(outdir, 'table_publication.html'), 'w',
            encoding='utf-8', newline='\n').write('\n'.join(html) + '\n')

    placed = sum(1 for r in rows if r[col['longitude']])
    md = ['# %s' % cap, '',
          '| Site | Long. | Lat. | Stage | N | σ1 D | σ1 P | σ2 D | σ2 P '
          '| σ3 D | σ3 P | RAP Φ | ANG | RUP | Q |',
          '|---|--:|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:-:|']
    for r in rows:
        md.append('| ' + ' | '.join(r) + ' |')
    md += ['', '%d determination(s)%s, %d with coordinates. Longitude and '
                'latitude are decimal degrees, WGS84. D is trend and P is '
                'plunge, both in degrees. RAP Φ is the shape ratio; ANG and '
                'RUP are the mean fit measures.'
           % (len(rows), ', %d phase(s)' % n_stage if n_stage else '',
              placed)]
    io.open(os.path.join(outdir, 'table_publication.md'), 'w',
            encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    return len(rows)


def write_all(recs, outdir, bin_deg=10.0):
    os.makedirs(outdir, exist_ok=True)
    write_table(recs, outdir)
    faults = write_faults(recs, outdir)
    npub = write_publication_table(recs, outdir)
    mapped, missing = write_map(recs, outdir)
    drawn, steep = write_stress_axes(recs, outdir)
    figs = write_roses(recs, outdir, bin_deg)
    print('\n%d runs -> %s' % (len(recs), outdir))
    print('  survey.csv / survey.md          one row per run')
    print('  table_publication.tex / .html / .md   %d row(s), journal layout'
          % npub)
    print('  faults.csv                     %d fault data across all runs'
          % len(faults))
    print('  map_points.csv / map_points.geojson   %d with coordinates, '
          '%d without' % (len(mapped), len(missing)))
    print('  stress_axes.geojson            %d axis line(s) a GIS can draw '
          'as they are%s' % (drawn, '' if not steep
                             else ', %d too steep to draw' % len(steep)))
    print('  %d rose figure(s) + roses.md' % len(figs))
    unassigned = [r for r in recs if not r.get('stage')]
    if unassigned:
        print('  %d run(s) have no phase assigned; they are grouped under '
              '"(unassigned)"' % len(unassigned))
    return dict(mapped=mapped, missing=missing, figures=figs)
