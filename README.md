# pyTENSOR

A Python reconstruction of Jacques Angelier's **TENSOR** palaeostress inversion
program (TENSOR 5.45, jan91), written from the published method rather than by
disassembling the original 16-bit DOS binary.

Angelier 古應力反演程式 **TENSOR 5.45（1991 年 1 月版）** 的 Python 重建版。
不反譯 16 位元 DOS 執行檔，照他發表的方法重寫，並用原程式留下的九十幾個 run 逐位驗證。

Named in tribute to the original. 名稱致敬原程式。

**[English](#english)**　｜　**[中文](#中文)**　｜　**User manual: [English](docs/manual.en.md) · [中文](docs/manual.zh.md)**

---

# English

## What this is

Angelier's direct inversion method takes a set of measured fault planes and
slickenside lineations and returns the reduced stress tensor that best explains
them: the three principal stress directions and the shape ratio Φ. His program
`Tensor.exe` did this from 1991 onwards and a great deal of published
palaeostress work rests on it.

pyTENSOR does the same arithmetic, reads and writes the same files, draws the
same diagrams, and adds the parts the original never had: back-tilting, a tilt
test, and a second run that minimises the same criterion properly so you can see
how much of an answer is the method rather than the data.

## Why not decompile

`Tensor.exe` is a 208 KB 16-bit MS-DOS binary with 5252 relocations, no symbol
table, probably Turbo Pascal, with overlays and most likely software floating
point. It will not run on 64-bit Windows, which dropped NTVDM. Decompiling it is
a dead end for the usual reasons: compilation threw away the names, the types
and the structure, and 16-bit segmented addressing makes pointers impossible to
resolve statically.

The algorithm, on the other hand, is fully published:

- Angelier, J. (1990) *Inversion of field data in fault tectonics to obtain the
  regional stress. III. A new rapid direct inversion method by analytical
  means.* Geophys. J. Int. **103**, 363-376.
- Angelier, J. (1984) *Tectonic analysis of fault slip data sets.*
  J. Geophys. Res. **89**(B7), 5835-5848.
- Angelier, J. (1994) *Fault slip analysis and palaeostress reconstruction.*
  In: Hancock (ed.) *Continental Deformation*, ch. 4.

So the work went into reading the papers, and into measuring the original's own
output files for everything the papers do not state.

## Quick start

```
pyTENSOR.bat                           desktop interface
python demo_report.py [site file]      invert an old site, print INFO1 + MOHR1
python run_batch.py [root] [out.csv]   both runs over a whole folder tree
```

Requires numpy, scipy, matplotlib, PyQt5. The full interface walkthrough,
control by control, is in **[docs/manual.en.md](docs/manual.en.md)**.

Type a fault in four fields and watch it land on the stereogram:

```
CS - 122 - 87W - 124
|    |     |     |
|    |     |     +-- pitch and quadrant (62N), or a bare trend (124)
|    |     +-------- dip and its quadrant
|    +-------------- strike
+------------------- confidence C/P/S  +  movement I/N/S/D
```

Or open an old run directly: point it at the extension-less data file named
after the site, for example `L12`, and everything loads, INFO1 and all.

## The criterion

| | |
|---|---|
| stress vector | σ = **T**·n  (eq 3) |
| shear traction | τ = σ − (n·σ)n  (eq 4-5) |
| upsilon vector | λs = τ + υ  (eq 12) |
| **objective** | **υ² = λ² + \|τ\|² − 2λ(s·σ)**  (eq A1), minimise **S₄ = Συ²** (eq 13) |
| quality | RUP = 100·\|υ\|/(√3/2), 0-200 % ; ANG = angle(s, τ), 0-180° |

The reduced stress tensor is normalised so that the **sum of squared
eigenvalues is 3/2** (eq A16), not so that σ₁ − σ₃ is fixed. The two agree only
at Φ = 0.5, and the criterion is not scale invariant, so this matters.

**The criterion is biased, and that is not a bug in anyone's code.** υ asks for
two things at once: that the predicted shear points along the observed slip,
and that its magnitude is close to λ. Fed perfect Bott data with no noise at
all, it still misses the true tensor by about 4 degrees, because it favours
orientations that put high shear on the faults. The angle-only criterion F2
recovers the same data to 0.00 degrees. This is the root of why TectonicsFP and
similar programs disagree with Angelier's numbers.

## Two runs: INVDIR and S4MIN

Named after what they are, not by a letter that would imply one is better.
**Neither is "the true stress"**, for the reason above.

### INVDIR

`pytensor.invdir`, code `INVD`, as TENSOR 5.45 runs it.

Uses Angelier's own (α, β, γ, ψ) parametrisation, equation (14), printed as
(A2) in the appendix:

```
T = [[cos ψ,  α,            γ          ],
     [α,      cos(ψ+2π/3),  β          ],
     [γ,      β,            cos(ψ+4π/3)]]
```

This tensor is **not** normalised: its entries square to 3/2 + 2(α²+β²+γ²), so
its maximum shear moves as the solution moves. That is exactly why λ has to be
re-adjusted over successive passes, and why the `LAMBDA` printed in INFO1 comes
out smaller than √3/2. The pipeline is:

1. **INVDIR pass k**: minimise S₄ at the current λ, then set λ to the taumax of
   the result. The `(NO k)` printed in INFO1 **is the pass number**, not a
   choice between two solutions.
2. **PSIDIR**: freeze the axes, switch to the normalised A16 form, λ = √3/2, and
   re-minimise over ψ across a **full turn**. This fixes Φ and repairs the
   artificial σ₁/σ₃ permutations the unnormalised pass can produce.

Two things to know if you reimplement this. υ² is *quadratic* in (α, β, γ) at
fixed ψ, so the inner minimisation is an exact 3×3 linear solve; Angelier's
Appendix I and II do that expansion by hand and the polynomials are regenerated
numerically here because the appendix is unreadable in the available scan. And
ψ must be scanned over the whole circle: restricting it to [0, π/3] gives Φ = 0
and the wrong axes, because the minimum often sits near ψ = 336-353°.

### Reproducing a specific historical run

λ is re-derived from scratch by default. Where the pass-1 surface is nearly flat
that can land a degree away with a *worse* fit than the original. On L12, six
near-parallel near-vertical planes, re-deriving gives σ₁ 82.2/35.7 at S₄ 0.3150
against the original's 81.0/35.9 at 0.3013.

Passing `lam_printed=` the LAMBDA that site's own INFO1 records fixes it. The
solver λ that prints that value is solved for, and the run follows the original:

| site | re-derived | adopting the recorded LAMBDA |
|---|---|---|
| L12 | 1.02° off, S₄ +0.0137 | **0.31° off, S₄ −0.0028** |
| CH-01ABE | 1.35° off, S₄ +0.0538 | **0.89° off, S₄ +0.0350** |
| 0406-7 | 0.05° off | 0.08° off |

One trap: the map from solver λ to printed λ is **not monotonic**. On L12 it
rises to about 0.87 near λ 2.5 and falls away again, so bisecting on the end
points finds no bracket and gives up even though the target is reachable. The
search scans, collects every crossing, and takes the one nearest the λ the
iteration had already reached on its own.

In the interface this is the **archive LAMBDA** box, enabled and ticked
automatically when a site is opened with an INFO1 beside it.

### S4MIN

`pytensor.modern`, code `S4MN`, the exact minimum of the same S₄.

Eigen-decomposition parametrisation, so λ is the constant √3/2 by construction
and no adjustment loop is needed; the search is global. It reaches a lower S₄ on
**all 92 archive sites**, without exception:

| site | INVDIR S₄ | S4MIN S₄ |
|---|---|---|
| L12 | 0.3018 | 0.2360 |
| 0406-7 | 7.6198 | 7.3201 |

So the original program does not reach the minimum of its own criterion, because
λ stops before it converges.

### What λ is, in Angelier's own words

None of this is reverse-engineered. Angelier sets it out in Section 4 and
Appendix IV of the 1990 paper, and it is worth reading before drawing any
conclusion from the difference between the two runs.

λ is the **largest shear stress the tensor can produce**. The criterion wants
the predicted shear to point along the observed slip *and* to be large enough to
overcome friction, so λ is the magnitude it is aiming at.

For the normalised A16 tensor that is a constant. For the equation (14) tensor
it is not, and Angelier says why: the diagonal terms carry ψ while the
off-diagonal terms do not, so turning the axes changes the magnitude of the
stress. His summary is that "rotation of axes and magnitude of stress are not
analytically independent" (1990, Section 4), and that without this the parameter
would simply be a constant and no adjustment would be needed.

His fix is the iteration: run the determination a few times, each pass taking λ
to be the largest shear of the previous pass. That is exactly what `(NO k)`
counts.

**Angelier also says plainly that the A16 form would be better**, that it would
make the λ adjustment unnecessary and leave λ constant at √3/2, and that he did
not use it because he could not solve that formulation analytically, while
noting there is no reason to think it impossible (Appendix IV). PSIDIR, the
final step, is the A16 form used once at the end, and he describes it as added
for safety against the artificial σ₁/σ₃ permutations that the unnormalised form
produces on poorly varied data.

So **S4MIN is not a modernisation of Angelier's method. It is the formulation he
described and wanted**, reached numerically because the analytical route he
needed in 1990 was closed. The gap between the two runs is the cost of that
1990 constraint, not a disagreement about geology.

### The iteration does not converge, and stopping early is the point

Angelier says "few successive determinations". He does not say how many, and he
does not claim convergence. Checking that against the archive: **the iteration
runs away on 72 of the 92 sites.** Site 0406-7 is one, left to run λ goes
0.866 → 1.009 → 1.115 → … → 1.1 × 10⁹ by pass 200, with S₄ degrading from 4 per
cent above the minimum to 78 per cent. On L12 it does settle, at λ = 2.2404 and
1.5 per cent above the minimum.

The mechanism is positive feedback: a larger λ asks the solver to match a larger
shear, it obliges by inflating the unnormalised tensor, and the inflated tensor
has a larger taumax, which becomes the next λ.

So a **user-chosen pass count** rather than "iterate to convergence" is not a
shortcut. On most sites it is what keeps the answer finite. The archive bears
that out: NO 1 on 62 sites, NO 2 on 25, and 3 to 5 on the remaining five.

### Reading convergence off an INFO1

INFO1 prints three numbers, and it is easy to read the wrong one:

```
SOLUTION INVDIR (NO 1)  LAMBDA= 0.68     <- the lambda INVDIR actually used
SOLUTION PSIDIR         AXES OK !
LAMBDA= 0.87            TAUMAX= 0.80     <- PSIDIR: lambda is sqrt(3)/2 by
                                            construction, so it is 0.87 in
                                            every file ever written
```

`TAUMAX` is not √3/2 either. For a normalised tensor with eigenvalues
cos(ψ + k·2π/3) the largest shear is

```
taumax = 3 / (4 sqrt(Phi^2 - Phi + 1))
```

which runs from 0.75 at Φ = 0 or 1 up to √3/2 = 0.866 at Φ = 0.5. That matches
the printed TAUMAX to within 0.005 on 87 archive runs, which is a useful check
that the whole picture is right.

**The adjustment has converged when the first number has climbed to meet the
third.** Across the 88 archive runs with both numbers, the median gap is 0.160
and none of them is inside 0.02:

| TAUMAX − LAMBDA | sites |
|---|---|
| ≤ 0.02, converged | 0 |
| 0.02 to 0.05 | 4 |
| 0.05 to 0.15 | 31 |
| over 0.15 | 53 |

That is not a criticism of how the runs were made. Given that the iteration
diverges on most sites, stopping at NO 1 or NO 2 was the right thing to do. It
does mean the recorded λ is a stopping point rather than a solution, which is
what **archive LAMBDA** exists to reproduce.

This also means the INVDIR-to-S4MIN gap is not one number. It depends on the
site and on the pass count that was used:

| | n ≥ 7 (55 sites) | n ≥ 15 (10 sites) |
|---|---|---|
| constrained axis | median 8.9°, p90 20.8° | median 4.8°, max 12.5° |
| \|ΔΦ\| | median 0.074 | median 0.065 |
| S₄ above the minimum | median 27 % | median 6 % |

0406-7's 4 per cent is at the good end. Note that the S₄ percentage is a poor
guide at small n: the tensor has four unknowns, so with four or five data the
global minimum falls to nearly zero and any ratio against it explodes. The angle
between the axes is the number to read.

### How far apart do they end up

Comparing only the axis the data actually constrain, σ₁ when Φ < 0.5 and σ₃ when
Φ > 0.5, over the 55 sites with seven or more faults:

| | median | p90 | max |
|---|---|---|---|
| constrained axis | 8.8° | 16.7° | 28.4° |
| degenerate axis | 19.1° | 39.1° | 71.7° |

It tightens with sample size: at n ≥ 15 the constrained axis agrees to a median
of 4.8° and never worse than 12.5°. The disagreement is mostly a small-sample
effect, not a method fault.

For scale, INVD's own bias on noise-free synthetic data is about 4°, and
Angelier quotes ±5-15° for field observation error on striae. The gap between
the two runs sits inside that noise floor.

**Practical use:** INVDIR for continuity with existing runs and with the
TENSOR-based literature; S4MIN as a robustness check, reported alongside.

## Back-tilting

Back-tilting has a window of its own, opened from the toolbar. The main window
shows the data as measured and nothing else, so a stereogram there never needs a
caption to say which orientation it is in.

The window rotates the data, inverts both states, and shows them side by side:
measured on the left, restored on the right, with the numbers for both
underneath. Three ways to set the rotation:

| mode | input | what it does |
|---|---|---|
| reference surface | strike / dip, or its pole as trend / plunge | the rotation that restores that surface to horizontal |
| rotation axis | trend / plunge / angle | applies it directly, right-hand rule |
| partial | 0 to 125 % | any fraction of either of the above |

Both the fault normals and the slip vectors are rotated, so rakes and senses
carry through. The convention was fixed against the archive rather than assumed:
solving for the rotation between an original site and its back-tilted copy
(Kabsch on the fault normals) reproduces all seven cases to better than 2°.

Reference surfaces are drawn as dashed great circles with their poles, and they
rotate with the data, so a correct restoration is visible: the dashed circle
flattens onto the primitive and the pole walks in to the centre.

**The angle is not computed.** There is no analytical solution for it. It is
found by trying values and looking at the result, which is why the archive
folders are named after what was tried, `(backtilted 020 -20)`. This only makes
trying fast and keeps the rotation in force visible. Choosing the reference
surface, and the angle, stay with the user.

### Where did the axes go

The measured axes put through the same rotation are drawn on the restored
diagram as **open rings**, with a dashed arc to the star. A back-tilted diagram
on its own does not show you the tilting; the axes are simply somewhere else and
nothing on the page says where they came from.

Ring and star need not coincide, and whether they do depends on the method.

- **S4MIN is exactly equivariant.** S₄ is rotation invariant, so its exact
  minimum turns with the data. Its Φ and S₄ therefore *cannot* change under
  back-tilting, and the entire content of a tilt test is where the axes end up.
- **INVDIR is not.** Equation (14) pins the tensor's **diagonal** to cos ψ,
  cos(ψ+2π/3), cos(ψ+4π/3) in the **geographic** frame. That four-parameter
  family is a different family once the data are turned, so re-inverting rotated
  data searches somewhere else.

This is a property of Angelier's method, not of this reconstruction. Checked
against the original program on the fourteen back-tilt pairs in the reference
archive, matched to their un-tilted parents by Kabsch to better than 2°:

| | median | max |
|---|---|---|
| σ₁ carried vs re-inverted | 10.4° | 66.4° |
| σ₂ | 24.3° | 88.7° |
| σ₃ | 23.6° | 87.5° |

The largest values fall where Φ is near 0 or 1 and two axes are near
degenerate, but not all of them do: site 0214-5, thirteen faults, Φ 0.46 → 0.72,
still moves σ₁ by 19.8° and σ₃ by 22.8°.

**What it means in practice.** On INVDIR alone, a change in the axes across a
back-tilt is partly the parametrisation and not the geology, so "the axes came
back to horizontal and vertical" is not by itself evidence. Read the Andersonian
test off S4MIN, where the axes provably only rotate, and keep INVDIR for
continuity with the older runs. The window prints both and the separation
between them. Locked down in `tests/test_backtilt.py`.

### Restoring to horizontal is not automatically right

That assumes the faults predate the tilting. If they formed *during* it, only
part of the tilt post-dates them, and removing all of it over-rotates the data
into a stress tensor that never existed.

**Tilt test** sweeps the rotation from 0 to 125 per cent, inverting at every
step and plotting two diagnostics:

| | what it says |
|---|---|
| mean ANG, RUP, S₄ | how well one tensor explains the data. Best near 100 per cent means the faults predate the tilting |
| Andersonian misfit | 90° minus the plunge of the steepest axis, so 0 is one axis vertical and two horizontal. Also names the regime: σ₁ vertical is normal, σ₂ strike-slip, σ₃ thrust |

A best answer well short of full restoration is what syn-tilt faulting looks
like, and the program says so. If the two criteria disagree by more than 20 per
cent of the rotation it says that too, because that needs explaining before
either is trusted. Neither is proof; they are diagnostics.

Worked example, site 0404-4C-2 against an invented reference surface: both
criteria get *worse* with restoration, best fit at 10 per cent, and the
Andersonian misfit rises from 40.8° to 49.2°. Restoring that surface to
horizontal would have quietly produced a worse answer than the raw data.

## Drawing: the HPGL files are the reference

Every run folder holds an `HPGL` file, which is plain-text plotter vector
commands. It is not a description of what the program drew, it *is* what the
program drew, stroke by stroke. So the drawing style here was measured off those
files rather than guessed from figure captions.

- **Equal-area (Schmidt) projection.** Decided by a test, not by assumption: a
  great circle is a true circular arc under stereographic projection and is not
  under equal-area. Circle-fit residuals came out at 0.0044 / 0.0062 / 0.0010
  against an equal-area prediction of 0.0040 / 0.0055 / 0.0007. Under
  stereographic they would be zero.
- **Stars**: σ₁ five-pointed, σ₂ four-pointed and set diagonally, σ₃
  three-pointed. Their size is not constant:
  `size = 0.1004 + 0.0928·(0.5 − Φ)·λᵢ`, fitted over 63 stars on 21 plots, rms
  0.00063. At Φ = 0.5 all three come out equal, which is why the size order
  flips either side of it.
- **Striae are a shear couple, not one arrow**: a filled dot with two parallel
  shafts each offset 0.024 to its own side, so the symbol reads as a Z. The head
  follows the confidence code: S has none, P gets one barb per end, C gets a
  two-segment slender head. Which side the offset and barbs sit is
  `sign(slip · strike)`, right on all 89 samples; reading it off the movement
  letter is right on only 83.
- **Heavy arrows** outside the circle, inward along σ₁ and outward along σ₃,
  omitted for an axis plunging more than 45°.
- **The frame box is not symmetric about the centre of the stereogram.** All 93
  archive HPGL files put it at x −1.2527 to 1.2547 and y −1.3047 to 1.4585, in
  units of the primitive radius, and set every caption left aligned at a fixed
  column. An earlier pass here assumed a symmetric box and put the bottom edge
  0.15 radii too low.

**HPGL export** replays `plot.plot_site` into a recorder that stands in for a
matplotlib Axes (`pytensor.penrec`), so the file carries exactly what the figure
carries and there is no second drawing routine to drift. Output lands on the
archive's own frame, 400 to 5420 by 396 to 5928 plotter units, which
`tests/test_ui_contract.py` checks.

## Reading and writing the old files

Old runs go straight back in, and after inverting, pyTENSOR writes `INFO1` and
`MOHR1` back out in the original layout and shows both in the interface.

`tests/test_report.py` regenerates both files for L12 and 0406-7 from the
recorded solutions and diffs them against the originals. It checks **layout**,
by comparing the column spans of every number, and **values**, numerically.
Current status: 0 layout and 0 value mismatches on both sites.

Two deliberate departures:

- the banner names pyTENSOR instead of claiming to be TENSOR 5.45. Everything a
  reader parses, the fixed-width table and the `03` result line, keeps the
  original layout, so the files still round-trip through `pytensor.tensorfile`.
- `RMU` can differ by tens of per cent when the normal stress is near zero,
  because it is a ratio. Every other column agrees within 1.

Two layout details worth recording, both easy to get wrong:

- the two flag fields are two characters wide and **right** aligned, so `!!`
  butts against the number while a single `!` gets a space in front.
- the columns headed `<75` and `<45` are the same statistic taken over the
  subset that passes the threshold, not a repeat of the previous column. On
  0406-7 the mean ANG is 21 over all 29 faults but 15 over the 28 below 45, the
  difference being the single datum at 174 degrees.

## File format

Decoded by cross-checking the data file, `MOHR1`, `INFO1` and `Mesure_key.txt`,
verified on 35 records from two sites. Fixed-width ASCII, one folder per run,
input and output in the same file:

| columns | content |
|---|---|
| `[0:2]` | first digit is the striae confidence, **1 = C, 2 = P, 3 = S**; second digit says which end of the strike line the rake was measured from (1 = the canonical end at dip azimuth − 90, 2 = the other, in which case the stored value is 180 − input) |
| `[2:5]` | **true dip azimuth**, already resolved with the quadrant letter, so `SN 174 74E` gives 84 and not 264 |
| `[5:7]` | dip |
| `[7:10]` | **rake (pitch)**, from the strike end at (dip azimuth − 90) |
| `[47:61]` | echo of what was typed; the last field may be a rake (`62N`) or a trend (`124`) |

Two traps, both fallen into during development:

- **The movement direction is rake + 180.** Using the stored value directly
  swaps σ₁ and σ₃.
- On a site where every plane dips 85-89°, `sin(plunge) = sin(rake)·sin(dip)`
  makes rake and plunge agree within a degree, so `[7:10]` looks like a plunge.
  It is not. Site 0406-7, dips 42-89°, settles it.

The `03` result line is also fixed width, trend 5 characters and plunge 4,
packed with no separators. Splitting it on whitespace or with a number regex
gives garbage.

## Verification

Seven test files, all passing. They read the original archive when it is
available and skip rather than fail when it is not.

| test | what it pins |
|---|---|
| `test_replication.py` | the whole pipeline against the original program's own output |
| `test_report.py` | INFO1 and MOHR1 layout and values |
| `test_entry.py` | typed records against the stored ones, 35 records |
| `test_rotate.py` | the back-tilt convention, against seven archive pairs |
| `test_backtilt.py` | S4MIN is equivariant, INVDIR is not |
| `test_ui_contract.py` | everything the GUI reaches for exists; the HPGL export |
| `test_gui_logic.py` | the non-Qt half of the interface |

Site 0406-7, 29 faults with dips from 42 to 89°, is the site that pins the
algorithm down:

```
forward model vs MOHR1   max |SIGMN| 0.001  |TAU| 0.001  |TAUST| 0.001
                         max |RUP|   0.099  |ANG| 0.113
INVDIR pipeline          sigma1 0.047 deg   sigma2 0.020   sigma3 0.032
                         Phi 0.138 (file 0.138)
                         mean ANG 20.898 (20.900)   mean RUP 54.097 (54.100)
                         LAMBDA printed 0.682 (0.680)
```

Site L12, six near-parallel and near-vertical planes, is degenerate and
reproduces less tightly, axes to about 1° and mean RUP within 0.6 per cent.
Tolerances are set per site to reflect that rather than being loosened globally.

No Qt object is ever constructed in a test: a QApplication started from an
automated shell pops a platform-plugin dialog and exits. What the tests do
instead is verify the contract between the interface and the library.

## Performance

The ψ scan used to call a scalar routine 4000 times per pass, with a 120-step
ternary search on top, and the archive-LAMBDA search repeated all of that about
ninety times. Almost none of that work depends on ψ: only the diagonal carries
it, and linearly, so the 3×3 normal matrix is a constant of the data set and
each ψ costs one right-hand side against the same factorisation. PSIDIR and the
S4MIN start search reduce the same way, through the eigenframe.

Measured on site 0406-7, 29 faults:

| | before | after |
|---|---|---|
| INVDIR, 2 passes | 0.975 s | 0.004 s |
| S4MIN, 400 starts | 0.208 s | 0.052 s |
| archive LAMBDA | 6.775 s | 0.063 s |

Agreement with the routines they replaced is 1e-13.

## The reference archive

Tests and the derivation scripts read real output from the original program.
That is unpublished field data, so its location is not baked into the source:

```
set PYTENSOR_ARCHIVE=<folder holding the TENSOR run folders>
```

Without it, those tests skip rather than fail. The data itself is not
distributed with this repository.

## Layout

```
pytensor/           the library
  core              geometry, the criterion, the quality estimators
  invdir            INVDIR, Angelier's parametrisation and pipeline
  modern            S4MIN, the exact minimum of the same criterion
  tensorfile        read the old site files
  report            write INFO1 and MOHR1
  entry             parse typed records
  plot              Angelier-style stereograms
  hpgl              read and write the plotter files
  penrec            replay the drawing code into plotter vectors
  rotate            rotations and the back-tilt convention
  tilt              Andersonian misfit and the incremental tilt sweep
  backtilt          the back-tilt window
  tiltui            the tilt-test dialog
  splash, about     opening screen and the About box
  retro, ui_style   1991 mode and the normal stylesheet
  archive           where the reference archive is
pyTENSOR.py         desktop interface
tests/              regression against the archive
research/           how every constant was measured, see its own README
```

## Credits and use

The method is Jacques Angelier's. This is an independent reimplementation from
his published papers, plus measurements taken from output files his program
wrote; no code was taken from the original binary.

The opening screen is Angelier's own block diagram of the Taiwan arc-continent
collision. He used earthquake focal mechanisms from near Yuli as the worked
example of applying this method to seismological data (1994, fig. 4.44). That
image is a published figure and is **not** committed here, so a fresh clone
starts without an opening screen and without the easter egg behind it. Drop
`Taiwan Tectonic Map.jpg` in the repository root to get both back.

Maintainer: Chi-Hsiu Pang. Licence not yet chosen; treat as all rights reserved
until one is added.

## Changelog

**0.2.0**

- back-tilting moved to a window of its own, measured and restored side by side,
  with the measured axes carried through the rotation drawn as open rings
- established, and pinned in a test, that INVDIR is not rotation equivariant
  while S4MIN is; confirmed against the original program on 14 archive pairs
- HPGL export rewritten to replay the real drawing code, so it carries the whole
  figure instead of the primitive and the fault planes only
- corrected the frame box, which is not symmetric about the centre, and the
  caption anchors, on screen and in every export
- ψ scans vectorised: INVERT went from seconds to milliseconds
- interface: a permanent line saying what is on screen, an out-of-date badge
  when the data have changed since the last inversion, per-panel titles,
  hairlines between sidebar sections

**0.1.0**

- criterion, quality estimators and forward model, verified on 35 faults
- INVDIR with PSIDIR, and S4MIN
- file reader, INFO1 and MOHR1 writers in the original layout
- Angelier-style stereograms measured off the archive HPGL
- desktop interface, 1991 mode

## Still open

- the `[0:2]` type-code table is decoded but not cross-checked against a manual
- writing TENSOR-format data files back out
- PSID, R4DT and NDA, Angelier's other methods, deliberately not started
- a licence

---

# 中文

## 這是什麼

Angelier 的直接反演法從一組實測斷層面與擦痕線理，解出最能解釋它們的簡化應力張量，
也就是三個主應力方向與形狀比 Φ。他的程式 `Tensor.exe` 從 1991 年起就在做這件事，
大量已發表的古應力工作建立在它上面。

pyTENSOR 做同一套運算、讀寫同一批檔案、畫同一種圖，
再補上原程式沒有的部分：回轉（back-tilting）、傾轉檢驗，
以及第二種把同一個準則真正最小化的跑法，讓你看得出一個答案有多少是方法造成的、多少是資料造成的。

## 為什麼不反譯

`Tensor.exe` 是 208 KB 的 16 位元 MS-DOS 執行檔，5252 個重定位項、沒有符號表、
疑似 Turbo Pascal、有 overlay、浮點很可能走軟體模擬。
64 位元 Windows 移除了 NTVDM，所以它跑不動。
反譯是死路，理由很平常：編譯把名字、型別、結構都刪了，16 位元分段定址讓指標無法靜態解析。

但演算法本身在論文裡寫得很完整（見上方英文段的三篇）。
所以力氣花在讀論文，以及**量原程式自己吐出來的檔案**，補上論文沒寫的部分。

## 怎麼跑

```
pyTENSOR.bat                           桌面介面
python demo_report.py [站檔]           反演一個舊站，印出 INFO1 + MOHR1
python run_batch.py [根目錄] [out.csv] 對整棵資料夾跑兩種方法
```

需要 numpy、scipy、matplotlib、PyQt5。
逐一功能的完整操作說明在 **[docs/manual.zh.md](docs/manual.zh.md)**。

輸入是四欄，打完就看到它落在投影網上：

```
CS - 122 - 87W - 124
|    |     |     |
|    |     |     +-- rake ＋象限（62N），或直接給 trend（124）
|    |     +-------- 傾角＋象限
|    +-------------- 走向
+------------------- 信心度 C/P/S ＋ 運動方式 I/N/S/D
```

或直接開舊 run：指向那個**沒有副檔名、檔名等於站名**的資料檔（例如 `L12`），
斷層資料、INFO1 全部一起載進來。

## 準則

- σ = **T**·n（式 3）；τ = σ − (n·σ)n（式 4-5）
- **υ² = λ² + |τ|² − 2λ(s·σ)**（式 A1），最小化 **S₄ = Συ²**（式 13）
- RUP = 100·|υ|/(√3/2)，範圍 0-200 %；ANG = s 與 τ 的夾角，0-180°
- 張量正規化是**特徵值平方和 = 3/2**（式 A16），**不是**固定 σ₁ − σ₃。
  兩者只在 Φ = 0.5 相同，而準則不是尺度不變的，所以這個差別會改變答案。

**這個準則本身有偏差，不是誰的程式有 bug。**
υ 同時要求「預測剪應力方向對上實測滑動」與「剪應力大小接近 λ」，
所以餵零雜訊的完美 Bott 合成資料，它仍然差真張量約 4°，會系統性偏向讓斷層承受高剪應力的方位。
純角度準則 F2 在同一批資料上是 0.00°。
這就是 TectonicsFP 這類軟體跟 Angelier 算不一樣的根本原因。

## 兩種跑法：INVDIR 與 S4MIN

用「它是什麼」命名，不用會暗示優劣的字母。因為上面那個理由，**兩者都不是「真應力」**。

**INVDIR**（`pytensor.invdir`，代碼 `INVD`）＝ Angelier 原方法、原程式的跑法。
用他自己的 (α, β, γ, ψ) 參數化（式 14 / A2）。這個張量**沒有正規化**，
最大剪應力會隨著解移動，這才是 λ 必須逐趟迭代的原因，
也是 INFO1 印出來的 `LAMBDA` 小於 √3/2 的原因。流程兩段：

1. **INVDIR 第 k 趟**：在當前 λ 下最小化 S₄，然後把 λ 換成該解的 taumax。
   INFO1 印的 `(NO k)` **是迭代趟數**，不是「兩個解取哪一個」。
2. **PSIDIR**：軸凍結在 INVDIR 的結果，改用正規化的 A16 形式、λ = √3/2，
   對 ψ **整圈**重新最小化。這一步定下 Φ，並修掉前一段可能產生的 σ₁/σ₃ 人為對調。

兩個實作要點。固定 ψ 時 υ² 對 (α, β, γ) 是二次式，內層就是精確的 3×3 線性解，
不必抄附錄那些多項式（可讀的掃描檔裡附錄看不清楚，這裡用數值重生）。
另外 ψ 一定要掃整圈：限制在 [0, π/3] 會得到 Φ = 0 的錯誤答案，
最小值常常落在 ψ ≈ 336-353°。

**S4MIN**（`pytensor.modern`，代碼 `S4MN`）＝同一個 S₄ 的精確最小值。
用特徵分解參數化，所以 λ 天生固定在 √3/2，不需要迭代；搜尋是全域的。
它在**全部 92 個 archive 站**都得到更低的 S₄，無一例外
（L12 0.2360 對 0.3018；0406-7 7.3201 對 7.6198）。
也就是說，原程式並沒有走到它自己準則的最小值，因為 λ 停在未收斂處。

### λ 是什麼：Angelier 自己的說法

以下都不是逆向工程猜的，是他 1990 年論文 Section 4 與 Appendix IV 白紙黑字寫的。

λ 是**這個張量能產生的最大剪應力**。準則同時要求預測剪應力方向對上實測滑動、
大小又要大到足以克服摩擦，λ 就是它瞄準的那個大小。

正規化的 A16 張量的最大剪應力是常數；式 (14) 的張量不是。原因他講得很白：
對角線帶著 ψ、非對角線不帶，所以**轉動應力軸會改變應力大小**。
他的總結是「軸的旋轉與應力大小在解析上不獨立」（1990, Section 4），
並說如果不是這樣，λ 就只是個常數、根本不需要調整。

他的補救就是那個迭代：跑個幾趟，每趟把 λ 換成前一趟解的最大剪應力。`(NO k)` 數的就是這個。

**Angelier 也明講 A16 那個形式比較好**：那樣 λ 的調整整個不需要、λ 恆等於 √3/2；
他沒用是因為那個式子他解析解不出來，同時註明「沒有理由認為不可能」（Appendix IV）。
PSIDIR 這最後一步，就是把 A16 形式在收尾用一次，他自己說是「為了安全加上的」，
用來修未正規化形式在資料方位變化太少時會產生的 σ₁/σ₃ 人為對調。

所以 **S4MIN 不是把 Angelier 的方法「現代化」，而是他描述過、想要但當年做不出來的那個形式**，
只是改用數值方法走到。兩種跑法的差距是 1990 年那個限制的代價，不是地質上的分歧。

### λ 迭代不會收斂，而「提早停」正是重點

Angelier 只說「幾趟連續的決定」，沒說幾趟，也沒宣稱收斂。拿 archive 驗證：
**92 站裡有 72 站會發散。** 0406-7 就是其中之一：放它一直跑，
λ 從 0.866 → 1.009 → 1.115 → … 到第 200 趟變成 1.1 × 10⁹，
S₄ 從高於最小值 4 % 惡化到 78 %。L12 則會收斂，停在 λ = 2.2404、高於最小值 1.5 %。

機制是正回饋：λ 變大就是要求更大的剪應力，
求解器照辦的方式是把沒正規化的張量撐大，撐大的張量最大剪應力又更大，變成下一輪的 λ。

所以**使用者自選趟數**而不是「迭代到收斂」，不是偷懶；在多數站上那是唯一讓答案不爆掉的做法。
archive 印證：62 站 NO 1、25 站 NO 2、五站 3 到 5。

### 從 INFO1 直接讀收斂程度

INFO1 印三個數字，很容易讀錯一個：

```
SOLUTION INVDIR (NO 1)  LAMBDA= 0.68     <- INVDIR 實際用的 λ
SOLUTION PSIDIR         AXES OK !
LAMBDA= 0.87            TAUMAX= 0.80     <- PSIDIR：λ 天生就是 √3/2，
                                            所以每一個檔案都印 0.87
```

`TAUMAX` 也不是 √3/2。特徵值為 cos(ψ + k·2π/3) 的正規化張量，最大剪應力是

```
taumax = 3 / (4·√(Φ² − Φ + 1))
```

從 Φ = 0 或 1 時的 0.75 到 Φ = 0.5 時的 0.866。87 個 archive run 對到 0.005 以內，
這也順便驗證了整個理解沒有錯。

**第一個數字爬到跟第三個數字一樣，才是收斂。** 88 個有這兩個數字的 run，
中位差距 0.160，沒有任何一個在 0.02 以內：

| TAUMAX − LAMBDA | 站數 |
|---|---|
| ≤ 0.02（收斂） | 0 |
| 0.02 到 0.05 | 4 |
| 0.05 到 0.15 | 31 |
| 超過 0.15 | 53 |

這不是在批評當年的跑法：迭代在多數站上會發散，停在 NO 1、NO 2 是對的。
它的意思是**記錄下來的 λ 是一個停止點、不是一個解**，
而 **archive LAMBDA** 這個功能存在的目的就是重現那個停止點。

這也表示 INVDIR 與 S4MIN 的差距**不是一個固定數字**，它取決於站別與當年用的趟數：

| | n ≥ 7（55 站） | n ≥ 15（10 站） |
|---|---|---|
| 受約束的軸 | 中位 8.9°、p90 20.8° | 中位 4.8°、最大 12.5° |
| \|ΔΦ\| | 中位 0.074 | 中位 0.065 |
| S₄ 高於最小值 | 中位 27 % | 中位 6 % |

0406-7 的 4 % 是偏好的那一端。
⚠️ 注意 S₄ 的百分比在 n 小的時候是**壞指標**：張量有四個未知數，
所以只有四五筆資料時全域最小值會趨近於零，任何跟它相比的比值都會爆掉。
該讀的是軸與軸之間的夾角。

**兩者差多少**：只看資料真正約束住的那根軸（Φ<0.5 看 σ₁、Φ>0.5 看 σ₃），
在 n ≥ 7 的 55 站，中位 8.8°、p90 16.7°、最大 28.4°。
n ≥ 15 時收斂到中位 4.8°、最大 12.5°，所以分歧主要是**樣本數問題**，不是方法錯。
對照組：INVD 自身在無雜訊合成資料上的偏差約 4°，Angelier 引的野外擦痕觀測誤差 ±5-15°。
兩種跑法的差距落在這個雜訊底線之內。

**實務建議**：以 **INVDIR 為主**，維持與既有 run、與 TENSOR 系文獻的一致性；
**S4MIN 當穩健性檢驗**併陳。

## 回轉（back-tilting）

回轉有自己的視窗，從工具列開。主視窗只呈現實測資料，不做旋轉，
所以那裡的投影網永遠不需要一行標題來說明它現在是什麼方位。

回轉視窗把資料轉過去、對前後兩個狀態各跑一次反演，左右並列：
左邊 as measured、右邊 back-tilted，下面是兩者的數字。設定旋轉有三種方式：

| 方式 | 輸入 | 作用 |
|---|---|---|
| 參考面 | 走向 / 傾角，或用它的 pole 給 trend / plunge | 把該面轉回水平的那個旋轉 |
| 旋轉軸 | trend / plunge / 角度 | 直接套用，右手定則 |
| 部分回轉 | 0 到 125 % | 上面任一種的任意比例 |

斷層面法向與滑動向量都會一起轉，所以 rake 與運動感都跟著走。
慣例不是猜的，是對 archive 驗過的：把原站與它的回轉版之間的旋轉解出來（對法向做 Kabsch），
七組全部重現到 2° 以內。

參考面畫成虛線大圓加它的 pole，並且跟著資料一起轉，
所以回轉對不對看得出來：虛線圓會壓平到基準圓上，pole 會走到圓心。

**角度不是算出來的。** 它沒有解析解，是試出來看結果，
這也是為什麼 archive 的資料夾名稱就是當年試過的值，`(backtilted 020 -20)`。
程式只是讓「試」變快，並把當前套用的旋轉標清楚。選哪個面、轉幾度，仍然是使用者的判斷。

### 軸被轉去哪

把實測的軸用同一個旋轉轉過去，畫在回轉後的圖上，是**空心圈**，並用虛線弧連到星形。
理由很簡單：單看一張回轉後的圖，你看不到「傾轉」這件事，
軸只是換了個位置，紙上沒有任何東西告訴你它原本在哪。

⚠️ **圈和星不一定重合，而且會不會重合跟方法有關。**

- **S4MIN 精確等變**。S₄ 是旋轉不變的，所以它的最小值跟著資料轉。
  推論：回轉**不可能**改變 S4MIN 的 Φ 與 S₄，傾轉檢驗的全部內容就是「軸最後落在哪」。
- **INVDIR 不等變**。式 (14) 把張量的**對角線**釘在**地理座標**的
  cos ψ、cos(ψ+2π/3)、cos(ψ+4π/3)。資料一轉，那個四參數族就變成另一個族，
  對回轉後的資料重算，搜的是別的地方。

**這是 Angelier 方法本身的性質，不是這個重建版的 bug。**
用原程式自己跑的十四組 archive 回轉配對驗證（Kabsch 擬合 <2° 確認同一批資料）：
把母站的軸轉過去 vs 檔案裡回轉後那次的結果，
中位差 σ₁ **10.4°**、σ₂ **24.3°**、σ₃ **23.6°**，最大到 88.7°。
最大的幾筆多半落在 Φ 接近 0 或 1、兩根軸近簡併的站，但不是全部：
0214-5（13 筆、Φ 0.46 → 0.72）σ₁ 仍差 19.8°、σ₃ 差 22.8°。

**這對論文的意思**：只用 INVDIR 的話，「回轉前後軸變了」有一部分是在讀參數化、不是讀地質，
所以「回轉後 σ₁₂₃ 回到水平／垂直」本身不能當證據。
乾淨的判準要看 S4MIN（它的軸可以證明只是純旋轉），INVDIR 留作與舊 run 的連續性對照。
視窗會把兩者並列並印出差距。測試鎖在 `tests/test_backtilt.py`。

### 「轉回水平」不會自動就是對的

那個做法預設斷層早於傾轉。如果斷層是**在傾轉過程中**形成的，
只有一部分傾轉發生在它們之後，把全部轉回去就是過度回轉，
會得到一個從來不存在的應力張量。

**Tilt test** 把旋轉從 0 掃到 125 %，每一步都反演，同時畫兩個診斷量：

| 診斷量 | 說明 |
|---|---|
| 平均 ANG、RUP、S₄ | 單一張量解釋資料的好壞。最佳值落在 100 % 附近，表示斷層早於傾轉 |
| Andersonian 失配 | 90° 減去最陡那根軸的傾沒，所以 0 就是一垂直兩水平。同時判斷體制：σ₁ 垂直為正斷、σ₂ 為平移、σ₃ 為逆衝 |

最佳解落在遠低於完全回轉的地方，就是同傾轉斷層的樣子，程式會直接講。
兩個判準若差超過旋轉量的 20 %，也會講，因為那個分歧要先解釋清楚，兩個才都能信。
兩者都不是證明，是診斷。

實例：0404-4C-2 對一個假造的參考面，兩個判準都隨回轉**變差**，
最佳落在 10 %，Andersonian 失配從 40.8° 升到 49.2°。
把那個面轉回水平，會安靜地得到一個比原始資料還差的答案。

## 畫圖：HPGL 才是畫風的標準答案

每個 run 資料夾裡都有一個 `HPGL`，是純文字的繪圖機向量指令。
它不是「對程式畫了什麼的描述」，它**就是**程式逐筆畫出來的那張圖。
所以這裡的畫風是量它量出來的，不是看論文插圖猜的。

- **投影是等面積 Schmidt**。這是測出來的，不是假設的：
  大圓在等角投影下是正圓弧，在等面積下不是。
  實測圓弧擬合殘差 0.0044 / 0.0062 / 0.0010，等面積的預測是 0.0040 / 0.0055 / 0.0007，等角應該是 0。
- **星形**：σ₁ 五角、σ₂ 四角（斜置）、σ₃ 三角。大小不是固定的：
  `size = 0.1004 + 0.0928·(0.5 − Φ)·λᵢ`（21 張圖 63 顆星擬合，rms 0.00063）。
  Φ = 0.5 時三顆等大，所以大小順序在 Φ = 0.5 兩側會翻轉。
- **擦痕符號是剪切對偶，不是單支箭頭**：實心圓點加兩支平行軸線，各自側偏 0.024，
  所以圖上呈 Z 字形。頭部隨信心度：S 完全無頭、P 每端一條單邊倒鉤、C 每端一個兩段式細長頭。
  倒鉤與側偏在哪一側是 `sign(滑動 · 走向)`，89 筆全中；用運動字母判只有 83 筆對。
- **粗箭頭**在圓外，沿 σ₁ 向內、σ₃ 向外，傾沒超過 45° 的那一對就不畫。
- ⚠️ **外框不是對稱於投影網中心**。93 個 archive HPGL 完全一致：
  x −1.2527 到 1.2547、y **−1.3047 到 1.4585**（單位＝基準圓半徑），標註全是固定欄左對齊。
  這裡先前假設對稱，底邊低了 0.15。

**HPGL 匯出**的做法是讓 `pytensor.penrec` 假扮成 matplotlib Axes，
重播 `plot.plot_site` 本身，所以檔案裡有的東西跟圖上完全一樣，沒有第二份實作可以漂移。
輸出落在 archive 自己的框上（400-5420 × 396-5928 繪圖機單位），由 `tests/test_ui_contract.py` 把關。

## 舊檔讀寫

舊 run 直接讀回來；反演之後，pyTENSOR 會用原格式寫回 `INFO1` 與 `MOHR1`，並顯示在介面上。

`tests/test_report.py` 用記錄的解重新產生兩個檔，跟原檔對拆：
**版面**（比對每個數字的欄位跨距）與**數值**分開檢查。
目前狀態：兩站都是 0 版面差異、0 數值差異。

刻意保留的兩處差異：

- 橫幅寫 pyTENSOR，不冒充 TENSOR 5.45。機器要讀的部分（定寬表格、`03` 結果行）維持原樣，
  所以檔案仍然可以用 `pytensor.tensorfile` 讀回去。
- `RMU` 在正向應力接近零時可以差幾十 %，因為它是比值。其他每一欄都在 ±1 之內。

兩個很容易寫錯的版面細節：

- 兩個旗標欄寬 2 字元、**右**對齊，所以 `!!` 貼齊數字，單一 `!` 前面要補一個空格。
- 標題 `<75` 與 `<45` 那兩欄，是**同一個統計量取通過門檻的子集**，不是重複前一欄。
  0406-7 全部 29 筆的平均 ANG 是 21，低於 45 的 28 筆是 15，差的就是那筆 174° 的離群值。

## 檔案格式

用資料檔、`MOHR1`、`INFO1`、`Mesure_key.txt` 互相對照解出來，兩站 35 筆驗證過。
定寬 ASCII，一個 run 一個資料夾，**輸入與輸出在同一個檔**：

| 位置 | 內容 |
|---|---|
| `[0:2]` | 第一位＝擦痕信心度 **1=C、2=P、3=S**；第二位＝rake 從走向線哪一端量起（1＝正規端，即傾向−90；2＝另一端，此時存的是 180 − 輸入值） |
| `[2:5]` | **真正的傾向**，已經含象限字母的判斷，所以 `SN 174 74E` 是 84 不是 264 |
| `[5:7]` | 傾角 |
| `[7:10]` | **rake（pitch）**，從（傾向−90）那一端量起 |
| `[47:61]` | 當年打進去的原始欄位；最後一欄可能是 rake（`62N`）也可能是 trend（`124`） |

兩個踩過的坑：

- ⚠️ **滑動方向 = rake + 180°**。直接用欄位值會讓 σ₁ 與 σ₃ 對調。
- ⚠️ 如果一站所有面的傾角都在 85-89°，`sin(plunge) = sin(rake)·sin(dip)` 會讓 rake 與 plunge 差不到 1°，
  於是 `[7:10]` 看起來像 plunge。它不是。用傾角 42-89° 的 0406-7 才能定案。

`03` 結果行同樣是定寬（trend 5 字元、plunge 4 字元），中間沒有分隔符。
用空白切或用數字正規表示式抓，都會黏成亂碼。

## 驗證

七個測試檔全過。有 archive 就讀，沒有就 skip，不會 fail。

| 測試 | 鎖住什麼 |
|---|---|
| `test_replication.py` | 整條流程對上原程式自己的輸出 |
| `test_report.py` | INFO1 / MOHR1 的版面與數值 |
| `test_entry.py` | 打字輸入對上檔案裡存的值，35 筆 |
| `test_rotate.py` | 回轉慣例，對七組 archive 配對 |
| `test_backtilt.py` | S4MIN 等變、INVDIR 不等變 |
| `test_ui_contract.py` | 介面用到的東西都存在；HPGL 匯出 |
| `test_gui_logic.py` | 介面裡不牽涉 Qt 的那一半 |

0406-7（29 筆，傾角 42-89°）是把演算法釘死的那一站：

```
前向模型 vs MOHR1        max |SIGMN| 0.001  |TAU| 0.001  |TAUST| 0.001
                         max |RUP|   0.099  |ANG| 0.113
INVDIR 流程              sigma1 0.047 度   sigma2 0.020   sigma3 0.032
                         Phi 0.138（檔案 0.138）
                         平均 ANG 20.898（20.900）  平均 RUP 54.097（54.100）
                         印出的 LAMBDA 0.682（0.680）
```

L12（六個近平行、近垂直的面）是簡併站，重現得比較鬆：軸約 1°、平均 RUP 在 0.6 % 內。
容差是**逐站設定**來反映這件事，不是全域放寬。

⚠️ 測試裡不會建立任何 Qt 物件：從自動化 shell 啟動 QApplication 會彈出平台外掛錯誤框然後退出。
測試改成驗證介面與函式庫之間的契約。

## 效能

ψ 掃描原本每趟呼叫純量常式 4000 次，上面再疊 120 步三分搜尋，
archive LAMBDA 又把整套重跑約九十次。而其實幾乎沒有一步跟 ψ 有關：
只有對角線帶 ψ，而且是線性的，所以 3×3 normal matrix 是資料集的常數，
每個 ψ 只剩一次對同一個分解的回代。PSIDIR 與 S4MIN 的起點掃描用特徵座標系同樣化簡。

0406-7（29 筆）實測：

| | 之前 | 現在 |
|---|---|---|
| INVDIR 2 趟 | 0.975 s | 0.004 s |
| S4MIN 400 起點 | 0.208 s | 0.052 s |
| archive LAMBDA | 6.775 s | 0.063 s |

與被取代的常式差 1e-13。

## 參考資料集

測試與推導腳本會讀原程式的真實輸出。那是**未發表的野外資料**，所以路徑不寫死在原始碼裡：

```
set PYTENSOR_ARCHIVE=<放 TENSOR run 資料夾的那個目錄>
```

沒設就 skip，不會 fail。資料本身不隨這個 repo 發布。

## 專案結構

```
pytensor/           函式庫
  core              幾何、準則、品質估計量
  invdir            INVDIR，Angelier 的參數化與兩段流程
  modern            S4MIN，同一準則的精確最小值
  tensorfile        讀舊站檔
  report            寫 INFO1 與 MOHR1
  entry             解析打字輸入
  plot              Angelier 畫風的投影網
  hpgl              繪圖機檔的讀與寫
  penrec            把畫圖程式重播成繪圖機向量
  rotate            旋轉與回轉慣例
  tilt              Andersonian 失配與逐步傾轉掃描
  backtilt          回轉視窗
  tiltui            傾轉檢驗對話框
  splash, about     開啟畫面與 About
  retro, ui_style   1991 模式與一般樣式表
  archive           參考資料集的位置
pyTENSOR.py         桌面介面
tests/              對 archive 的回歸測試
research/           每個常數是怎麼量出來的，該夾有自己的 README
```

## 更新紀錄

**0.2.0**

- 回轉獨立成一個視窗，實測與回轉左右並列，並把實測軸經同一旋轉畫成空心圈
- 確立並用測試鎖住：INVDIR 不是旋轉等變的、S4MIN 是；用原程式的 14 組 archive 配對驗證
- HPGL 匯出改成重播真正的畫圖程式，整張圖都會進檔案，不再只有基準圓與斷層面
- 修正外框（不對稱）與標註錨點，螢幕與所有匯出一起修
- ψ 掃描全部向量化，INVERT 從幾秒降到毫秒
- 介面：常駐一行說明現在畫的是什麼、資料改過但還沒重算會顯示過期標記、每個面板有標題、側欄分段加細線

**0.1.0**

- 準則、品質估計量與前向模型，35 筆驗證
- INVDIR ＋ PSIDIR，以及 S4MIN
- 舊檔讀取、原格式的 INFO1 與 MOHR1 輸出
- 量自 archive HPGL 的 Angelier 畫風投影網
- 桌面介面、1991 模式

## 還沒做

- `[0:2]` 代碼表已解出但還沒對過手冊
- 寫回 TENSOR 格式的資料檔
- PSID、R4DT、NDA 這幾個 Angelier 的其他方法，刻意還沒開始
- 授權條款

## 授權與致謝

方法是 Jacques Angelier 的。這是依他發表的論文、加上對他程式輸出檔的量測所做的獨立重寫，
沒有從原執行檔取用任何程式碼。

開啟畫面是 Angelier 自己畫的台灣弧陸碰撞塊體圖。
他把玉里附近的地震震源機制當作「把這個方法用在地震學資料上」的示範例（1994, fig. 4.44）。
那是已發表的圖，**沒有**放進這個 repo，所以新 clone 下來不會有開啟畫面，
藏在它後面的彩蛋也開不了。把 `Taiwan Tectonic Map.jpg` 放回專案根目錄兩者就會回來。

維護者：Chi-Hsiu Pang。授權尚未選定，在加入之前請視為保留所有權利。
