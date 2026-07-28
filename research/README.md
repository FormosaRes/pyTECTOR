# research/ — how every constant was measured

pyTENSOR is a reimplementation, not a guess. These are the scripts that derived
each number in `pytensor/`, kept so the claims in the main README can be
checked rather than taken on trust.

They all read the reference archive, so they need `PYTENSOR_ARCHIVE` pointing
at the folder of original TENSOR runs. Without it they exit with a message.

## The algorithm

| script | what it settled |
|---|---|
| `solve_backtilt.py` | recovers the rotation between an original site and its back-tilted copy (Kabsch on the fault normals), which fixes the back-tilt convention |
| `verify_backtilt.py` | the same check driven from the folder names |

## The drawing style

The `HPGL` file beside every run is plain-text plotter vectors, so it records
exactly what the original program drew. That is the authority for the style,
not the figure captions.

| script | what it settled |
|---|---|
| `render_hpgl.py` | renders the archive plots so they can be looked at |
| `decisive_test.py`, `decisive_test2.py` | **projection.** A great circle is a true circular arc under the stereographic projection and not under the equal-area one. Fitting circles to the archive's own great circles gives residuals matching the equal-area prediction, so it is Schmidt |
| `decide_projection.py`, `overlay_projection.py`, `measure_projection.py` | earlier, weaker attempts at the same question, kept because they show how a wrong primitive radius (2638 instead of 2002) makes equal-angle look better |
| `diag_polys.py` | inventory of what the HPGL actually contains |
| `dump_first.py`, `dump_furniture.py` | the frame furniture: tick lengths, centre cross, the N and M letter strokes, the magnetic dogleg, the box proportions |
| `extract_glyphs.py`, `extract_templates.py` | the star polygons and the heavy arrow template, vertex by vertex |
| `fit_star_size.py` | the star size is not constant. `size = 0.1004 + 0.0928 (0.5 - Phi) lambda`, fitted over 21 plots and 63 stars, rms 0.00063 |
| `zoom_arrows.py`, `probe_striae_glyph.py` | which strokes make up one striae symbol |
| `measure_striae_glyph.py`, `catalogue_striae.py` | the shear-couple geometry across 94 symbols, and the three confidence styles |
| `compare_style.py` | side-by-side check of the original against pyTENSOR's rendering |

## The two runs

| script | what it shows |
|---|---|
| `analyse_batch.py` | INVDIR against S4MIN, broken down by data-set size |
| `ab_wellconstrained.py` | the same, restricted to the axis the data actually constrain |
| `check_phi_degeneracy.py` | confirms the disagreement sits in whichever axis is near-degenerate for that Phi |

Run `run_batch.py` first to produce the CSV these three read.
