# pyTENSOR

A Python reconstruction of Jacques Angelier's **TENSOR** palaeostress inversion
program (TENSOR 5.45, jan91), written from the published method rather than by
disassembling the original 16-bit DOS binary.

Named in tribute to the original.

---

## Why

The original `Tensor.exe` is a 16-bit MS-DOS binary with no symbol table, so it
will not run on 64-bit Windows and cannot usefully be decompiled. The algorithm,
however, is fully documented:

- Angelier, J. (1990) *Inversion of field data in fault tectonics to obtain the
  regional stress — III. A new rapid direct inversion method by analytical
  means.* Geophys. J. Int. **103**, 363–376.
- Angelier, J. (1984) *Tectonic analysis of fault slip data sets.*
  J. Geophys. Res. **89**(B7), 5835–5848.
- Angelier, J. (1994) *Fault slip analysis and palaeostress reconstruction.*
  In: Hancock (ed.) *Continental Deformation*, ch. 4.

## The criterion

| | |
|---|---|
| stress vector | σ = **T**·n  (eq 3) |
| shear traction | τ = σ − (n·σ)n  (eq 4–5) |
| upsilon vector | λs = τ + υ  (eq 12) |
| **objective** | **υ² = λ² + \|τ\|² − 2λ(s·σ)**  (eq A1), minimise **S₄ = Συ²** (eq 13) |
| quality | RUP = 100·\|υ\|/(√3/2), 0–200 % ; ANG = angle(s, τ), 0–180° |

The reduced stress tensor is normalised so that the **sum of squared
eigenvalues is 3/2** (eq A16), not so that σ₁ − σ₃ is fixed. The two agree only
at Φ = 0.5, and the criterion is not scale invariant, so this matters.

## Two runs: INVDIR and S4MIN

Named after what they are, not by a letter that would imply one is the better
one. **Neither is "the true stress"**: the criterion itself is biased. Fed
perfect Bott data with no noise at all, INVD still misses the true tensor by
about 4 degrees, because upsilon trades slip-shear angle against shear
magnitude. The angle-only criterion F2 recovers it to 0.00 degrees on the same
data. So the gap between the two runs is not a gap between wrong and right.



**INVDIR — `pytensor.invdir`, code `INVD`, as TENSOR 5.45 runs it.**
Uses Angelier's own (α, β, γ, ψ) parametrisation (eq 14 / A2), in which the
tensor is *not* normalised, so its maximum shear moves with the solution. That
is why λ has to be re-adjusted over successive passes, and why the `LAMBDA`
printed in INFO1 is smaller than √3/2. Pipeline:

1. `INVDIR` pass *k*: minimise S₄ at the current λ, then set λ ← taumax of the
   result. The `(NO k)` printed in INFO1 **is the pass number**.
2. `PSIDIR`: freeze the axes, switch to the normalised A16 form, λ = √3/2, and
   re-minimise over ψ across a **full turn**. This fixes Φ and repairs
   artificial σ₁/σ₃ permutations.

Note that υ² is *quadratic* in (α, β, γ) at fixed ψ, so the inner minimisation
is an exact 3×3 linear solve. Angelier's Appendix I–II do this by hand; the
polynomials are regenerated numerically here because the appendix is
unreadable in the available scan.

**S4MIN — `pytensor.modern`, code `S4MN`, the exact minimum of the same S₄.**
Eigen-decomposition parametrisation, λ fixed at √3/2, global search. It reaches
a lower S₄ on **all 92 archive sites**, without exception:

| site | INVDIR S₄ | S4MIN S₄ |
|---|---|---|
| L12 | 0.3018 | 0.2360 |
| 0406-7 | 7.6198 | 7.3201 |

So the original program does not reach the minimum of its own criterion,
because λ stops before it converges.

**How far apart do they end up?** Comparing only the axis the data actually
constrain (σ₁ when Φ<0.5, σ₃ when Φ>0.5), over the 55 sites with 7 or more
faults:

| | median | p90 | max |
|---|---|---|---|
| constrained axis | 8.8° | 16.7° | 28.4° |
| degenerate axis | 19.1° | 39.1° | 71.7° |

It tightens with sample size: at n≥15 the constrained axis agrees to a median
of 4.8° and never worse than 12.5°. So the disagreement is mostly a
small-sample effect, not a method fault.

For scale: INVD's own bias on noise-free synthetic data is about 4°, and
Angelier quotes ±5–15° for field observation error on striae. The gap between
the two runs sits inside that noise floor.

Practical use: **INVDIR for continuity** with existing runs and with the
TENSOR-based literature; **S4MIN as a robustness check**, reported alongside.

## Verification

`tests/test_replication.py` reads the original archive files and checks
against them. Current status: **all pass**.

Site 0406-7 (29 faults, dips 42–89°) is the site that pins the algorithm down:

```
forward model vs MOHR1   max |SIGMN| 0.001  |TAU| 0.001  |TAUST| 0.001
                         max |RUP|   0.099  |ANG| 0.113
Mode A pipeline          sigma1 0.047 deg   sigma2 0.020   sigma3 0.032
                         Phi 0.138 (file 0.138)
                         mean ANG 20.898 (20.900)   mean RUP 54.097 (54.100)
                         LAMBDA printed 0.682 (0.680)
```

