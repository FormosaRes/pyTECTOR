# pyTECTOR user manual

Every control, the full workflows, and the input and output formats.
The method itself (the criterion, the two runs, λ, equivariance) lives in the
[README](../README.md); this document is about **how to drive the program**.

---

## Contents

1. [Install and start](#1-install-and-start)
2. [The main window](#2-the-main-window)
3. [Getting data in](#3-getting-data-in)
4. [Inverting](#4-inverting)
5. [Reading the results](#5-reading-the-results)
6. [Reading the diagram: Angelier's symbols](#6-reading-the-diagram-angeliers-symbols)
7. [The back-tilt window](#7-the-back-tilt-window)
8. [The tilt test](#8-the-tilt-test)
9. [Output](#9-output)
10. [1991 mode](#10-1991-mode)
11. [Batch and command line](#11-batch-and-command-line)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Install and start

**Install Anaconda or Miniconda first.** Strongly recommended on every
platform: it avoids the Microsoft Store `python` stub, which PyQt5 does not
work under and which is the most common reason a setup fails, and it supplies
scipy and Qt as prebuilt binaries so nothing has to be compiled. Miniconda is
enough. <https://www.anaconda.com/download/success>, default answers, no
administrator rights needed, no need to tick "Add to PATH".

**One click**: double-click **`install.bat`** in the repository root, or run
**`install.command`** on macOS and Linux. Either one finds a Python (Anaconda
and Miniconda first, the Store stub excluded), installs the four dependencies
(numpy, scipy, matplotlib, PyQt5) with conda-forge as the fallback, checks that
all four actually import, records the interpreter in `python-path.txt` so the
launcher starts that same one, compile-checks the program, and puts a pyTECTOR
shortcut on the desktop. Safe to run twice.

If the machine has no Python at all, the installer offers to download Miniconda
from `repo.anaconda.com` and install it for this user, about 80 MB. Answering
`n` opens the download page instead.

Manually: Python 3.8 or newer plus those four packages (an Anaconda install
lacks only PyQt5), then:

```
pyTECTOR.bat        double-click
python pyTECTOR.py  or from a shell
pip install .       also works, and installs a pytector command
```

The opening screen (Angelier's Taiwan block diagram) shows for four seconds; a
click, any key, or its own timer dismisses it. Without
`Taiwan Tectonic Map.jpg` in the program folder it goes straight to the main
window.

Optional environment variable:

```
set PYTECTOR_ARCHIVE=<folder holding the TENSOR run folders>
```

Only the tests and derivation scripts use it; normal operation does not.

## 2. The main window

```
┌───────────────────────────────────────────────────────────────────┐
│ toolbar Open site  Scan folder  Clear │ ☑INVDIR ☑S4MIN ☐Fitted   │
│         INVDIR pass [1]  ☐archive LAMBDA  decl [1.95]             │
│         [INVERT]  Back-tilt │ Save PNG  HPGL  INFO1  MOHR1  About │
├──────────────┬────────────────────────────────────────────────────┤
│ sidebar      │  SITE L12   6 faults   1 excluded    (context line)│
│  SITE        │ ┌────────────────────────────────────────────────┐ │
│  NEW RECORD  │ │        stereograms (one to three panels)       │ │
│  REFERENCE   │ └────────────────────────────────────────────────┘ │
│  PLANES      ├────────────────────────────────────────────────────┤
│  FAULT SLIPS │  Results │ INFO1 │ MOHR1              (bottom tabs)│
│  (table)     │                                                    │
├──────────────┴────────────────────────────────────────────────────┤
│ status bar                                       [progress]       │
└───────────────────────────────────────────────────────────────────┘
```

Division of labour: **the main window shows the data as measured and runs the
inversion, nothing else.** All rotation happens in the back-tilt window
(section 7), so a stereogram here never needs a caption to say which
orientation it is in.

A context line above the plot is always present: site name, fault count,
excluded count, reference surfaces. If the data change after an inversion, a
red **press INVERT** badge appears next to it and a translucent OUT OF DATE
watermark covers the plot. Seeing either means: run INVERT again.

## 3. Getting data in

### 3.1 Typing records (NEW RECORD)

Four fields, the original MESURE format:

```
CS - 122 - 87W - 124
│     │     │     └─ rake + quadrant letter (62N), or a bare trend (124)
│     │     └─────── dip + quadrant letter
│     └───────────── strike 000–360
└─────────────────── confidence + movement
```

**Field 1**, two letters:

| letter 1 (confidence) | letter 2 (movement) |
|---|---|
| C certain | I inverse (reverse) |
| P probable | N normal |
| S supposé (supposed) | S senestral |
| | D dextral |

The confidence sets the striae arrowhead on the plot (C full head, P one barb,
S none). The movement letter is a note; the actual slip direction comes from
field 4.

These are the striated-fault codes of MESURE's own system, which is larger:
index 1 may also be `*` (striae, unknown sense), `F` (fault without
slickensides), `J` (joints and bedding), `M` (metamorphic planes), `L`
(lineations) or `A` (fold axes), each with its own second-letter table, and
the original warns that vertical striae take the letter of the downgoing
side and horizontal faults the motion of the lower block. pyTECTOR reads
the striated-fault records; the full table, recovered from the program's
embedded HELP text, is in
[mesure_oracle.md](mesure_oracle.md#mesures-own-help-the-complete-structure-code-system).

**Field 3**: dip + the dip's quadrant. `87W` means dipping 87° to the west.
The program resolves the true dip azimuth from the quadrant letter, so a
strike of `122` or `302` both work.

**Field 4**, two forms:
- **with a letter** = a rake (pitch), 0–180, measured from the strike-line end
  the letter points at. Example `62N`.
- **without a letter** = the trend of the slip line, 0–360; the program solves
  for the rake of the line with that trend lying in the plane. Example `124`.

Both occur in the archive: 0406-7 was entered as rakes, L12 as trends.

Mechanics: a full field auto-advances to the next; Backspace in an empty field
walks back; **Enter** in any field commits the record. A malformed field pops a
message saying which one.

### 3.2 Opening old runs (Open site / Scan folder)

**Open site**: pick a TENSOR site file, the **extension-less file named after
the site** (`L12`, `0406-04`).

**Scan folder**: pick a root; every TENSOR run underneath is found recursively
and offered in a picker. Double-click or press Open.

What loading does:

1. all fault records go into the table, the site name into the SITE field
2. if the file carries the original `03` result line, the **archive** result
   strip appears with the σ axes and Φ that run recorded
3. if an `INFO1` sits in the same folder:
   - its `(NO k)` fills the **INVDIR pass** spinner
   - its recorded λ enables and ticks **archive LAMBDA** (the value shows on
     the checkbox)

So opening an old run and pressing INVERT immediately reruns it with the
original settings.

### 3.3 The fault table (FAULT SLIPS)

| column | content |
|---|---|
| # | number |
| use | checkbox. Unticked = excluded from inversion and plots, row greyed but kept |
| type | confidence + movement letters |
| as typed | the original input string |
| strike / dip / rake | the resolved canonical values |

Exclusion is reversible; the excluded count shows under the table and in the
context line. Selecting rows and pressing the **Delete** key (or button)
removes them for good.

**Clear** (toolbar) empties the site.

### 3.4 Reference surfaces (REFERENCE PLANES)

Surfaces for the back-tilt window (typically the S₃ foliation or bedding). Two
input modes:

- **plane**: strike + dip-with-quadrant, same convention as faults (`122` `87W`)
- **pole**: the surface's pole as trend / plunge (`045` `12`)

Any number can be entered. **Double-click** one in the list (or select it and
press Set as reference) to make it the back-tilt reference, marked `*` and
drawn with a **long dash**; the others get a short dash. Every surface carries
its open-circle pole.

## 4. Inverting

At least 4 active faults are required (the tensor has four unknowns). Press
**INVERT** or **Ctrl+Enter**. The computation runs in a background thread with
a progress bar in the status bar; the result strips and the INFO1 / MOHR1 tabs
update together when it lands.

Toolbar options:

| control | effect |
|---|---|
| ☑ INVDIR | run Angelier's own method (with the PSIDIR final step). Use for continuity with old runs and the literature |
| ☑ S4MIN | run the exact minimum of the same criterion. Use as the robustness check |
| INVDIR pass | the k of `(NO k)`, the λ iteration count. Match the INFO1 when reproducing an old run; auto-filled on load |
| ☐ archive LAMBDA | adopt the λ recorded in the site's INFO1 instead of re-deriving it. **For reproducing that specific historical run**; only available when the site was loaded with an INFO1. See the README for why |
| ☐ Fitted shear | one extra panel: the same planes carrying the shear the solution predicts, Angelier's visual check of fit quality |
| decl | magnetic declination. Moves the M mark only, **never rotates the data** |

## 5. Reading the results

The Results tab shows up to four strips, each labelled with what it is:

```
ARCHIVE   what the old run recorded     ← from the file's 03 line, if present
INVDIR    as TENSOR 5.45 runs it
S4MIN     exact minimum of the same criterion
```

Each strip: σ₁ σ₂ σ₃ (trend/plunge), Φ, ANG (mean shear–striae angle), RUP
(mean RUP %), and in small type n / S₄ / count of RUP>75.

With both methods ticked a **difference line** appears underneath: the angle
between the two solutions per axis, ΔΦ, ΔS₄. When Φ sits near 0 or 1 it adds a
note that one axis is near-degenerate and the disagreement is expected to sit
there.

Quality conventions (Angelier 1990):

| estimator | good | suspect |
|---|---|---|
| per-datum ANG | < 22.5° | > 45° means that datum disagrees with the solution |
| mean ANG | 7–19° is the range of his published examples | |
| per-datum RUP | < 50 % | > 75 % flags the datum |

Per-datum ANG / RUP live in the INFO1 tab, where over-threshold data carry `!`
/ `!!` flags.

**INFO1 / MOHR1 tabs**: the screen shows the compact version (banner omitted);
saved files carry the full layout. Column meanings: SIGMA=|σ|, SIGMN=σₙ,
TAU=|τ|, TAUST=s·τ, RMU=|τ|/|σₙ|, OBL=arctan(|σₙ|/|τ|), RUP, ANG.

## 6. Reading the diagram: Angelier's symbols

The style is measured stroke by stroke from the original program's HPGL files.
Equal-area (Schmidt) projection, lower hemisphere.

| symbol | meaning |
|---|---|
| thin great circle | fault plane |
| filled dot + double shaft | striae: the dot is the slip line, the two offset parallel shafts are the shear couple (the symbol reads as a Z, not one line), running along the horizontal component of hanging-wall motion |
| arrowheads | C two-segment slender head / P single barb / S bare shaft, from the record's confidence |
| five-pointed star | σ₁ |
| four-pointed star (diagonal) | σ₂ |
| three-pointed star | σ₃ |
| star size | varies with Φ and the eigenvalue (the size order flips either side of Φ = 0.5), same formula as the original |
| heavy arrows outside the circle | inward along σ₁ = compression, outward along σ₃ = extension; omitted for an axis plunging over 45° |
| N | geographic north |
| M + dogleg | magnetic north, positioned by the decl field |
| dashed great circle + open circle | reference surface and its pole; the long dash is the back-tilt reference |
| code at the top | the SITE field |

On screen each panel gets a title line (INVDIR / S4MIN / FITTED SHEAR);
exported PNG and HPGL omit it and keep Angelier's exact layout.

## 7. The back-tilt window

Opened with **Back-tilt** on the toolbar; non-modal, so the main window stays
usable.

On opening it takes a **copy** of the main window's data (not a live view; if
you edit the table, press **Reload data** — this guarantees the pair of
diagrams on screen always describes one consistent data set).

### 7.1 Setting the rotation

The combo picks the source:

- **restore the reference surface to horizontal**: uses the surface starred
  `*` in the main window. If none is starred it says so.
- **rotation axis trend / plunge / angle**: direct input, right-hand rule.

**restore %** (0–125): partial restoration; 100 % applies the whole rotation,
less treats the faults as having moved part-way through the tilting.

The header always shows the rotation in force, including the archive's own
naming form (`backtilted 020 -20`).

### 7.2 Invert both

**Invert both** runs the ticked methods on **both states** and shows them side
by side:

- left, AS MEASURED: the data and the solution as measured
- right, BACK-TILTED: the rotated data and its re-inverted solution, with the
  reference surfaces rotated too (a correct restoration is visible: the dashed
  circle flattens, the pole walks to the centre)

**☑ carried axes** adds three **open rings with dashed arcs** on the right:
the measured σ axes put through the same rotation, arcs leading to the
re-inverted stars. Ring = "the answer, rotated"; star = "the rotated data,
re-inverted".

⚠️ When ring and star disagree, read with care: for S4MIN they coincide by
necessity (S₄ is rotation invariant); for INVDIR they do not (the
parametrisation is pinned to the geographic frame), and that gap is method,
not geology — median 10° on σ₁ and about 24° on σ₂/σ₃ across the archive's own
back-tilt pairs. **Judge "did the axes come back to horizontal/vertical" on
S4MIN.** Details in the README.

### 7.3 The numbers block

Four lines per method: measured and restored σ₁σ₂σ₃ / Φ / ANG / S₄ /
Andersonian misfit (with the regime named), then the carried-vs-re-inverted
separation per axis. If the axes moved **away** from horizontal and vertical
the block says plainly "this rotation is not supported".

**Save PNG** exports this window's side-by-side figure with the Angelier-style
annotation block.

## 8. The tilt test

**Tilt test** in the back-tilt window. Sweeps the rotation from 0 to 125 %,
inverting at every step, and plots two diagnostics:

| curve | meaning |
|---|---|
| fit quality (ANG / RUP / S₄) | best near 100 % → the faults predate the tilting, full restoration is justified. Best part-way → syn-tilt faulting |
| Andersonian misfit | how far the steepest axis is from vertical; 0 = one axis vertical, two horizontal |

If the two curves prefer positions more than 20 % of the rotation apart, the
program flags it — that disagreement needs explaining before trusting either.

Afterwards, pick a percentage in **adopt** and press **Use this restoration**:
the back-tilt window switches to axis mode with the corresponding axis and
angle filled in.

## 9. Output

| button | contents |
|---|---|
| Save PNG (main window) | the current figure at 300 dpi. The export drops the screen titles and adds Angelier's two-line annotation block (S1 S2 S3 / PHI ANG RUP N) |
| Save PNG (back-tilt window) | the measured + restored pair, annotated the same way |
| Save HPGL | plotter vectors in **the original program's dialect and coordinates** (scale 2002, origin 2908,3008 — overlays the archive's own HPGL files). Content = the screen drawing code replayed, so everything is in it: striae, ticks, cross, N/M, frame, arrows, reference surfaces |
| Save INFO1 | the full INFO1 with banner; layout column-identical to the original, readable back by `pytector.tensorfile` |
| Save MOHR1 | likewise for MOHR1 |

Note: INFO1/MOHR1 report **the first method with a result** (INVDIR if it was
ticked). The banner names pyTECTOR rather than claiming to be TENSOR 5.45;
everything machine-read (fixed-width table, the 03 line) keeps the original
layout.

## 10. 1991 mode

The easter egg. Trigger: **click the J.A. signature on the opening screen**.

What changes: Turbo Pascal blue DOS palette, double-line frames, monospace
type, the stereogram goes phosphor green on black with antialiasing off (lines
render as pixel stairs), and the interface switches to French — where words
marked ORIGINAL are taken from the program's own output files (CALCUL DU
TENSEUR DES CONTRAINTES, MOYENNE, ECART-…). The About box's "1991 mode" tab
lists which words are Angelier's and which were translated here.

**Nothing about the computation changes.** The way back is the
**MODE 1991 ×** button that appears on the right of the toolbar.

## 11. Batch and command line

```
python demo_report.py [site file]       invert an old site, print INFO1 + MOHR1
python run_batch.py [root] [out.csv]    both methods over every run under root
python demo_fitted.py                   observed vs fitted comparison figure
```

The library works without the GUI:

```python
from pytector import read_site, invdir, modern, core
site = read_site(r'...\L12\L12')
r = invdir.run(site.n, site.s, n_pass=2)      # INVDIR
b = modern.run(site.n, site.s)                # S4MIN
print(core.summary(r['T'], site.n, site.s)['sigma1'])
```

## 12. Troubleshooting

| symptom | cause and fix |
|---|---|
| "Four fault slips are the minimum" | fewer than 4 active faults; check the use column |
| a record is rejected | see section 3.1; dip 0–90, rake 0–180, trend 0–360 |
| archive LAMBDA greyed out | the site was not loaded from a folder with an INFO1; typed data has no historical λ to adopt |
| OUT OF DATE across the plot | data or settings changed since the last inversion; press INVERT |
| back-tilt window says "mark a reference surface" | star one in the main window's list, then press Reload data |
| back-tilt window shows stale data | press Reload data; it works on a copy taken when opened |
| the two methods disagree a lot | check n and Φ first: below n = 7 or with Φ near 0/1 that is expected (statistics in the README). Chase it only if the gap crosses one of your stage boundaries |
| an old run reproduces 1° off | make sure INVDIR pass matches the INFO1's (NO k) and archive LAMBDA is ticked |
| exported HPGL does not overlay an old plot | use 0.2.0 or later (earlier exports were a quarter too large) |
| `ModuleNotFoundError: No module named 'PyQt5'` | the launcher started a different Python from the one the dependencies went into. Run `install.bat` (or `install.command`) again: it records the interpreter in `python-path.txt` and the launcher then uses that one |
| typing `python` opens the Microsoft Store | that is the Store stub, not an interpreter. Install Miniconda and run the installer again; it excludes the stub by path |
| the installer cannot install anything | usually a proxy blocking pip, or no network. With conda present it falls back to conda-forge on its own, so installing Miniconda first often clears it |
| the desktop shortcut does nothing | it points at `pyTECTOR.bat` in the folder you ran the installer from. Moving or renaming that folder breaks it; run `install.bat` again from the new location |
