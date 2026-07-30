<div align="center">

![pyTECTOR](docs/img/banner.png)

**Angelier 古應力反演的 Python 重建版，對應 TENSOR 5.45 (jan91)**

照論文重寫，不反譯執行檔；原程式 90 個 run 重現 85 個；回轉與 tilt test；逐筆影響力診斷；INFO1／MOHR1／HPGL 原格式輸出

[![TENSOR](https://img.shields.io/badge/TENSOR%205.45-reconstructed-1f6feb)](docs/mesure_oracle.md)
[![version](https://img.shields.io/badge/version-0.3.0-brightgreen)](pyproject.toml)
[![python](https://img.shields.io/badge/python-3.x-555)](#quick-start)
[![tests](https://img.shields.io/badge/tests-11%20suites%20passing-2ea44f)](tests/)
[![archive](https://img.shields.io/badge/archive-85%2F90%20runs%20reproduced-2ea44f)](tests/test_replication.py)
[![licence](https://img.shields.io/badge/licence-MIT-8250df)](LICENSE)

[使用手冊 中文](docs/manual.zh.md) · [English manual](docs/manual.en.md) · [原程式對話全文](docs/mesure_oracle.md) · [English below](#english)

</div>

---

> A Python reconstruction of Jacques Angelier's **TENSOR** palaeostress
> inversion program, written from the published method rather than by
> disassembling the original 16-bit DOS binary, and checked against
> ninety-two runs the original itself produced.

Angelier 的直接反演法從一組斷層面與擦痕線理，解出最能解釋它們的簡化應力張量，
也就是三個主應力方向與形狀比 Φ。`Tensor.exe` 自 1991 年起執行這項計算，
大量已發表的古應力研究皆建立在其結果之上。

pyTECTOR 執行相同的運算、讀寫相同的檔案、繪製相同的圖，並補上原程式沒有的部分：
**回轉（back-tilt）**、**tilt test**，以及**把同一個準則真正最小化**的第二種跑法，
用來分辨一個答案有多少來自方法本身、多少來自資料。

名稱取自 **TECTOR**，即 Angelier 為這套程式的構造方位資料庫所取的名稱，
印在它產生的每一份 INFO1 上。

---

## 📸 長什麼樣

| 兩種跑法並列 | 回轉與 tilt test |
|---|---|
| ![methods](docs/img/methods.png) | ![back-tilt](docs/img/backtilt.png) |

<div align="center"><img src="docs/img/mohr.png" width="420" alt="Mohr diagram"></div>

> 以上圖片皆由 repo 內的公開 fixture `tests/fixtures/L12-2/` 產生，
> 那是一個合成站點，不是野外資料，任何人 clone 這個 repo 都能重製出同一張圖。

---

## ✨ 核心特色

- **照論文重寫，不反譯執行檔。** 原始執行檔是 16-bit MZ 格式，含 5252 個
  relocation、無符號表，疑似含 overlay 與軟體浮點模擬。演算法本身在
  Angelier (1984, 1990) 中已完整發表，依論文重建比逆向二進位快上一個量級。
- **對原程式逐位驗證。** 以 archive 中 92 個 run 作為回歸測試集：前向量
  （SIGMN／TAU／TAUST／RUP／ANG）逐筆吻合至檔案精度；以各站記錄的 pass 數與
  LAMBDA 重跑後，**85/90 站三軸角度差小於 3°**。
- **INVDIR／S4MIN 兩種跑法並列。** `INVDIR` 是 Angelier 原方法、原程式的跑法；
  `S4MIN` 是同一準則的精確最小值。兩者皆非「真應力」：υ 準則本身有系統性偏差，
  即使餵入零雜訊的理想合成資料，仍與真實張量相差約 4°。兩種跑法並列，
  是為了呈現差異所在，而非在其中擇一。
- **回轉與 tilt test，原程式沒有的功能。** 角度以拉桿試誤調整，σ₁σ₂σ₃ 即時重算；
  空心圈標示實測軸經同一旋轉後的位置，星形是重新反演的答案。對 INVDIR 而言，
  兩者的差距反映的是方法本身的性質，而非地質意義（14 組 archive 配對，
  實測中位數 σ₁ 差 10.4°）。
- **逐筆影響力診斷。** 「擬合誤差大」與「決定了答案」是兩件不同的事。程式對每筆
  資料做 leave-one-out 重新反演，並提供**剔除後殘差** ANG\*／RUP\*：
  以不含該筆資料的解去衡量它，不受該筆資料自身拉力的影響。
- **排除資訊完整揭露。** 產生「全部資料」與「剔除後」兩個答案並列的區塊，
  連同軸移動的角度，一併寫入匯出的 INFO1。
- **原格式輸出。** INFO1／MOHR1 與原始檔案逐位元組相同（測試逐欄位比對）；
  HPGL 匯出是重播原本的繪圖程式本身，而非另一套獨立實作。
- **Session 存檔。** 記錄、參考面、設定、回轉、已計算的解存成單一 JSON 檔；
  只保存張量本身，其餘數值於載入時重新計算，因此存檔中的 Φ 不可能與存檔中的
  張量互相矛盾。

---

# English

## What this is

Angelier's direct inversion method takes a set of measured fault planes and
slickenside lineations and returns the reduced stress tensor that best explains
them: the three principal stress directions and the shape ratio Φ. His program
`Tensor.exe` did this from 1991 onwards and a great deal of published
palaeostress work rests on it.

pyTECTOR performs the same arithmetic, reads and writes the same files, draws the
same diagrams, and adds the parts the original never had: back-tilting, a tilt
test, and a second run that minimises the same criterion properly, so that how
much of an answer comes from the method rather than the data can be assessed.

## Why not decompile

`Tensor.exe` is a 208 KB 16-bit MS-DOS binary with 5252 relocations, no symbol
table, probably Turbo Pascal, with overlays and most likely software floating
point. It will not run on 64-bit Windows, which dropped NTVDM. Decompiling it is
not a viable route, for the usual reasons: compilation discarded the names, the
types and the structure, and 16-bit segmented addressing makes pointers
impossible to resolve statically.

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

## Why the name

Angelier's papers never name a program: the 1984, 1989 and 1990 texts speak
only of "the new direct inversion method". The binary names itself, in every
INFO1 it wrote:

```
Progr. TENSOR, 1975-1991,  version 5.45, jan91
Copyright 1987,1988,1989,1990,1991 J. Angelier

*** DATA BASE FOR TECTONIC ORIENTATIONS "TECTOR" ***
```

"TENSOR" would have been the natural tribute, but the name is taken twice
over: in the palaeostress community it now means Damien Delvaux's unrelated
TENSOR / Win-Tensor program (Delvaux & Sperner 2003), and on PyPI `pytensor`
is PyMC's actively maintained array library, so the import name would collide
with real installations. **TECTOR** is the other name on that banner, it is
uniquely Angelier's, and nothing else uses it. Hence pyTECTOR.

## Quick start

One-click on Windows: download the repository, double-click **`install.bat`**.
It finds a Python (Anaconda first), installs numpy, scipy, matplotlib and
PyQt5, and puts a pyTECTOR shortcut on the desktop. Alternatively
`pip install .` (or `pip install git+https://github.com/FormosaRes/pyTECTOR`)
installs a `pytector` command.

```
pyTECTOR.bat                           desktop interface
python demo_report.py [site file]      invert an old site, print INFO1 + MOHR1
python run_batch.py [root] [out.csv]   both runs over a whole folder tree
```

The full interface walkthrough, control by control, is in
**[docs/manual.en.md](docs/manual.en.md)**.

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

`pytector.invdir`, code `INVD`, as TENSOR 5.45 runs it.

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

Two points are relevant to any reimplementation. υ² is *quadratic* in (α, β, γ)
at fixed ψ, so the inner minimisation is an exact 3×3 linear solve; Angelier's
Appendix I and II perform that expansion by hand, and the polynomials are
regenerated numerically here because the appendix is illegible in the available
scan. Second, ψ must be scanned over the whole circle: restricting it to
[0, π/3] yields Φ = 0 and the wrong axes, because the minimum often sits near
ψ = 336-353°.

### When PSIDIR relabels the axes

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

`pytector.modern`, code `S4MN`, the exact minimum of the same S₄.

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
matplotlib Axes (`pytector.penrec`), so the file carries exactly what the figure
carries and there is no second drawing routine to drift. Output lands on the
archive's own frame, 400 to 5420 by 396 to 5928 plotter units, which
`tests/test_ui_contract.py` checks.

## Reading and writing the old files

Old runs go straight back in, and after inverting, pyTECTOR writes `INFO1` and
`MOHR1` back out in the original layout and shows both in the interface.

`tests/test_report.py` regenerates both files for L12 and 0406-7 from the
recorded solutions and diffs them against the originals. It checks **layout**,
by comparing the column spans of every number, and **values**, numerically.
Current status: 0 layout and 0 value mismatches on both sites.

Two deliberate departures:

- the banner names pyTECTOR instead of claiming to be TENSOR 5.45. Everything a
  reader parses, the fixed-width table and the `03` result line, keeps the
  original layout, so the files still round-trip through `pytector.tensorfile`.
- `RMU` can differ by tens of per cent when the normal stress is near zero,
  because it is a ratio. Every other column agrees within 1.

Two layout details are worth recording, both easily implemented incorrectly:

- the two flag fields are two characters wide and **right** aligned, so `!!`
  abuts the number while a single `!` is preceded by a space.
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

Two pitfalls, both encountered during development:

- **The movement direction is rake + 180.** Using the stored value directly
  swaps σ₁ and σ₃.
- On a site where every plane dips 85-89°, `sin(plunge) = sin(rake)·sin(dip)`
  makes rake and plunge agree to within a degree, so `[7:10]` appears to be a
  plunge. It is not. Site 0406-7, with dips of 42-89°, resolves the ambiguity.

The `03` result line is also fixed width, trend 5 characters and plunge 4,
packed with no separators. Splitting it on whitespace or with a numeric regex
produces invalid values.

## Verification

Eleven test files, all passing. They read the original archive when it is
available and skip rather than fail when it is not.

| test | what it pins |
|---|---|
| `test_replication.py` | the whole pipeline against the original program's own output |
| `test_fixture.py` | the whole pipeline against the public fixture, no archive needed |
| `test_report.py` | INFO1 and MOHR1 layout and values |
| `test_entry.py` | typed records against the stored ones, 35 records |
| `test_rotate.py` | the back-tilt convention, against seven archive pairs |
| `test_backtilt.py` | S4MIN is equivariant, INVDIR is not |
| `test_diagnose.py` | the leave-one-out influence diagnostics |
| `test_session.py` | a session round-trips without changing any answer |
| `test_ui_contract.py` | everything the GUI reaches for exists; the HPGL export |
| `test_gui_logic.py` | the non-Qt half of the interface |
| `test_import.py` | the package imports cleanly |

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
set PYTECTOR_ARCHIVE=<folder holding the TENSOR run folders>
```

Without it, those tests skip rather than fail. The data itself is not
distributed with this repository.

## Layout

```
pytector/           the library
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
pyTECTOR.py         desktop interface
tests/              regression against the archive
research/           how every constant was measured, see its own README
```

## Licence, credits and use

The code in this repository is released under the **MIT Licence**; see
[LICENSE](LICENSE). If it contributes to published work, a citation of this
repository alongside Angelier's own papers is appreciated but not required.

Three things the licence does not cover, because they are not this project's to
license:

- **The method** is Jacques Angelier's, set out in the papers cited above. This
  is an independent reimplementation from those papers, plus measurements taken
  from output files his program wrote; no code was taken from the original
  binary.
- **The reference archive** is unpublished field data. It is not distributed
  here and is not covered by this licence (see *The reference archive*).
- **The opening screen** is Angelier's own block diagram of the Taiwan
  arc-continent collision. He used earthquake focal mechanisms from near Yuli as
  the worked example of applying this method to seismological data (1994,
  fig. 4.44). That image is a published figure and is **not** committed here, so
  a fresh clone starts without an opening screen and without the easter egg
  behind it. Placing `Taiwan Tectonic Map.jpg` in the repository root restores
  both, for local use only.

Maintainer: Chi-Hsiu Pang.

## Changelog

**0.3.0**

- **released under the MIT Licence**, which settles the one item that had been
  blocking public use (see *Licence, credits and use* for what the licence does
  and does not cover)
- renamed pyTENSOR → **pyTECTOR**, after Angelier's own data-base name, to
  stay clear of Delvaux's TENSOR / Win-Tensor and of PyMC's `pytensor`
  package (see *Why the name*). `PYTENSOR_ARCHIVE` still works as a legacy
  spelling of `PYTECTOR_ARCHIVE`.
- one-click setup: `install.bat` installs the dependencies and puts a desktop
  shortcut up; `pip install .` works too and installs a `pytector` command
- MESURE 5.51 and TENSOR 5.45 run on the original machine as oracles;
  docs/mesure_oracle.md transcribes both sessions
- **a public end-to-end fixture**: tests/fixtures/L12-2 is a complete run of
  the original programs on a synthetic site, and tests/test_fixture.py checks
  the whole pipeline against it with no archive needed, axes to 0.05 degrees

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

- writing TENSOR-format data files back out (the site-header fields are now
  known, see [docs/mesure_oracle.md](docs/mesure_oracle.md))
- R4DT / R4DS / R2DT / R2DS, Angelier's iterative-search methods,
  deliberately not started (TENSOR's own help documents them, see
  docs/mesure_oracle.md)

---

# 中文

## 這是什麼

Angelier 的直接反演法從一組實測斷層面與擦痕線理，解出最能解釋它們的簡化應力張量，
也就是三個主應力方向與形狀比 Φ。他的程式 `Tensor.exe` 自 1991 年起執行這項計算，
大量已發表的古應力研究建立在其結果之上。

pyTECTOR 執行同一套運算、讀寫同一批檔案、繪製同一種圖，
並補上原程式沒有的部分：回轉（back-tilting）、傾轉檢驗，
以及第二種將同一準則真正最小化的跑法，用以分辨一個答案有多少來自方法、多少來自資料。

## 為什麼不反譯

`Tensor.exe` 是 208 KB 的 16 位元 MS-DOS 執行檔，含 5252 個重定位項、無符號表、
疑似以 Turbo Pascal 編譯、含 overlay，浮點運算很可能採軟體模擬。
64 位元 Windows 已移除 NTVDM，因此它無法執行。
反譯不可行的理由相當常見：編譯過程已移除名稱、型別與結構，
而 16 位元分段定址使指標無法靜態解析。

演算法本身在論文中已完整發表（見上方英文段落所列三篇）。
因此本專案的工作集中於研讀論文，以及**量測原程式自身產生的輸出檔案**，
以補足論文未載明的部分。

## 為什麼叫 pyTECTOR

Angelier 的論文全篇未為程式命名，只稱之為「the new direct inversion
method」。名稱出自程式自身，印在它產生的每一份 INFO1 上：

```
Progr. TENSOR, 1975-1991,  version 5.45, jan91
Copyright 1987,1988,1989,1990,1991 J. Angelier

*** DATA BASE FOR TECTONIC ORIENTATIONS "TECTOR" ***
```

最直接的致敬名稱應為 TENSOR，但該名稱已有兩處衝突：在古應力領域中，
「the TENSOR program」現指 Delvaux 的 TENSOR／Win-Tensor（Delvaux & Sperner 2003），
與 Angelier 無關；而 PyPI 上的 `pytensor` 是 PyMC 團隊持續維護的張量運算庫，
import 名稱會與實際安裝環境衝突。橫幅上的另一個名稱 **TECTOR** 同樣出自 Angelier，
且目前無其他專案使用，故定名為 pyTECTOR。

## 安裝與執行

Windows 一鍵安裝：下載整個 repo 後雙擊 **`install.bat`**。
該腳本會自動尋找 Python（優先使用 Anaconda）、安裝 numpy／scipy／matplotlib／PyQt5，
並在桌面建立 pyTECTOR 捷徑。亦可使用
`pip install .`（或 `pip install git+https://github.com/FormosaRes/pyTECTOR`），
安裝後會提供 `pytector` 指令。

```
pyTECTOR.bat                           桌面介面
python demo_report.py [站檔]           反演一個舊站，印出 INFO1 + MOHR1
python run_batch.py [根目錄] [out.csv] 對整棵資料夾跑兩種方法
```

逐項功能的完整操作說明見 **[docs/manual.zh.md](docs/manual.zh.md)**。

輸入分為四個欄位，輸入後即顯示於投影網上：

```
CS - 122 - 87W - 124
|    |     |     |
|    |     |     +-- rake ＋象限（62N），或直接給 trend（124）
|    |     +-------- 傾角＋象限
|    +-------------- 走向
+------------------- 信心度 C/P/S ＋ 運動方式 I/N/S/D
```

亦可直接開啟舊有的 run：指向那個**沒有副檔名、檔名等於站名**的資料檔（例如 `L12`），
斷層資料與 INFO1 會一併載入。

## 準則

- σ = **T**·n（式 3）；τ = σ − (n·σ)n（式 4-5）
- **υ² = λ² + |τ|² − 2λ(s·σ)**（式 A1），最小化 **S₄ = Συ²**（式 13）
- RUP = 100·|υ|/(√3/2)，範圍 0-200 %；ANG = s 與 τ 的夾角，0-180°
- 張量正規化採**特徵值平方和 = 3/2**（式 A16），**並非**固定 σ₁ − σ₃。
  兩種定義僅在 Φ = 0.5 時相同，而此準則不具尺度不變性，故此差異會改變結果。

**此準則本身帶有系統性偏差，並非任何程式的錯誤。**
υ 同時要求「預測剪應力方向與實測滑動一致」與「剪應力大小接近 λ」，
因此即使餵入零雜訊的理想 Bott 合成資料，結果仍與真實張量相差約 4°，
並系統性地偏向使斷層承受高剪應力的方位。
純角度準則 F2 在同一批資料上的誤差為 0.00°。
這即是 TectonicsFP 等軟體與 Angelier 計算結果不一致的根本原因。

## 兩種跑法：INVDIR 與 S4MIN

兩者以其實質內容命名，避免使用暗示優劣的代號。基於上述理由，**兩者皆非「真應力」**。

**INVDIR**（`pytector.invdir`，代碼 `INVD`）為 Angelier 原方法、原程式的跑法，
採用他自己的 (α, β, γ, ψ) 參數化（式 14 / A2）。此張量**未經正規化**，
其最大剪應力隨解的移動而改變，這正是 λ 必須逐趟迭代的原因，
也是 INFO1 所印出的 `LAMBDA` 小於 √3/2 的原因。流程分兩段：

1. **INVDIR 第 k 趟**：在當前 λ 下最小化 S₄，隨後將 λ 更新為該解的 taumax。
   INFO1 印出的 `(NO k)` **為迭代趟數**，而非「在兩個解之間擇一」。
2. **PSIDIR**：將軸凍結於 INVDIR 的結果，改用正規化的 A16 形式、λ = √3/2，
   對 ψ **整圈**重新最小化。此步驟決定 Φ，並修正前一階段可能產生的
   σ₁/σ₃ 人為對調。

兩項實作要點：固定 ψ 時 υ² 對 (α, β, γ) 為二次式，內層即精確的 3×3 線性求解，
無須轉抄附錄中的多項式（現有掃描檔的附錄辨識度不足，此處改以數值方式重新生成）。
另外 ψ 必須掃描整圈：若限制於 [0, π/3] 會得到 Φ = 0 的錯誤結果，
因為最小值常落在 ψ ≈ 336-353°。

### PSIDIR 什麼時候會把軸重新貼標籤

INVDIR 的軸來自未正規化的張量，因此它為 σ₁/σ₂/σ₃ 指派的標籤不保證正確。
PSIDIR 的職責就是檢查並在必要時修正；但它並非每次都會實際改動任何東西，
而一個 run 屬於哪一種情況，決定了最終應該把哪一組數字當成答案。

在凍結的 INVDIR 軸上，正規化張量的三個特徵值為 cos ψ、cos(ψ+120°)、cos(ψ+240°)，
其中 ψ 取 PSIDIR 掃描收斂到的值。**這三個值只有在 ψ 落在整圈的最後 60°
（300° 到 360°）時才依大小排序，也就是與 INVDIR 原本設定的
σ₁ > σ₂ > σ₃ 順序一致。** 其餘每個 60° 區間各對應另外五種排列之一。

- **ψ 落在 [300°, 360°) → `AXES OK !`**。INVDIR 的 σ₁/σ₂/σ₃ 標籤維持不變。
  Φ 一律會換成 PSIDIR 計算的值，但該 Φ 所屬的軸仍是 INVDIR 原本報告的那一組，
  因此無論將此解歸給 INVDIR 或 PSIDIR，讀出來的都是同一組數字。
- **ψ 落在其他區間 → `PERMUTATION`**。σ₁/σ₂/σ₃ 被重新指派到與 INVDIR 標籤
  不同的凍結方向上。此時 INVDIR 印出的 Φ 與最終 PSIDIR 的 Φ 描述的是不同的
  軸指派，而非同一組軸上的細微修正；這正是必須改讀 PSIDIR 數值、
  不可再引用 INVDIR 數值的情況。pyTECTOR 遇到時一律標示：back-tilt 視窗的
  摘要會印出 `PSIDIR ...: sigma1/2/3 are NOT INVDIR's labels`，
  底層旗標為 `permutation=True`、`psidir_flag='PERMUTATION'`
  （見 `pytector.invdir.axis_order`）。

以 archive 驗證：在 pyTECTOR 重現至 σ₁ 誤差 3° 以內的 56 個 run 中，
上述「300-360°」規則 56 次全部正確預測了檔案記錄的旗標。
其餘 6 個未命中的 run，本身連 INVDIR 解都未能重現，
因此那 6 筆檢驗的是重現程度，而非這條規則。

Angelier 本人的說明（Appendix IV）指出，這一步用於修正「資料方位變化不足」時，
未正規化的 INVDIR 階段會產生的「人為 σ₁/σ₃ 對調」，也就是斷層資料本身
對應力張量的約束不足、未正規化形式無法自行將軸置於正確位置的那些站點。
因此出現 PERMUTATION 並不代表解有問題，而正是 PSIDIR 被設計出來要處理的情形。

**S4MIN**（`pytector.modern`，代碼 `S4MN`）為同一個 S₄ 的精確最小值。
其採特徵分解參數化，故 λ 依定義恆為 √3/2，無須迭代，且搜尋為全域搜尋。
它在**全部 92 個 archive 站**均取得更低的 S₄，無一例外
（L12 為 0.2360 對 0.3018；0406-7 為 7.3201 對 7.6198）。
換言之，原程式並未達到其自身準則的最小值，因為 λ 停在未收斂之處。

### λ 的定義：Angelier 的原始說明

以下內容並非逆向推測，而是他 1990 年論文 Section 4 與 Appendix IV 明確載明的。

λ 為**該張量所能產生的最大剪應力**。準則同時要求預測剪應力方向與實測滑動一致，
且其大小足以克服摩擦，λ 即為其目標值。

正規化的 A16 張量最大剪應力為常數，式 (14) 的張量則不然。原因他闡述得相當清楚：
對角線項帶有 ψ、非對角線項則無，因此**轉動應力軸會改變應力大小**。
他的結論是「軸的旋轉與應力大小在解析上不獨立」（1990, Section 4），
並指出若非如此，λ 便僅是一個常數，完全無須調整。

他的處理方式即為該迭代：執行數趟，每趟將 λ 更新為前一趟解的最大剪應力。
`(NO k)` 計數的正是此項。

**Angelier 亦明確指出 A16 形式更為理想**：採用該形式時 λ 的調整完全不必要、
λ 恆等於 √3/2；他未採用的原因是無法對該式求出解析解，同時註明
「沒有理由認為不可能」（Appendix IV）。
PSIDIR 這最後一步即是在收尾階段套用一次 A16 形式，他自述為「為求穩妥而增設」，
用以修正未正規化形式在資料方位變化不足時所產生的 σ₁/σ₃ 人為對調。

因此 **S4MIN 並非將 Angelier 的方法「現代化」，而正是他描述過、
意圖採用但當年無法實現的那個形式**，只是改以數值方法達成。
兩種跑法的差距源自 1990 年的解析限制，而非地質判斷上的分歧。

### λ 迭代不會收斂，提早停止即為其設計要點

Angelier 僅提及「數趟連續的決定」，未指明趟數，亦未主張收斂。以 archive 驗證：
**92 站中有 72 站會發散。** 0406-7 即為其中之一：若持續執行，
λ 由 0.866 → 1.009 → 1.115 → … 至第 200 趟達 1.1 × 10⁹，
S₄ 則由高於最小值 4 % 惡化至 78 %。L12 則會收斂，停在 λ = 2.2404、高於最小值 1.5 %。

其機制為正回饋：λ 增大即要求更大的剪應力，
求解器的因應方式是撐大未正規化的張量，而撐大後的張量最大剪應力又更大，
成為下一輪的 λ。

因此採**使用者自選趟數**而非「迭代至收斂」並非簡化處理；
在多數站點上，這是唯一能使結果保持有限的做法。
archive 的紀錄亦印證此點：62 站用 NO 1、25 站用 NO 2、五站用 3 至 5。

### 從 INFO1 判讀收斂程度

INFO1 印出三個數字，容易誤讀其中之一：

```
SOLUTION INVDIR (NO 1)  LAMBDA= 0.68     <- INVDIR 實際採用的 λ
SOLUTION PSIDIR         AXES OK !
LAMBDA= 0.87            TAUMAX= 0.80     <- PSIDIR：λ 依定義即為 √3/2，
                                            故所有檔案皆印出 0.87
```

`TAUMAX` 亦非 √3/2。對特徵值為 cos(ψ + k·2π/3) 的正規化張量，其最大剪應力為

```
taumax = 3 / (4·√(Φ² − Φ + 1))
```

其值自 Φ = 0 或 1 時的 0.75 至 Φ = 0.5 時的 0.866。此式與 87 個 archive run
吻合至 0.005 以內，同時也驗證了整體理解無誤。

**唯有第一個數字上升至與第三個數字相等，才代表收斂。** 在具備這兩個數字的
88 個 run 中，差距中位數為 0.160，且無任何一筆落在 0.02 以內：

| TAUMAX − LAMBDA | 站數 |
|---|---|
| ≤ 0.02（收斂） | 0 |
| 0.02 到 0.05 | 4 |
| 0.05 到 0.15 | 31 |
| 超過 0.15 | 53 |

此處並非批評當年的執行方式：迭代在多數站點上會發散，停在 NO 1 或 NO 2 是正確的判斷。
其意義在於**記錄下來的 λ 是一個停止點，而非一個解**，
而 **archive LAMBDA** 這項功能存在的目的即為重現該停止點。

由此可知 INVDIR 與 S4MIN 的差距**並非一個固定數字**，
而取決於站點以及當年所採用的趟數：

| | n ≥ 7（55 站） | n ≥ 15（10 站） |
|---|---|---|
| 受約束的軸 | 中位 8.9°、p90 20.8° | 中位 4.8°、最大 12.5° |
| \|ΔΦ\| | 中位 0.074 | 中位 0.065 |
| S₄ 高於最小值 | 中位 27 % | 中位 6 % |

0406-7 的 4 % 屬於表現較佳的一端。
須注意 S₄ 的百分比在 n 較小時是**不可靠的指標**：張量有四個未知數，
因此僅有四至五筆資料時全域最小值會趨近於零，任何與之相比的比值都會失去意義。
應據以判讀的是軸與軸之間的夾角。

**兩者的實際差距**：僅檢視資料真正約束住的那根軸（Φ < 0.5 看 σ₁、Φ > 0.5 看 σ₃），
在 n ≥ 7 的 55 站中，中位數 8.8°、p90 為 16.7°、最大 28.4°。
n ≥ 15 時收斂至中位數 4.8°、最大 12.5°，可見此分歧主要為**樣本數效應**，
而非方法本身的缺陷。
對照基準：INVD 自身在無雜訊合成資料上的偏差約 4°，
而 Angelier 引用的野外擦痕觀測誤差為 ±5-15°。
兩種跑法的差距落在此雜訊水準之內。

**實務建議**：以 **INVDIR 為主**，以維持與既有 run 及 TENSOR 系文獻的一致性；
並以 **S4MIN 作為穩健性檢驗**併陳。

## 回轉（back-tilting）

回轉功能有獨立的視窗，由工具列開啟。主視窗僅呈現實測資料、不做任何旋轉，
因此該處的投影網無須額外標註目前所處的方位。

回轉視窗會將資料轉至指定方位，並對前後兩個狀態各執行一次反演，左右並列呈現：
左側為 as measured、右側為 back-tilted，下方列出兩者的數值。設定旋轉的方式有三種：

| 方式 | 輸入 | 作用 |
|---|---|---|
| 參考面 | 走向 / 傾角，或以其 pole 給定 trend / plunge | 將該面轉回水平所需的旋轉 |
| 旋轉軸 | trend / plunge / 角度 | 直接套用，依右手定則 |
| 部分回轉 | 0 到 125 % | 上述任一方式的任意比例 |

斷層面法向與滑動向量會一併旋轉，因此 rake 與運動感亦隨之改變。
此慣例並非推測，而是對 archive 驗證過的：解出原站與其回轉版之間的旋轉
（對法向施以 Kabsch 演算法），七組全部重現至 2° 以內。

參考面以虛線大圓及其 pole 繪出，並隨資料一同旋轉，
因此回轉是否正確可直接目視判斷：虛線圓會壓平至基準圓上，pole 則移至圓心。

**旋轉角度並非計算而得。** 該角度無解析解，須以試誤方式檢視結果，
這也是 archive 資料夾名稱直接記錄當年試用值的原因，例如 `(backtilted 020 -20)`。
本程式的作用僅在於加速試誤過程，並明確標示當前套用的旋轉；
參考面的選擇與旋轉角度的判斷仍由使用者決定。

### 軸的位移

將實測的軸經同一旋轉轉換後，繪於回轉後的圖上，以**空心圈**表示，並以虛線弧連接至星形。
理由在於：單獨檢視一張回轉後的圖，無法看出「傾轉」本身，
軸僅是位於不同位置，圖面上並無任何資訊指出其原始方位。

**空心圈與星形不必然重合，且是否重合取決於所用方法。**

- **S4MIN 為精確等變。** S₄ 具旋轉不變性，因此其最小值隨資料一同旋轉。
  由此可推論：回轉**不可能**改變 S4MIN 的 Φ 與 S₄，
  傾轉檢驗的全部內容即在於「軸最終落於何處」。
- **INVDIR 非等變。** 式 (14) 將張量的**對角線**固定於**地理座標**下的
  cos ψ、cos(ψ+2π/3)、cos(ψ+4π/3)。資料一經旋轉，該四參數族即成為另一個族，
  對回轉後的資料重新計算，所搜尋的是不同的解空間。

**此為 Angelier 方法本身的性質，而非本重建版的缺陷。**
以原程式自身執行的十四組 archive 回轉配對驗證（經 Kabsch 擬合 < 2° 確認為同一批資料）：
將母站的軸經旋轉轉換後，與檔案中回轉版的計算結果相比，
中位差為 σ₁ **10.4°**、σ₂ **24.3°**、σ₃ **23.6°**，最大達 88.7°。
差距最大的數筆多落在 Φ 接近 0 或 1、兩根軸近乎簡併的站點，但並非全部如此：
0214-5（13 筆、Φ 0.46 → 0.72）σ₁ 仍差 19.8°、σ₃ 差 22.8°。

**對研究撰寫的意義**：若僅採用 INVDIR，「回轉前後軸發生變化」有一部分反映的是
參數化的性質而非地質意義，因此「回轉後 σ₁₂₃ 回到水平／垂直」本身不足以作為證據。
較嚴謹的判準應採 S4MIN（其軸可證明僅為純旋轉），INVDIR 則保留作為與舊有 run
的連續性對照。視窗會同時列出兩者及其差距。相關測試見 `tests/test_backtilt.py`。

### 「轉回水平」並非必然正確

該做法預設斷層形成早於傾轉。若斷層是**在傾轉過程中**形成的，
則僅有部分傾轉發生於其後，將全部傾轉轉回即構成過度回轉，
會得到一個從未存在過的應力張量。

**Tilt test** 將旋轉自 0 掃描至 125 %，每一步皆執行反演，並繪出兩項診斷量：

| 診斷量 | 說明 |
|---|---|
| 平均 ANG、RUP、S₄ | 單一張量解釋資料的程度。最佳值落在 100 % 附近，表示斷層形成早於傾轉 |
| Andersonian 失配 | 90° 減去最陡那根軸的傾沒，故 0 代表一軸垂直、兩軸水平。同時判定應力體制：σ₁ 垂直為正斷、σ₂ 為平移、σ₃ 為逆衝 |

最佳解落在遠低於完全回轉之處，即為同傾轉斷層的特徵，程式會明確標示。
若兩項判準的差異超過旋轉量的 20 %，程式亦會提示，
因為該分歧須先釐清，兩項判準才具參考價值。兩者皆非證明，而是診斷指標。

實例：0404-4C-2 對一個虛構的參考面，兩項判準均隨回轉而**變差**，
最佳值落在 10 %，Andersonian 失配自 40.8° 升至 49.2°。
將該面轉回水平，會在無警示的情況下得到比原始資料更差的結果。

## 繪圖：HPGL 為畫風的判準依據

每個 run 資料夾內都有一個 `HPGL` 檔，內容為純文字的繪圖機向量指令。
它並非對程式繪圖行為的描述，而**即是**程式逐筆繪出的那張圖。
因此本專案的畫風係經量測該檔案而得，並非依論文插圖推測。

- **投影法為等面積 Schmidt 投影。** 此結論係經量測而得，非出於假設：
  大圓在等角投影下為正圓弧，在等面積投影下則非。
  實測圓弧擬合殘差為 0.0044 / 0.0062 / 0.0010，等面積投影的預測值為
  0.0040 / 0.0055 / 0.0007，若為等角投影則應為 0。
- **星形符號**：σ₁ 為五角、σ₂ 為四角（斜置）、σ₃ 為三角。其大小非固定值：
  `size = 0.1004 + 0.0928·(0.5 − Φ)·λᵢ`（以 21 張圖、63 顆星擬合，rms 0.00063）。
  Φ = 0.5 時三者等大，故大小順序在 Φ = 0.5 兩側會反轉。
- **擦痕符號為剪切對偶，非單一箭頭**：實心圓點搭配兩支平行軸線，各側偏 0.024，
  故圖面上呈 Z 字形。頭部形式依信心度而定：S 無頭、P 每端一條單邊倒鉤、
  C 每端一個兩段式細長頭。倒鉤與側偏所在側由 `sign(滑動 · 走向)` 決定，
  89 筆全數符合；若依運動字母判定則僅 83 筆正確。
- **粗箭頭**位於圓外，沿 σ₁ 向內、沿 σ₃ 向外；傾沒超過 45° 的該對不予繪出。
- **外框並非對稱於投影網中心。** 93 個 archive HPGL 檔完全一致：
  x 自 −1.2527 至 1.2547、y 自 **−1.3047 至 1.4585**（單位為基準圓半徑），
  標註皆為固定欄左對齊。本專案先前曾假設對稱，導致底邊偏低 0.15。

**HPGL 匯出**的實作方式是令 `pytector.penrec` 代替 matplotlib Axes，
重播 `plot.plot_site` 本身，因此檔案內容與圖面完全一致，
不存在第二套實作可能產生偏移。輸出對齊 archive 自身的框架
（400-5420 × 396-5928 繪圖機單位），由 `tests/test_ui_contract.py` 驗證。

## 舊檔讀寫

舊有的 run 可直接讀入；反演完成後，pyTECTOR 會以原格式寫出 `INFO1` 與 `MOHR1`，
並顯示於介面上。

`tests/test_report.py` 以記錄的解重新產生這兩個檔案，並與原始檔案比對，
分別檢查**版面**（比對每個數字的欄位跨距）與**數值**。
目前狀態：兩站皆為 0 項版面差異、0 項數值差異。

刻意保留的兩處差異：

- 檔頭橫幅標示 pyTECTOR，不冒用 TENSOR 5.45 的名義。供程式解析的部分
  （定寬表格、`03` 結果行）維持原樣，因此檔案仍可由 `pytector.tensorfile` 讀回。
- `RMU` 在正向應力接近零時可能相差數十個百分點，因其為比值。其餘各欄皆在 ±1 之內。

兩項容易實作錯誤的版面細節：

- 兩個旗標欄位寬 2 字元且**靠右**對齊，因此 `!!` 會緊貼數字，
  而單一個 `!` 前方需補一個空格。
- 標題為 `<75` 與 `<45` 的兩欄，是**同一統計量取通過門檻後的子集**，
  並非重複前一欄。0406-7 全部 29 筆的平均 ANG 為 21，低於 45 的 28 筆為 15，
  差異即來自那筆 174° 的離群值。

## 檔案格式

係以資料檔、`MOHR1`、`INFO1`、`Mesure_key.txt` 相互對照解出，並以兩站 35 筆資料驗證。
格式為定寬 ASCII，每個 run 一個資料夾，**輸入與輸出位於同一檔案**：

| 位置 | 內容 |
|---|---|
| `[0:2]` | 第一位＝擦痕信心度 **1=C、2=P、3=S**；第二位＝rake 從走向線哪一端量起（1＝正規端，即傾向−90；2＝另一端，此時存的是 180 − 輸入值） |
| `[2:5]` | **真正的傾向**，已經含象限字母的判斷，所以 `SN 174 74E` 是 84 不是 264 |
| `[5:7]` | 傾角 |
| `[7:10]` | **rake（pitch）**，從（傾向−90）那一端量起 |
| `[47:61]` | 當年輸入的原始欄位；最後一欄可能是 rake（`62N`）或 trend（`124`） |

兩處實際遭遇過的陷阱：

- **滑動方向 = rake + 180°。** 直接採用欄位值會導致 σ₁ 與 σ₃ 對調。
- 若某站所有面的傾角皆在 85-89° 之間，`sin(plunge) = sin(rake)·sin(dip)`
  會使 rake 與 plunge 相差不到 1°，導致 `[7:10]` 看似 plunge，實則並非。
  須以傾角範圍 42-89° 的 0406-7 才能確認。

`03` 結果行同為定寬格式（trend 佔 5 字元、plunge 佔 4 字元），中間無分隔符號。
以空白切分或以數字正規表示式擷取，皆會得到錯誤結果。

## 驗證

十一個測試檔全數通過。有 archive 時即讀取，無 archive 時則 skip，不會 fail。

| 測試 | 驗證範圍 |
|---|---|
| `test_replication.py` | 整條流程對照原程式自身的輸出 |
| `test_fixture.py` | 整條流程對照公開 fixture，無須 archive |
| `test_report.py` | INFO1 / MOHR1 的版面與數值 |
| `test_entry.py` | 打字輸入對照檔案中儲存的值，35 筆 |
| `test_rotate.py` | 回轉慣例，對照七組 archive 配對 |
| `test_backtilt.py` | S4MIN 等變、INVDIR 不等變 |
| `test_diagnose.py` | leave-one-out 影響力診斷 |
| `test_session.py` | session 存讀一輪不改變任何結果 |
| `test_ui_contract.py` | 介面所調用的項目均存在；HPGL 匯出 |
| `test_gui_logic.py` | 介面中不涉及 Qt 的部分 |
| `test_import.py` | 套件可正常匯入 |

0406-7（29 筆，傾角 42-89°）是確立演算法的關鍵站點：

```
前向模型 vs MOHR1        max |SIGMN| 0.001  |TAU| 0.001  |TAUST| 0.001
                         max |RUP|   0.099  |ANG| 0.113
INVDIR 流程              sigma1 0.047 度   sigma2 0.020   sigma3 0.032
                         Phi 0.138（檔案 0.138）
                         平均 ANG 20.898（20.900）  平均 RUP 54.097（54.100）
                         印出的 LAMBDA 0.682（0.680）
```

L12（六個近平行、近垂直的面）為簡併站點，重現程度較為寬鬆：軸約 1°、
平均 RUP 在 0.6 % 以內。容差係**逐站設定**以反映此差異，而非全域放寬。

測試中不會建立任何 Qt 物件：自動化 shell 啟動 QApplication 會彈出平台外掛
錯誤對話框並結束程序。測試改以驗證介面與函式庫之間的契約為主。

## 效能

ψ 掃描原本每趟呼叫純量常式 4000 次，並疊加 120 步三分搜尋，
而 archive LAMBDA 又將整套流程重跑約九十次。實際上其中幾乎沒有一步與 ψ 相關：
僅對角線帶有 ψ，且為線性關係，因此 3×3 normal matrix 為資料集的常數，
每個 ψ 僅需對同一分解執行一次回代。PSIDIR 與 S4MIN 的起點掃描亦以特徵座標系
做同樣的化簡。

0406-7（29 筆）實測結果：

| | 最佳化前 | 最佳化後 |
|---|---|---|
| INVDIR 2 趟 | 0.975 s | 0.004 s |
| S4MIN 400 起點 | 0.208 s | 0.052 s |
| archive LAMBDA | 6.775 s | 0.063 s |

與被取代的常式差異為 1e-13。

## 參考資料集

測試與推導腳本會讀取原程式的實際輸出。該資料屬**未發表的野外資料**，
因此路徑不寫入原始碼中：

```
set PYTECTOR_ARCHIVE=<放 TENSOR run 資料夾的那個目錄>
```

未設定時測試會 skip，不會 fail。資料本身不隨本 repo 發布。

## 專案結構

```
pytector/           函式庫
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
pyTECTOR.py         桌面介面
tests/              對 archive 的回歸測試
research/           各項常數的量測過程，該資料夾另有 README
```

## 更新紀錄

**0.3.0**

- **以 MIT 授權釋出**，解決先前唯一阻礙公開使用的項目
  （授權涵蓋與不涵蓋的範圍見「授權與致謝」）
- 更名 pyTENSOR → **pyTECTOR**，取自 Angelier 自身的資料庫名稱，
  以避開 Delvaux 的 TENSOR／Win-Tensor 與 PyMC 的 `pytensor`
  （見「為什麼叫 pyTECTOR」）。環境變數 `PYTENSOR_ARCHIVE` 仍可使用，
  為 `PYTECTOR_ARCHIVE` 的舊有拼法
- 一鍵安裝：`install.bat` 安裝相依套件並建立桌面捷徑；亦可使用 `pip install .`，
  安裝後提供 `pytector` 指令
- 於原機器實際執行 MESURE 5.51 與 TENSOR 5.45 作為 oracle，
  兩個 session 的完整紀錄見 docs/mesure_oracle.md
- **公開的端到端 fixture**：tests/fixtures/L12-2 為原程式對合成站的完整執行結果，
  tests/test_fixture.py 無須 archive 即可驗證整條流程，軸精度達 0.05°

**0.2.0**

- 回轉功能獨立為一個視窗，實測與回轉結果左右並列，
  並將實測軸經同一旋轉後繪為空心圈
- 確立並以測試固定：INVDIR 非旋轉等變、S4MIN 為等變；
  以原程式的 14 組 archive 配對驗證
- HPGL 匯出改為重播實際的繪圖程式，完整圖面均寫入檔案，
  不再僅含基準圓與斷層面
- 修正外框（非對稱）與標註錨點，螢幕顯示與所有匯出一併修正
- ψ 掃描全面向量化，INVERT 由數秒降至毫秒等級
- 介面調整：常駐一行說明當前繪製內容、資料變更但尚未重算時顯示過期標記、
  各面板加上標題、側欄分段加入細線

**0.1.0**

- 準則、品質估計量與前向模型，以 35 筆資料驗證
- INVDIR ＋ PSIDIR，以及 S4MIN
- 舊檔讀取、原格式的 INFO1 與 MOHR1 輸出
- 依 archive HPGL 量測而得的 Angelier 畫風投影網
- 桌面介面、1991 模式

## 尚未實作

- 寫出 TENSOR 格式的資料檔（站頭欄位已由原程式實際執行解出，
  見 [docs/mesure_oracle.md](docs/mesure_oracle.md)）
- R4DT／R4DS／R2DT／R2DS 等 Angelier 的疊代搜尋法，刻意尚未著手
  （TENSOR 自身的說明文件有相關記載，見 docs/mesure_oracle.md）

## 授權與致謝

本 repo 的程式碼以 **MIT 授權**釋出，全文見 [LICENSE](LICENSE)。
若本工具對已發表研究有所助益，歡迎在引用 Angelier 原始論文之外一併引用本 repo，
但並非必要。

以下三項不在本授權範圍內，因為它們並非本專案所能授權的對象：

- **方法本身**為 Jacques Angelier 所提出，載於前文所引論文。本專案係依其發表的
  論文，並輔以對其程式輸出檔案的量測所完成的獨立重寫，未自原執行檔取用任何
  程式碼。
- **參考資料集**屬未發表的野外資料，未隨本 repo 發布，亦不在本授權範圍內
  （見「參考資料集」一節）。
- **開啟畫面**採用 Angelier 繪製的台灣弧陸碰撞塊體圖。他以玉里附近的地震震源
  機制作為「將此方法應用於地震學資料」的示範案例（1994, fig. 4.44）。該圖為
  已發表的圖件，**未**納入本 repo，因此新 clone 的版本不會有開啟畫面，
  其後的彩蛋亦無法開啟。將 `Taiwan Tectonic Map.jpg` 置於專案根目錄即可恢復兩者，
  僅限本機使用。

維護者：Chi-Hsiu Pang。
