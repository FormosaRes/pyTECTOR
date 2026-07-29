# -*- coding: utf-8 -*-
"""Given an original and its back-tilted copy, SOLVE for the rotation that
maps one to the other (Kabsch on the fault normals, record order assumed
preserved), then read off its axis and angle. Comparing that with the folder
name tells us the convention instead of guessing it."""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
from pytector import tensorfile

from pytector.archive import ROOT
PAT = re.compile(r'\(backtilted\s*([0-9]{1,3})\s*([+-]?\d+)\s*\)', re.I)


def kabsch(A, B):
    """Rotation R with R a_i ~ b_i, allowing the sign flip of each normal."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    best = None
    # a fault normal is defined up to sign, so try aligning each one either way
    for _ in range(1):
        signs = np.ones(len(A))
        for _it in range(20):
            H = (A * signs[:, None]).T @ B
            U, _S, Vt = np.linalg.svd(H)
            d = np.sign(np.linalg.det(Vt.T @ U.T))
            R = Vt.T @ np.diag([1, 1, d]) @ U.T
            pred = (A @ R.T)
            new = np.sign(np.einsum('ki,ki->k', pred, B))
            new[new == 0] = 1
            if np.array_equal(new, signs):
                break
            signs = signs * new
        err = np.degrees(np.arccos(np.clip(
            np.abs(np.einsum('ki,ki->k', A @ R.T, B)), -1, 1)))
        if best is None or err.mean() < best[0]:
            best = (err.mean(), R, err)
    return best[1], best[0], best[2]


def axis_angle(R):
    ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
    w, V = np.linalg.eig(R)
    k = None
    for i in range(3):
        if abs(w[i].real - 1) < 1e-6 and abs(w[i].imag) < 1e-6:
            k = V[:, i].real
    if k is None:
        return None, None, ang
    k = k / np.linalg.norm(k)
    if k[2] > 0:
        k, ang = -k, -ang
    trend = np.degrees(np.arctan2(k[0], k[1])) % 360.0
    plunge = np.degrees(np.arcsin(np.clip(-k[2], -1, 1)))
    return trend, plunge, ang


files = tensorfile.discover(ROOT)
targets = [p for p in files if PAT.search(p)]
plain = [p for p in files if not PAT.search(p) and 'backtilt' not in p.lower()]

for p in targets:
    m = PAT.search(p)
    trend_s, ang_s = float(m.group(1)), float(m.group(2))
    try:
        tgt = tensorfile.read_site(p)
    except Exception:
        continue
    stem = os.path.basename(os.path.dirname(p)).split('(')[0].strip().lower()

    cands = []
    for q in plain:
        try:
            src = tensorfile.read_site(q)
        except Exception:
            continue
        if len(src) != len(tgt):
            continue
        s2 = os.path.basename(os.path.dirname(q)).lower()
        score = 2 if stem.rstrip('-c') in s2 or s2 in stem else 0
        cands.append((score, q, src))
    if not cands:
        continue
    cands.sort(key=lambda t: -t[0])

    print('=' * 76)
    print(os.path.relpath(p, ROOT))
    print('   folder says: trend %03d  angle %+d   (%d faults)'
          % (trend_s, ang_s, len(tgt)))
    shown = 0
    for score, q, src in cands:
        R, err, per = kabsch(src.n, tgt.n)
        t, pl, a = axis_angle(R)
        if t is None:
            continue
        tag = ''
        if err < 2.0:
            tag = '   <== FITS'
        print('   vs %-40s  err %6.2f deg  axis %05.1f/%04.1f  angle %+6.1f%s'
              % (os.path.relpath(q, ROOT)[:40], err,
                 t, pl, a, tag))
        shown += 1
        if shown >= 4 and err > 2.0:
            break
