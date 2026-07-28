# -*- coding: utf-8 -*-
"""The back-tilt window's arithmetic, and the claim it prints on screen.

No Qt object is built here. Importing the module is safe; it is QApplication
that must never be constructed from an automated shell.

The claim under test: back-tilting the data and re-inverting is NOT the same
as rotating the answer, and whether it is depends on the method.

  S4MIN   exactly equivariant. S4 is rotation invariant, so its minimum turns
          with the data. Its Phi and S4 cannot change under back-tilting, and
          the whole content of a tilt test is where the axes end up.

  INVDIR  not equivariant. Angelier's equation (14) pins the tensor DIAGONAL
          to cos(psi), cos(psi + 2pi/3), cos(psi + 4pi/3) in the geographic
          frame, so the four-parameter family it searches is a different
          family once the data are turned.

That second point is a property of the method, not of this reconstruction: it
holds for the original program too. tests/test_rotate.py matches the archive's
back-tilt runs to their un-tilted parents; across those pairs the original
program's own axes disagree with the carried ones by a median of about 10
degrees on sigma1. So a change in the axes across a back-tilt cannot be read
as geology on INVDIR alone.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pytensor import backtilt, core, rotate, tensorfile, tilt
from pytensor.archive import ARCHIVE_ROOT as AROOT

fails = []


def ok(cond, msg):
    print('   %s  %s' % ('ok  ' if cond else 'FAIL', msg))
    if not cond:
        fails.append(msg)


ROTS = ((20.0, 0.0, -20.0), (145.0, 10.0, 35.0))
SITES = [('L12', 'L12'), ('0406-7', '0406-04')]

print('1. carried() is a pure rotation')
n = core.normal_from_dipaz(np.array([10., 100., 190., 280., 45., 135.]),
                           np.array([70., 55., 80., 40., 65., 75.]))
s = core.slip_from_rake(np.array([10., 100., 190., 280., 45., 135.]),
                        np.array([70., 55., 80., 40., 65., 75.]),
                        np.array([20., 160., 95., 40., 130., 70.]))
raw = backtilt._run('A', n, s, 1)
c = backtilt.carried(raw, 33.0, 12.0, 41.0)
V = np.column_stack([core.vec_from_trend_plunge(*c[k])
                     for k in ('sigma1', 'sigma2', 'sigma3')])
ok(float(np.abs(V.T @ V - np.eye(3)).max()) < 1e-9,
   'the carried axes stay orthonormal')
ok(abs(c['phi'] - raw['phi']) < 1e-12, 'a rotation cannot change Phi')
# arccos is ill conditioned next to zero: a dot product one part in 1e16 short
# of unity already reads as 1e-6 degrees. That is far below the 0.1 degree the
# window prints, so the tolerance here is set to what the number means.
ok(max(backtilt.separation(c, c)) < 1e-4, 'separation() is zero against self')

print('\n2. equivariance, per method')
if not os.path.exists(AROOT):
    print('   archive missing, using the synthetic set only')
    data = [('synthetic', n, s)]
else:
    data = []
    for folder, datafile in SITES:
        site = tensorfile.read_site(os.path.join(AROOT, folder, datafile))
        data.append((folder, site.n, site.s))

worst_b, worst_a = 0.0, 0.0
for name, dn, ds in data:
    for rot in ROTS:
        rn, rs = rotate.rotate_site(dn, ds, *rot)
        for key in ('B', 'A'):
            base = backtilt._run(key, dn, ds, 2)
            got = backtilt._run(key, rn, rs, 2)
            sep = max(backtilt.separation(backtilt.carried(base, *rot), got))
            if key == 'B':
                worst_b = max(worst_b, sep)
            else:
                worst_a = max(worst_a, sep)
ok(worst_b < 0.5, 'S4MIN is equivariant: worst axis moves %.3f deg' % worst_b)
ok(worst_a > 2.0,
   'INVDIR is NOT equivariant, and the window must keep saying so: worst axis '
   'moves %.1f deg' % worst_a)

print('\n3. the summary block can be built from any solution')
for name, dn, ds in data:
    r = backtilt._run('A', dn, ds, 1)
    m, regime, axis = tilt.andersonian(r)
    ok(0.0 <= m <= 90.0 and regime in ('normal', 'strike-slip', 'thrust')
       and axis in ('sigma1', 'sigma2', 'sigma3'),
       '%s: Andersonian misfit %.1f deg, %s' % (name, m, regime))

print('\n%d failures' % len(fails))
sys.exit(1 if fails else 0)
