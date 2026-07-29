# -*- coding: utf-8 -*-
"""Save and reopen a whole working state, so nothing has to be typed twice.

A site is entered fault by fault, reference surfaces are marked, a back-tilt is
found by trying angles, and only then is anything inverted. Losing all of that
on closing the window is the reason people keep a program open for days. This
writes it to one file.

What goes in, and what deliberately does not
--------------------------------------------
The RECORDS and the settings go in verbatim: they are what was typed and they
cannot be recomputed. So do the reference surfaces and the back-tilt in force.

Of the RESULTS, only the tensor is stored, 3x3 numbers per method, plus the
lambda trace that INFO1 prints. Everything else a result carries -- the axes,
Phi, the eight per-datum columns, the means, S4 -- is a function of that tensor
and the data, so it is recomputed on load rather than written out. That is a
few milliseconds and it removes a whole class of bug: a file whose stored Phi
disagrees with its stored tensor cannot exist.

The format is JSON, not pickle. It has to be readable in ten years by someone
who does not have this program, which is the same reason the TENSOR files
themselves are still usable.
"""
import io
import json
import os

import numpy as np

from . import core

#: Bumped only when an old file would otherwise be misread. Readers should
#: accept anything they understand and say so plainly when they do not.
FORMAT = 1

EXT = '.tec'

#: the fields of a record that were typed rather than derived
RECORD_KEYS = ('code', 'dipaz', 'dip', 'rake', 'confidence', 'sense', 'raw',
               'use', 'weight')


def _clean(rec):
    out = {}
    for k in RECORD_KEYS:
        if k in rec and rec[k] is not None:
            v = rec[k]
            out[k] = float(v) if isinstance(v, (np.floating,)) else (
                int(v) if isinstance(v, (np.integer,)) else v)
    return out


def dumps(state):
    """state -> JSON text. See save() for the keys."""
    out = dict(format=FORMAT, program='pyTECTOR')
    for k in ('site_name', 'site_code', 'declination', 'n_pass',
              'use_invdir', 'use_s4min', 'use_archive_lambda',
              'archive_lambda', 'rotation', 'rotation_mode'):
        if state.get(k) is not None:
            out[k] = state[k]
    out['records'] = [_clean(r) for r in state.get('records') or []]
    out['planes'] = [dict(kind=p.get('kind'), a=p.get('a'), b=p.get('b'),
                          dipaz=p.get('dipaz'), dip=p.get('dip'),
                          ref=bool(p.get('ref')))
                     for p in state.get('planes') or []]
    res = {}
    for key, r in (state.get('results') or {}).items():
        if r is None or 'T' not in r:
            continue
        item = dict(T=np.asarray(r['T'], float).tolist())
        if r.get('T_invdir') is not None:
            item['T_invdir'] = np.asarray(r['T_invdir'], float).tolist()
        if r.get('lambda_trace'):
            item['lambda_trace'] = [
                dict((k, (float(v) if isinstance(v, (int, float, np.floating))
                          else v)) for k, v in step.items())
                for step in r['lambda_trace']]
        res[key] = item
    out['results'] = res
    return json.dumps(out, indent=1, ensure_ascii=False)


def loads(text, n=None, s=None):
    """JSON text -> state. Results are rebuilt from the stored tensors.

    n and s are the data the results belong to; without them the tensors are
    returned but the derived columns are not, because there is nothing honest
    to compute them against.
    """
    d = json.loads(text)
    if d.get('format', 0) > FORMAT:
        raise ValueError(
            'this file was written by a newer pyTECTOR (format %s, this one '
            'reads %s)' % (d.get('format'), FORMAT))
    state = dict(d)
    state['records'] = [dict(r) for r in d.get('records') or []]
    state['planes'] = [dict(p) for p in d.get('planes') or []]

    out = {}
    for key, item in (d.get('results') or {}).items():
        T = np.asarray(item['T'], float)
        r = {'T': T}
        if n is not None and s is not None and len(n):
            r = core.summary(T, n, s)
            r['T'] = T
        if item.get('T_invdir') is not None:
            Ti = np.asarray(item['T_invdir'], float)
            r['T_invdir'] = Ti
            if n is not None and s is not None and len(n):
                r['invdir_summary'] = core.summary(Ti, n, s)
        if item.get('lambda_trace'):
            r['lambda_trace'] = item['lambda_trace']
        out[key] = r
    state['results'] = out
    return state


#: Sessions have a home rather than landing wherever the last dialog was, so
#: that a fresh clone has somewhere obvious to put them and they stay together.
#: The folder is in the repository (with a .gitkeep) so it exists on install;
#: its contents are field data and are git-ignored.
DIRNAME = 'Session'


def default_dir():
    """The Session folder beside the program, created if it is not there yet.

    Falls back to the home directory if that location cannot be written, which
    is what happens when the package is installed read-only into site-packages
    rather than run from a clone.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, DIRNAME)
    try:
        if not os.path.isdir(d):
            os.makedirs(d)
        return d
    except OSError:
        return os.path.expanduser('~')


def default_path(site):
    """Where a session for this site should be offered."""
    from .rotate import safe_name
    return os.path.join(default_dir(), safe_name(site) + EXT)


def save(path, state):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(dumps(state))


def load(path, n=None, s=None):
    with io.open(path, encoding='utf-8') as fh:
        return loads(fh.read(), n=n, s=s)
