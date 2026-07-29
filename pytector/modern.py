# -*- coding: utf-8 -*-
"""Mode B: the same criterion, minimised properly.

Mode A (invdir.py) reproduces what TENSOR 5.45 actually computed, including a
lambda that stops before it converges. That is faithful, but it is not the
minimum of Angelier's own stated objective: on both archive sites checked,
Mode B reaches a lower S4 than the original program did.

    site      TENSOR S4     Mode B S4
    L12         0.3018        0.2360
    0406-7      7.6198        7.3201

Mode B parametrises the tensor by its eigen-decomposition in the normalised
A16 form, so lambda is the constant sqrt(3)/2 by construction and no adjustment
loop is needed. The search is global (many random starts) rather than a single
analytical extremum, which also avoids the artificial axis permutations that
PSIDIR exists to repair.

Use Mode A to reproduce published numbers. Use Mode B when the question is what
the data actually support. Report both when the difference matters.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation

from .core import LAMBDA, tensor_A16, describe, S4


def _params_to_T(x):
    return tensor_A16(x[3], Rotation.from_rotvec(x[:3]).as_matrix())


def _obj(x, n, s):
    return S4(_params_to_T(x), n, s, LAMBDA)


def run(n, s, n_starts=400, seed=0, refine=2):
    """Global minimisation of S4 = sum |lambda s - tau|^2 with lambda fixed."""
    rng = np.random.default_rng(seed)
    rots = Rotation.random(n_starts, random_state=rng).as_rotvec()
    psis = np.linspace(0.0, 2 * np.pi, 12, endpoint=False)

    # Score all n_starts x 12 candidates at once rather than one at a time.
    # In each candidate's own eigenframe the tensor is diagonal, so with
    # u = R'n and v = R's the objective is three dot products against
    # d = cos(psi + 0, 2pi/3, 4pi/3), and |tau|^2 = |sigma|^2 - (n.sigma)^2.
    Rm = Rotation.from_rotvec(rots).as_matrix()               # (M,3,3)
    u = np.einsum('ki,mij->mkj', n, Rm)
    v = np.einsum('ki,mij->mkj', s, Rm)
    U, V = u ** 2, v * u
    d = np.cos(psis[:, None] + np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3]))
    grid = (len(n) * LAMBDA ** 2
            + U.sum(1) @ (d ** 2).T
            - (np.einsum('mki,pi->mkp', U, d) ** 2).sum(1)
            - 2 * LAMBDA * (V.sum(1) @ d.T))                  # (M,P)

    i, j = np.unravel_index(int(np.argmin(grid)), grid.shape)
    x = np.array([rots[i][0], rots[i][1], rots[i][2], psis[j]], float)
    for tol in [1e-11, 1e-13][:refine]:
        x = minimize(_obj, x, args=(n, s), method='Nelder-Mead',
                     options={'xatol': tol, 'fatol': tol * 1e-2,
                              'maxiter': 60000, 'maxfev': 60000}).x

    T = _params_to_T(x)
    return dict(T=T, S4=_obj(x, n, s), params=x, **describe(T))


def bootstrap(n, s, n_boot=200, seed=0, n_starts=60):
    """Resample the fault set with replacement to get confidence clouds on the
    principal axes. Cheap and assumption-light; the usual caveat about
    bootstrap on small, geometrically clustered data sets applies."""
    rng = np.random.default_rng(seed)
    K = len(n)
    out = []
    for b in range(n_boot):
        idx = rng.integers(0, K, K)
        try:
            r = run(n[idx], s[idx], n_starts=n_starts, seed=b, refine=1)
        except Exception:
            continue
        out.append((r['sigma1'], r['sigma2'], r['sigma3'], r['phi']))
    return out
