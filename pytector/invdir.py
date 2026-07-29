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


def _refine(scan, lo, hi, rounds=7, pts=33):
    """Locate the minimum inside a bracket, calling `scan` on whole grids.

    Replaces a 120-step ternary search that evaluated one psi at a time. Each
    round shrinks the bracket by 16, so seven rounds take a 4000-point scan
    step down to about 1e-14 radians, which is the floating-point floor for an
    angle of this size. The point is that all 33 probes go out in one call.
    """
    for _ in range(rounds):
        grid = np.linspace(lo, hi, pts)
        j = int(np.argmin(scan(grid)))
        lo, hi = grid[max(j - 1, 0)], grid[min(j + 1, pts - 1)]
    return 0.5 * (lo + hi)


def _scan_invdir(n, s, psis, lam):
    """S4 at every psi at once. Same numbers as calling _solve_at_psi in a
    loop, which is what this replaced.

    Worth the algebra: the scan is 4000 points and it re-runs for every trial
    lambda, so the archive-LAMBDA search alone was calling the scalar routine
    about a hundred thousand times and taking the best part of ten seconds.
    Almost none of that work depends on psi.

    With T = C(psi) + alpha P + beta Q + gamma R, only the diagonal C carries
    psi and it enters linearly. So M, b, f and the 3x3 normal matrix A are
    constants of the data set, built once; each psi then costs one right-hand
    side solved against that SAME matrix.
    """
    psis = np.asarray(psis, float)
    cd = np.cos(psis[:, None] + np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3]))

    M = np.stack([n @ _P.T, n @ _Q.T, n @ _R.T], axis=2)      # (K,3,3)
    b = np.einsum('ki,kij->kj', n, M)                          # (K,3)
    f = np.einsum('ki,kij->kj', s, M)                          # (K,3)
    A = (np.einsum('kij,kil->kjl', M, M)
         - np.einsum('ki,kj->kij', b, b)).sum(0)               # (3,3)
    W = np.einsum('kij,ki->ij', M, n)                          # (3,3)

    n2 = n ** 2
    a = n2 @ cd.T                                              # (K,P)
    g = cd @ W - a.T @ b - lam * f.sum(0)                      # (P,3)
    const = (len(n) * lam ** 2
             + (cd ** 2) @ n2.sum(0)
             - (a ** 2).sum(0)
             - 2 * lam * (cd @ (s * n).sum(0)))
    p = -np.linalg.solve(A, g.T).T                             # (P,3)
    return const + np.einsum('pj,pj->p', g, p)


def invdir_pass(n, s, lam, n_psi=4000):
    """One INVDIR determination at a given lambda.

    psi is scanned over a FULL turn. Restricting it to [0, pi/3] gives wrong
    answers; the minimum frequently sits near psi = 330-355 deg.
    """
    psis = np.linspace(0.0, 2 * np.pi, n_psi, endpoint=False)
    vals = _scan_invdir(n, s, psis, lam)
    i = int(np.argmin(vals))
    step = 2 * np.pi / n_psi
    psi = _refine(lambda g: _scan_invdir(n, s, g, lam),
                  psis[i] - step, psis[i] + step)
    T, s4, p = _solve_at_psi(n, s, psi, lam)
    return T, s4, psi, p


#: Order of the three A16 eigenvalues as a function of psi. The tensor built
#: on the frozen axes is
#:
#:     T = R diag(cos psi, cos(psi+2pi/3), cos(psi+4pi/3)) R'
#:
#: so column i of R -- which is INVDIR's sigma(i+1) -- is handed the eigenvalue
#: cos(psi + 2 i pi/3). Those three cosines are in DESCENDING order only while
#: psi lies in the last 60 degrees of the turn. Each of the six possible
#: orderings owns one 60 degree sector, so wherever PSIDIR's minimum lands
#: outside that one sector the labels sigma1/sigma2/sigma3 move to different
#: frozen directions. That, and nothing else, is what makes TENSOR print
#: PERMUTATION instead of AXES OK ! on the PSIDIR line.
#:
#: Verified against the archive: on the 56 runs pyTECTOR reproduces to better
#: than 3 degrees on sigma1, this rule predicts the recorded flag 56 times out
#: of 56. The six runs where it does not agree are all runs whose INVDIR
#: solution we do not reproduce in the first place (sigma1 off by 8 to 80
#: degrees), so they test the reproduction, not the rule.
AXES_OK_SECTOR = (300.0, 360.0)


def axis_order(psi):
    """Which frozen axis each of sigma1, sigma2, sigma3 ends up on.

    Returns (order, permuted): order[k] is the column of R that becomes
    sigma(k+1), and permuted is False only for the identity (0, 1, 2).
    """
    d = np.cos(float(psi) + np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3]))
    order = tuple(int(i) for i in np.argsort(d)[::-1])
    return order, order != (0, 1, 2)


def psidir(n, s, R, n_psi=8000):
    """PSIDIR, Angelier (1990) Appendix III.

    Axes frozen at the INVDIR result, tensor switched to the NORMALISED A16
    form, lambda = sqrt(3)/2, and psi re-minimised over a full turn. Angelier
    reduces the stationary condition to a quartic in tan(psi/2); scanning the
    whole circle finds the same extremum without needing his coefficients.

    Its stated purpose is to "definitely identify the actual stress axes",
    i.e. to repair artificial permutations of sigma1/sigma2/sigma3 that the
    unnormalised INVDIR pass can produce on poorly varied data sets. It is not
    a second opinion that TENSOR adopts when it looks better: the final Phi and
    the final axis LABELS always come from here. See AXES_OK_SECTOR for when
    that relabelling actually moves anything.
    """
    # In the eigenframe the tensor is diagonal, so with u = R'n and v = R's
    #   n.sigma = sum u_i^2 d_i,  |sigma|^2 = sum u_i^2 d_i^2,  s.sigma = sum
    #   v_i u_i d_i,  and |tau|^2 = |sigma|^2 - (n.sigma)^2.
    # Every psi is then three dot products against d = cos(psi + 0, 2pi/3,
    # 4pi/3), so the whole 8000-point scan is a couple of matrix products.
    U = (n @ R) ** 2
    V = (s @ R) * (n @ R)
    Us, Vs = U.sum(0), V.sum(0)
    base = len(n) * LAMBDA ** 2

    def scan(psis):
        psis = np.asarray(psis, float)
        d = np.cos(psis[:, None] + np.array([0.0, 2 * np.pi / 3,
                                             4 * np.pi / 3]))
        return (base + (d ** 2) @ Us - ((U @ d.T) ** 2).sum(0)
                - 2 * LAMBDA * (d @ Vs))

    psis = np.linspace(0.0, 2 * np.pi, n_psi, endpoint=False)
    i = int(np.argmin(scan(psis)))
    step = 2 * np.pi / n_psi
    psi = _refine(scan, psis[i] - step, psis[i] + step)
    return tensor_A16(psi, R), float(scan([psi])[0]), psi


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
    order, permuted = axis_order(psi)
    return dict(T_invdir=T, T=T_psi, psi=psi, S4=s4_psi,
                invdir=d_inv, lambda_trace=trace,
                psidir_order=order, permutation=permuted,
                psidir_flag='PERMUTATION' if permuted else 'AXES OK !')
