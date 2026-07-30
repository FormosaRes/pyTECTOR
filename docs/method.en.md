# pyTECTOR: the method in detail

The criterion, Angelier's parametrisation and its consequences, in more depth
than the README carries. Everything here was either read out of the published
papers or measured off the original program's own output; where a number is
quoted, the script that produced it is in `research/`.

Back to the [README](../README.md).

---

## When PSIDIR relabels the axes

INVDIR's own axes come from an unnormalised tensor, so its σ₁/σ₂/σ₃ labelling
is not automatically right. PSIDIR's job is to check that and correct it where
necessary, but it does not always change anything, and which case a given run
falls into determines which set of numbers should be read as the answer.

On the frozen INVDIR axes, the normalised tensor's three eigenvalues are
cos ψ, cos(ψ+120°), cos(ψ+240°), for whatever ψ the PSIDIR scan settles on.
Those three values come out **in descending order, matching INVDIR's own
σ₁ > σ₂ > σ₃ slots, only while ψ sits in the last 60° of the turn, 300° to
360°.** Every other 60° sector belongs to one of the other five orderings.

- **ψ lands in [300°, 360°) → `AXES OK !`.** INVDIR's own σ₁/σ₂/σ₃ labels
  stand. Φ still moves to PSIDIR's value, as it always does, but the axes it
  describes are those INVDIR already reported, so the solution reads the same
  whether it is attributed to INVDIR or to PSIDIR.
- **ψ lands anywhere else → `PERMUTATION`.** σ₁/σ₂/σ₃ are reassigned to
  different frozen directions than INVDIR's own labels. INVDIR's printed Φ and
  the final PSIDIR Φ then describe genuinely different axis assignments rather
  than a small correction to the same one, and this is the case in which
  PSIDIR's numbers, not INVDIR's, must be read as the result. pyTECTOR flags
  it wherever it occurs: the back-tilt window's summary prints
  `PSIDIR ...: sigma1/2/3 are NOT INVDIR's labels`, and the underlying flag is
  `permutation=True, psidir_flag='PERMUTATION'` (see
  `pytector.invdir.axis_order`).

Verified against the archive: on the 56 runs pyTECTOR reproduces to within 3°
on σ₁, this 300-360° rule predicts the recorded flag 56 times out of 56. The
six remaining runs are all cases whose INVDIR solution is not itself
reproduced, so they test the reproduction rather than the rule.

Angelier's own account (Appendix IV) is that this repairs "artificial
σ₁/σ₃ permutations" the unnormalised INVDIR pass produces "on poorly varied
data", that is, sites where the fault population does not constrain the stress
tensor tightly enough for the unnormalised form to place the axes in the
correct slots unaided. A permutation is therefore not an indication of a poor
solution; it is PSIDIR performing the function Angelier designed it for.

## Reproducing a specific historical run

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

---

## What λ is, in Angelier's own words

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

## The iteration does not converge, and stopping early is the point

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

## Reading convergence off an INFO1

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

## How far apart do they end up

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

---

## Where did the axes go

The measured axes put through the same rotation are drawn on the restored
diagram as **open rings**, with a dashed arc to the star. A back-tilted diagram
on its own does not convey the tilting itself: the axes are simply in a
different position, and nothing on the page indicates where they came from.

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

## Restoring to horizontal is not automatically right

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

---

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
