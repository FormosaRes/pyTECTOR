# -*- coding: utf-8 -*-
"""Mode A: faithful reconstruction of Angelier's TENSOR 5.45 (jan91).

Reverse engineered on 2026-07-28 from the outputs of two runs of the original
program (sites L12 and 0406-7 of the Chingshuichi data set), cross-checked
against Angelier (1990). Verification is recorded in tests/test_replication.py.

The essential point, and the reason a first attempt failed: TENSOR does NOT
work with a normalised stress tensor. Angelier's equation (14), legible in the
scan as (A2), is

    T = [[cos psi,  alpha,          gamma        ],
         [alpha,    cos(psi+2pi/3), beta         ],
         [gamma,    beta,           cos(psi+4pi/3)]]

Trace is zero for any psi, but the sum of squared entries is
3/2 + 2(alpha^2 + beta^2 + gamma^2), so the tensor's maximum shear moves as the
solution moves. That is precisely why the parameter lambda has to be adjusted
over successive passes (Angelier 1990, sec.4, and his Appendix IV), and why the
LAMBDA that INFO1 prints is smaller than sqrt(3)/2.

upsilon^2 is QUADRATIC in (alpha, beta, gamma) at fixed psi, so the inner
minimisation is an exact 3x3 linear solve. Angelier's Appendix I and II do the
same thing by hand; the polynomials a, b, ..., w of (A6) and (A8) are just that
expansion written out. They are regenerated numerically here rather than
transcribed, because the appendix is unreadable in the available scan.

Pipeline, as printed by INFO1:

    SOLUTION INVDIR (NO k)  LAMBDA= ...     <- k is the PASS NUMBER
    SOLUTION PSIDIR         AXES OK !       <- axes frozen, psi re-solved
"""
import numpy as np

from .core import LAMBDA, tensor_A16, describe

# the three symmetric off-diagonal unit matrices multiplying alpha, beta, gamma
_P = np.array([[0., 1., 0.], [1., 0., 0.], [0., 0., 0.]])
_Q = np.array([[0., 0., 0.], [0., 0., 1.], [0., 1., 0.]])
_R = np.array([[0., 0., 1.], [0., 0., 0.], [1., 0., 0.]])


def _C(psi):
    return np.diag(np.cos(psi + np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3])))


def _solve_at_psi(n, s, psi, lam):
    """Exact minimiser of S4 over (alpha, beta, gamma) at fixed psi."""
    C = _C(psi)
    c = n @ C.T                                       # constant part of sigma
    M = np.stack([n @ _P.T, n @ _Q.T, n @ _R.T], axis=2)      # (K,3,3)

    a = np.einsum('ki,ki->k', n, c)
    b = np.einsum('ki,kij->kj', n, M)
    e = np.einsum('ki,ki->k', s, c)
    f = np.einsum('ki,kij->kj', s, M)

    A = (np.einsum('kij,kil->kjl', M, M)
         - np.einsum('ki,kj->kij', b, b)).sum(0)
    g = (np.einsum('kij,ki->kj', M, c) - a[:, None] * b - lam * f).sum(0)
    const = float(np.sum(lam ** 2 + np.einsum('ki,ki->k', c, c)
                         - a ** 2 - 2 * lam * e))

    p = -np.linalg.solve(A, g)
    return C + p[0] * _P + p[1] * _Q + p[2] * _R, const + float(g @ p), p


def invdir_pass(n, s, lam, n_psi=4000):
    """One INVDIR determination at a given lambda.

    psi is scanned over a FULL turn. Restricting it to [0, pi/3] gives wrong
    answers; the minimum frequently sits near psi = 330-355 deg.
    """
    psis = np.linspace(0.0, 2 * np.pi, n_psi, endpoint=False)
    vals = np.fromiter((_solve_at_psi(n, s, p, lam)[1] for p in psis),
                       float, n_psi)
    i = int(np.argmin(vals))
    step = 2 * np.pi / n_psi
    lo, hi = psis[i] - step, psis[i] + step
    for _ in range(120):                                   # ternary search
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if _solve_at_psi(n, s, m1, lam)[1] < _solve_at_psi(n, s, m2, lam)[1]:
            hi = m2
        else:
            lo = m1
    psi = 0.5 * (lo + hi)
    T, s4, p = _solve_at_psi(n, s, psi, lam)
    return T, s4, psi, p


