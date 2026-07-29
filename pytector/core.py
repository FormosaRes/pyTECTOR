# -*- coding: utf-8 -*-
"""pyTECTOR core: geometry, the Angelier criterion, and the quality estimators.

Every formula carries its source. Primary reference:

  Angelier, J. (1990) Inversion of field data in fault tectonics to obtain the
  regional stress - III. A new rapid direct inversion method by analytical
  means. Geophys. J. Int. 103, 363-376.

Cross-checked against:

  Angelier, J. (1984) Tectonic analysis of fault slip data sets.
  J. Geophys. Res. 89(B7), 5835-5848.
  Angelier, J. (1994) Fault slip analysis and palaeostress reconstruction.
  In: Hancock (ed.) Continental Deformation, ch.4.

Coordinate frame throughout: x = East, y = North, z = Up (right handed).
Compression positive, so sigma1 is the largest eigenvalue.
"""
import numpy as np

# Largest possible shear stress for the normalised (A16) reduced stress tensor.
# INFO1 files print this as "LAMBDA= 0.87".
LAMBDA = np.sqrt(3.0) / 2.0


# --------------------------------------------------------------- geometry ---
def normal_from_dipaz(dipaz_deg, dip_deg):
    """Upward unit normal of a plane, from dip azimuth and dip.

    Derivation:
        strike  = (-cos A, sin A, 0)
        downdip = ( sin A cos d, cos A cos d, -sin d)
        strike x downdip = (-sin A sin d, -cos A sin d, -cos d)   [downward]

    so the upward normal is the negative of that. Sanity check: a plane dipping
    east (A = 90) has an upward normal tilted EAST, like the surface z = -x
    whose normal is (1, 0, 1)/sqrt(2).
    """
    a = np.radians(np.asarray(dipaz_deg, float))
    d = np.radians(np.asarray(dip_deg, float))
    return np.stack([np.sin(d) * np.sin(a),
                     np.sin(d) * np.cos(a),
                     np.cos(d) * np.ones_like(a)], axis=-1)


def strike_and_downdip(dipaz_deg, dip_deg):
    a = np.radians(np.asarray(dipaz_deg, float))
    d = np.radians(np.asarray(dip_deg, float))
    strike = np.stack([np.sin(a - np.pi / 2), np.cos(a - np.pi / 2),
                       np.zeros_like(a)], axis=-1)
    downdip = np.stack([np.sin(a) * np.cos(d), np.cos(a) * np.cos(d),
                        -np.sin(d)], axis=-1)
    return strike, downdip


def slip_from_rake(dipaz_deg, dip_deg, rake_deg):
    """Unit slip vector from a rake measured in the plane, anticlockwise from
    the strike end at (dip azimuth - 90).

    NOTE for TENSOR files: the rake stored in columns [7:10] must be used as
    rake + 180 to get the movement direction. See tensorfile.read_site.
    """
    strike, downdip = strike_and_downdip(dipaz_deg, dip_deg)
    r = np.radians(np.asarray(rake_deg, float))[..., None]
    s = np.cos(r) * strike + np.sin(r) * downdip
    return s / np.linalg.norm(s, axis=-1, keepdims=True)


def trend_plunge(v):
    """Trend and plunge in degrees, forced to the lower hemisphere."""
    v = np.asarray(v, float)
    if v[2] > 0:
        v = -v
    return (np.degrees(np.arctan2(v[0], v[1])) % 360.0,
            np.degrees(np.arcsin(np.clip(-v[2], -1.0, 1.0))))


def vec_from_trend_plunge(trend, plunge):
    t, p = np.radians(trend), np.radians(plunge)
    return np.array([np.sin(t) * np.cos(p), np.cos(t) * np.cos(p), -np.sin(p)])


# ----------------------------------------------------------------- tensor ---
def tensor_A16(psi, R=np.eye(3)):
    """Normalised reduced stress tensor, Angelier (1990) eq (A16).

    Eigenvalues are cos(psi), cos(psi + 2pi/3), cos(psi + 4pi/3): they sum to
    zero (deviatoric) and their squares sum to exactly 3/2, for any psi. This
    is the normalisation TENSOR uses; MOHR1 of site L12 records eigenvalues
    0.912 / -0.100 / -0.812 whose squares sum to 1.5010.

    It is NOT the same as fixing sigma1 - sigma3; the two agree only at
    Phi = 0.5. The scale matters because the upsilon criterion is not scale
    invariant.
    """
    d = np.cos(psi + np.array([0.0, 2 * np.pi / 3, 4 * np.pi / 3]))
    return R @ np.diag(d) @ R.T


