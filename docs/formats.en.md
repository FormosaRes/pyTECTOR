# File formats, drawing, and repository layout

How the original program's files are read and written, how the drawing style
was measured off its plotter output, and where everything lives in this
repository.

Back to the [README](../README.md).

---

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
- **Heavy arrows** outside the circle, inward along σ₁ and outward along σ₃.
  **These were never computed from the tensor.** DIAGRA's own help lists them
  under `SPECIAL CODES`, where 81 and 82 are a large black compression and
  extension pair and 83-88 the small and open variants, and once a code is
  chosen it asks

  ```
  AZIMUTH OF ARROWS [0-360] ? :
  ```

  so the direction was typed in by hand, one arrow at a time, until `0` ended
  the loop. On CH-01a the σ₃ pair lands within 0.3° of the solution while the
  σ₁ pair is 3.5° off in opposite senses, which is someone reading integers off
  INFO1 rather than a computed value.

  An archive plate may therefore carry both pairs, one, or none, whatever its
  tensor. Drawing them from σ₁ and σ₃ and omitting an axis plunging more than
  45° is a convenience this reconstruction adds; it reproduces 85 of the 90
  archive runs. The five it does not are runs where no arrow was entered at all
  (QS0711-1, 0406-7A, one back-tilted 0404-04C) or only one pair was (LL-3b,
  CH-01e), and no geometric rule separates them: QS0216-14 draws its σ₃ pair at
  plunge 36.5° while QS0711-1, at 35.4° with every axis within 2.3° of it, draws
  nothing. The **Arrows** checkbox turns them off to match such a plate.
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

---

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

---

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
