# -*- coding: utf-8 -*-
"""Turn a tree of TENSOR runs into a table, map data and roses per phase.

    python make_survey.py [root] [outdir] [--stages FILE] [--coords FILE]
                          [--method auto|invdir|psidir|03] [--bin 10]

root defaults to PYTECTOR_ARCHIVE. The two side files are yours and optional:

  --stages FILE    CSV `run,stage`. Which run belongs to which deformation
                   phase is your judgement; nothing here guesses it. The key
                   may be the run id, the site name, or the folder name.
  --coords FILE    CSV `site,longitude,latitude`, same keying.

Outputs into outdir:

  survey.csv, survey.md              every run, grouped by phase
  map_points.csv, map_points.geojson the ones with coordinates; QGIS opens
                                     the GeoJSON directly
  rose_<phase>.png, roses.md         sigma1 and sigma3 roses per phase, with
                                     the readable panel marked

Nothing in the source folders is modified, and neither side file is written.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pytector import survey
from pytector.archive import ROOT


def parse_args(argv):
    pos, opt = [], dict(stages=None, coords=None, method='auto', bin=10.0)
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--stages', '--coords', '--method', '--bin'):
            if i + 1 >= len(argv):
                raise SystemExit('%s needs a value' % a)
            key = a[2:]
            opt[key] = float(argv[i + 1]) if key == 'bin' else argv[i + 1]
            i += 2
        elif a in ('-h', '--help'):
            print(__doc__)
            raise SystemExit(0)
        else:
            pos.append(a)
            i += 1
    return pos, opt


def main(argv):
    pos, opt = parse_args(argv)
    root = pos[0] if pos else ROOT
    outdir = pos[1] if len(pos) > 1 else 'survey_out'
    if not root:
        raise SystemExit(
            'give a root folder, or set PYTECTOR_ARCHIVE.\n'
            'It is not defaulted to a real path on purpose: it points at '
            'field data and this file is public.')
    if not os.path.isdir(root):
        raise SystemExit('not a folder: %s' % root)

    print('reading %s' % root)
    recs = survey.collect(root, method=opt['method'])
    if not recs:
        raise SystemExit('no readable TENSOR runs found under that folder')
    print('%d run(s), solution chosen by method=%s' % (len(recs), opt['method']))
    none = [r for r in recs if r.get('solution_from') == 'none']
    if none:
        print('  %d run(s) carry no recorded solution and have no axes: %s'
              % (len(none), ', '.join(r['run_id'] for r in none[:5])
                 + (' ...' if len(none) > 5 else '')))

    if opt['stages']:
        survey.attach_stages(recs, opt['stages'])
    if opt['coords']:
        survey.attach_coords(recs, opt['coords'])

    survey.write_all(recs, outdir, bin_deg=opt['bin'])


if __name__ == '__main__':
    main(sys.argv[1:])