def describe(T):
    """Principal axes (trend, plunge), shape ratio Phi, and max shear."""
    w, V = np.linalg.eigh(T)
    o = np.argsort(w)[::-1]                 # compression positive
    w, V = w[o], V[:, o]
    axes = [trend_plunge(V[:, i]) for i in range(3)]
    phi = float((w[1] - w[2]) / (w[0] - w[2]))
    return dict(sigma1=axes[0], sigma2=axes[1], sigma3=axes[2],
                phi=phi, taumax=float((w[0] - w[2]) / 2),
                eigenvalues=w, eigenvectors=V)


# -------------------------------------------------------------- criterion ---
def resolve(T, n, s):
    """Stress vector, normal stress, shear traction and s.sigma per datum.

    eq (3)    sigma = T n
    eq (4-5)  tau   = sigma - (n.sigma) n
    """
    sig = n @ T.T
    sn = np.einsum('ki,ki->k', n, sig)
    tau = sig - sn[:, None] * n
    return sig, sn, tau, np.einsum('ki,ki->k', s, sig)


def upsilon_sq(T, n, s, lam=LAMBDA):
    """|upsilon|^2 per datum, Angelier (1990) eq (A1):

        upsilon^2 = lambda^2 + |tau|^2 - 2 lambda (s . sigma)

    s.sigma is used rather than s.tau; they are equal because s is
    perpendicular to n.
    """
    _, _, tau, s_dot_sig = resolve(T, n, s)
    tau2 = np.einsum('ki,ki->k', tau, tau)
    return lam ** 2 + tau2 - 2.0 * lam * s_dot_sig, tau


def S4(T, n, s, lam=LAMBDA):
    """The objective, Angelier (1990) eq (13): S4 = sum upsilon^2."""
    return float(upsilon_sq(T, n, s, lam)[0].sum())


# ------------------------------------------------------- quality estimators --
def estimators(T, n, s):
    """Reproduce every column TENSOR writes to INFO1 and MOHR1.

    SIGMA |sigma|              SIGMN sigma_n            TAU |tau|
    TAUST s.tau                RMU   |tau| / |sigma_n|  OBL arctan(|sigma_n|/|tau|)
    RUP   100 |upsilon| / (sqrt(3)/2)   (0 to 200 per cent, Angelier 1990 sec.5)
    ANG   angle(s, tau) in degrees      (0 to 180, Angelier 1994 p.81)
    """
    sig, sn, tau, taust = resolve(T, n, s)
    tn = np.linalg.norm(tau, axis=1)
    v2 = LAMBDA ** 2 + np.einsum('ki,ki->k', tau, tau) - 2 * LAMBDA * taust
    rup = 100.0 * np.sqrt(np.maximum(v2, 0.0)) / LAMBDA
    ang = np.degrees(np.arccos(np.clip(taust / np.maximum(tn, 1e-300), -1, 1)))
    with np.errstate(divide='ignore', invalid='ignore'):
        rmu = 100.0 * tn / np.abs(sn)
        obl = np.degrees(np.arctan2(np.abs(sn), tn))
    return dict(SIGMA=np.linalg.norm(sig, axis=1), SIGMN=sn, TAU=tn,
                TAUST=taust, RMU=rmu, OBL=obl, RUP=rup, ANG=ang)


def summary(T, n, s):
    """Axes, Phi and the aggregate numbers that appear on the 03INVD line."""
    out = describe(T)
    est = estimators(T, n, s)
    out.update(est)
    out['RUP_mean'] = float(est['RUP'].mean())
    out['ANG_mean'] = float(est['ANG'].mean())
    out['n_rup1'] = int((est['RUP'] > 75).sum())
    out['n_rup2'] = int(((est['RUP'] <= 75) & (est['RUP'] > 50)).sum())
    out['n_ang1'] = int((est['ANG'] >= 45).sum())
    out['n_ang2'] = int(((est['ANG'] < 45) & (est['ANG'] > 22.5)).sum())
    out['S4'] = S4(T, n, s)
    return out