Site L12 (6 near-parallel, near-vertical planes) is degenerate and reproduces
less tightly (axes ~1°, mean RUP within 0.6 %). Tolerances in the test are set
per site to reflect that rather than being loosened globally.

## File format

Decoded 2026-07-28 by cross-checking the data file, `MOHR1`, `INFO1` and
`Mesure_key.txt`. Fixed-width ASCII:

| columns | content |
|---|---|
| `[0:2]` | type / movement-sense code (11, 12, 21, 22, 31 seen; table unknown but not needed) |
| `[2:5]` | **true dip azimuth**, already resolved with the quadrant letter (`SN 174 74E` → 84, not 264) |
| `[5:7]` | dip |
| `[7:10]` | **rake (pitch)** from the strike end at (dip azimuth − 90) |
| `[47:61]` | echo of what was typed; last field may be a rake (`62N`) or a trend (`124`) |

Two traps, both fallen into during development:

- **The movement direction is rake + 180.** Using the stored value directly
  swaps σ₁ and σ₃.
- On a site where every plane dips 85–89°, `sin(plunge) = sin(rake)·sin(dip)`
  makes rake and plunge agree within a degree, so `[7:10]` looks like a plunge.
  It is not. Site 0406-7 settles it.

The `03` result line is also fixed width (trend 5 chars, plunge 4), packed with
no separators; splitting it on whitespace or with a number regex gives garbage.

## Reading and writing the old files

Old runs go straight back in: point pyTENSOR at a site's data file (the
extension-less one named after the site, e.g. `L12`) and the fault slips load.
After inverting, it writes `INFO1` and `MOHR1` back out in the original layout,
and shows both in the interface.

`tests/test_report.py` regenerates both files for L12 and 0406-7 from the
recorded solutions and diffs them against the originals. It checks two things
separately: **layout**, by comparing the column spans of every number, and
**values**, numerically. Current status: 0 layout and 0 value mismatches on
both sites.

Two deliberate departures:

- the banner names pyTENSOR instead of claiming to be TENSOR 5.45. Everything
  a reader parses (the fixed-width table and the `03` result line) keeps the
  original layout, so the files still round-trip through `pytensor.tensorfile`.
- `RMU` can differ by tens of per cent when the normal stress is near zero,
  because it is a ratio; every other column agrees within 1.

Two layout details worth recording, both easy to get wrong:

- the two flag fields are two characters wide and **right** aligned, so `!!`
  butts against the number while a single `!` gets a space in front
- the columns headed `<75` and `<45` are the same statistic taken over the
  subset that passes the threshold, not a repeat of the previous column. On
  0406-7 the mean ANG is 21 over all 29 faults but 15 over the 28 below 45,
  the difference being the single datum at 174 degrees.

## Back-tilting

Rotate the data before inverting, three ways:

| mode | input | what it does |
|---|---|---|
| reference plane | dip azimuth / dip | the rotation that restores that plane to horizontal |
| reference plane by pole | trend / plunge | the same, given the plane by its pole |
| rotation axis | trend / plunge / angle | applies it directly, right-hand rule |

Both the fault normals and the slip vectors are rotated, so rakes and senses
carry through. The site label picks up the rotation in the archive's own form,
`(backtilted 020 -20)`.

**The angle is not computed.** There is no analytical solution for it: it is
found by trying values and looking at the result, which is why the archive
folders are named after what was tried. This only makes trying fast and records
what is in force. Choosing the reference surface, and the angle, stay with the
user.

The convention was fixed against the archive rather than assumed: solving for
the rotation between an original site and its back-tilted copy (Kabsch on the
fault normals) reproduces all seven cases to better than 2°.

## The reference archive

Tests and the derivation scripts read real output from the original program.
That is unpublished field data, so its location is not baked into the source:

```
set PYTENSOR_ARCHIVE=<folder holding the TENSOR run folders>
```

Without it, those tests skip rather than fail.

## Layout

```
pytensor/          the library
  core            geometry, the criterion, the quality estimators
  invdir          INVDIR, Angelier's parametrisation and pipeline
  modern          S4MIN, the exact minimum
  tensorfile      read the old site files
  report          write INFO1 and MOHR1
  entry           parse typed records
  plot            Angelier-style stereograms
  hpgl            read and write the plotter files
  rotate          back-tilting
pyTENSOR.py        desktop interface
tests/             regression against the archive
research/          how every constant was measured, see its own README
```

## Usage

```
pyTENSOR.bat                           desktop interface
python demo_report.py [site file]      invert an old site, print INFO1 + MOHR1
python run_batch.py [root] [out.csv]   both runs over a whole folder tree
python tests/test_replication.py       regression against the archive
python tests/test_report.py            INFO1 / MOHR1 layout and values
python tests/test_rotate.py            back-tilt convention
```

numpy, scipy, matplotlib, PyQt5.

## Status

- [x] criterion and quality estimators, verified on 35 faults
- [x] file reader
- [x] Mode A, INVDIR + PSIDIR
- [x] Mode B
- [x] desktop interface (stereonet, A/B comparison, INFO1 and MOHR1 tabs)
- [x] write INFO1 and MOHR1 in the original layout
- [ ] back-tilting (rotate data about the S₃ foliation before inversion)
- [ ] the `[0:2]` type-code table, still unknown
- [ ] writing TENSOR-format files back out