def psidir(n, s, R, n_psi=8000):
    """PSIDIR, Angelier (1990) Appendix III.

    Axes frozen at the INVDIR result, tensor switched to the NORMALISED A16
    form, lambda = sqrt(3)/2, and psi re-minimised over a full turn. Angelier
    reduces the stationary condition to a quartic in tan(psi/2); scanning the
    whole circle finds the same extremum without needing his coefficients.

    Its stated purpose is to "definitely identify the actual stress axes",
    i.e. to repair artificial permutations of sigma1/sigma2/sigma3 that the
    unnormalised INVDIR pass can produce on poorly varied data sets.
    """
    def obj(psi):
        T = tensor_A16(psi, R)
        sig = n @ T.T
        sn = np.einsum('ki,ki->k', n, sig)
        tau = sig - sn[:, None] * n
        return float(np.sum(LAMBDA ** 2 + np.einsum('ki,ki->k', tau, tau)
                            - 2 * LAMBDA * np.einsum('ki,ki->k', s, sig)))

    psis = np.linspace(0.0, 2 * np.pi, n_psi, endpoint=False)
    vals = np.fromiter((obj(p) for p in psis), float, n_psi)
    i = int(np.argmin(vals))
    step = 2 * np.pi / n_psi
    lo, hi = psis[i] - step, psis[i] + step
    for _ in range(120):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if obj(m1) < obj(m2):
            hi = m2
        else:
            lo = m1
    psi = 0.5 * (lo + hi)
    return tensor_A16(psi, R), obj(psi), psi


def printed_lambda(n, s, lam, n_psi=4000):
    """One pass, plus the LAMBDA that INFO1 would print for it.

    INFO1 does not print the lambda that was fed to the solver: it prints that
    lambda rescaled onto the normalised tensor. So the printed value depends on
    the solution, which depends on the lambda. Hence the search below.
    """
    T, s4, psi, p = invdir_pass(n, s, lam, n_psi=n_psi)
    d = describe(T)
    scale = np.sqrt(1.5 / float((d['eigenvalues'] ** 2).sum()))
    return lam * scale, T, d, s4


def lambda_for_printed(n, s, target, prefer=None, n_psi=1200,
                       lo=0.25, hi=6.0, steps=48):
    """Find the solver lambda whose printed value is the one an archive INFO1
    records, so a specific historical run can be reproduced rather than
    re-derived.

    The mapping from solver lambda to printed lambda is NOT monotonic: on site
    L12 it rises to about 0.87 near lambda 2.5 and falls away again, so plain
    bisection on the end points finds no bracket and gives up even though the
    target is reachable. Scan first, collect every crossing, then take the one
    nearest `prefer`, which is the lambda the iteration would have reached on
    its own. That keeps the answer on the branch the original program was on.
    """
    grid = np.linspace(lo, hi, steps)
    vals = np.array([printed_lambda(n, s, x, n_psi)[0] - target for x in grid])

    roots = []
    for i in range(len(grid) - 1):
        if vals[i] == 0.0:
            roots.append(grid[i])
        elif vals[i] * vals[i + 1] < 0:
            a, b, fa = grid[i], grid[i + 1], vals[i]
            for _ in range(40):
                m = 0.5 * (a + b)
                fm = printed_lambda(n, s, m, n_psi)[0] - target
                if fa * fm <= 0:
                    b = m
                else:
                    a, fa = m, fm
                if b - a < 1e-6:
                    break
            roots.append(0.5 * (a + b))
    if not roots:
        return None
    if prefer is None:
        return roots[0]
    return min(roots, key=lambda x: abs(x - prefer))


def run(n, s, n_pass=1, n_psi=4000, lam_printed=None):
    """Full TENSOR pipeline.

    n_pass reproduces the "(NO k)" that INFO1 prints. Observed in the archive:
    site 0406-7 used NO 1, site L12 used NO 2. When replicating an existing
    run, read the number out of that site's INFO1.

    lam_printed, when given, is the LAMBDA an archive INFO1 records. The solver
    lambda that produces it is solved for and used for the final pass. This
    matters where the surface is flat: re-deriving lambda from scratch can land
    a degree away with a slightly worse S4, whereas adopting the recorded value
    reproduces the historical run. Site L12 is the case in point.

    Returns a dict with the INVDIR tensor (which fixes the axes), the PSIDIR
    tensor (which fixes Phi), and the lambda trace.
    """
    lam = LAMBDA
    trace = []
    T = None
    for k in range(n_pass):
        last = (k == n_pass - 1)
        if last and lam_printed is not None:
            # prefer the branch the iteration was already on
            solved = lambda_for_printed(n, s, float(lam_printed), prefer=lam)
            if solved is not None:
                lam = solved
        T, s4, psi, p = invdir_pass(n, s, lam, n_psi=n_psi)
        d = describe(T)
        # INFO1 prints lambda rescaled onto the normalised tensor
        scale = np.sqrt(1.5 / float((d['eigenvalues'] ** 2).sum()))
        trace.append(dict(no=k + 1, lam_used=lam, lam_printed=lam * scale,
                          phi=d['phi'], taumax_raw=d['taumax'], S4=s4,
                          from_archive=bool(last and lam_printed is not None)))
        lam = d['taumax']

    d_inv = describe(T)
    R = d_inv['eigenvectors']
    T_psi, s4_psi, psi = psidir(n, s, R, n_psi=2 * n_psi)
    return dict(T_invdir=T, T=T_psi, psi=psi, S4=s4_psi,
                invdir=d_inv, lambda_trace=trace)
