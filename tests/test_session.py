# -*- coding: utf-8 -*-
"""Sessions round-trip, and reopening one does not change any answer.

The point of a session file is that work does not have to be done twice, which
is only worth anything if what comes back is the same. So this saves a real
site with real solutions, reads it back, and checks the numbers against the
originals rather than against themselves.

Run:  python tests/test_session.py
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pytector import core, entry, invdir, modern, session, tensorfile

from pytector.archive import ROOT

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


def axis_gap(a, b):
    u = core.vec_from_trend_plunge(*a)
    v = core.vec_from_trend_plunge(*b)
    return float(np.degrees(np.arccos(min(abs(float(u @ v)), 1.0))))


print('1. a session with no results still round-trips')
recs = [entry.parse_record(*t) for t in
        (('CS', '122', '87W', '124'), ('PN', '135', '85W', '80S'),
         ('CN', '145', '62W', '50N'), ('SN', '174', '74E', '62N'),
         ('CN', '151', '69W', '72N'), ('PN', '3', '70E', '76N'))]
state = dict(site_name='TEST', site_code='01', declination=2.0, n_pass=2,
             use_invdir=True, use_s4min=False, records=recs,
             planes=[dict(kind='plane', a=212, b=87, dipaz=122, dip=87,
                          ref=True)],
             rotation=[20.0, 0.0, -30.0], rotation_mode=1, results={})
back = session.loads(session.dumps(state))
ok(len(back['records']) == len(recs), 'every record comes back')
ok(all(a['dipaz'] == b['dipaz'] and a['dip'] == b['dip']
       and abs(a['rake'] - b['rake']) < 1e-9
       for a, b in zip(recs, back['records'])),
   'geometry is unchanged to the last digit')
ok(all(a.get('confidence') == b.get('confidence')
       and a.get('sense') == b.get('sense')
       for a, b in zip(recs, back['records'])),
   'the confidence and movement letters survive')
ok(back['planes'][0]['ref'] is True and back['planes'][0]['dip'] == 87,
   'the reference surface survives, still marked as the reference')
ok(back['rotation'] == [20.0, 0.0, -30.0] and back['rotation_mode'] == 1,
   'the back-tilt in force survives')
ok(back['n_pass'] == 2 and back['use_s4min'] is False,
   'settings survive')

print('\n2. a session with solutions gives the same answers back')
site = os.path.join(ROOT, '0406-7', '0406-04')
if os.path.exists(site):
    st = tensorfile.read_site(site)
    n, s = st.n, st.s
    ra = invdir.run(n, s, n_pass=1)
    rb = modern.run(n, s, n_starts=200)
    A = core.summary(ra['T'], n, s)
    A['T'], A['T_invdir'] = ra['T'], ra['T_invdir']
    A['lambda_trace'] = ra['lambda_trace']
    B = core.summary(rb['T'], n, s)
    B['T'] = rb['T']

    state = dict(site_name=st.name, site_code=st.code, n_pass=1,
                 records=st.records, planes=[], results={'A': A, 'B': B})
    fd, path = tempfile.mkstemp(suffix=session.EXT)
    os.close(fd)
    try:
        session.save(path, state)
        got = session.load(path, n=n, s=s)
    finally:
        os.remove(path)

    for k, orig in (('A', A), ('B', B)):
        r = got['results'].get(k)
        ok(r is not None, 'result %s comes back' % k)
        if r is None:
            continue
        gaps = [axis_gap(orig[a], r[a])
                for a in ('sigma1', 'sigma2', 'sigma3')]
        ok(max(gaps) < 1e-6,
           '%s axes identical (max %.2e deg)' % (k, max(gaps)))
        ok(abs(orig['phi'] - r['phi']) < 1e-9,
           '%s Phi identical (%.6f)' % (k, r['phi']))
        ok(abs(orig['S4'] - r['S4']) < 1e-9, '%s S4 identical' % k)
        ok(abs(orig['ANG_mean'] - r['ANG_mean']) < 1e-9
           and abs(orig['RUP_mean'] - r['RUP_mean']) < 1e-9,
           '%s mean ANG and RUP identical' % k)
        ok(np.allclose(orig['ANG'], r['ANG'])
           and np.allclose(orig['RUP'], r['RUP']),
           '%s per-datum columns identical, though not stored' % k)
    ok('invdir_summary' in got['results']['A'],
       'the pre-PSIDIR block is rebuilt too, so INFO1 still prints both')
    ok(got['results']['A'].get('lambda_trace'),
       'the lambda trace survives')
else:
    print('   archive missing, skipped')

print('\n3. a file from a newer version is refused, not misread')
try:
    session.loads('{"format": 999, "records": []}')
    ok(False, 'should have refused')
except ValueError as exc:
    ok('newer pyTECTOR' in str(exc), 'refused with a message that says why')

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
