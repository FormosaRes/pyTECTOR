# The original programs run as oracles

Two sessions on the Windows XP machine (a VMware guest), both photographed in
full: MESURE 5.51 creating a data file, and TENSOR 5.45 inverting one.

# MESURE 5.51 run as an oracle

On 2026-07-29 the original data-entry program was run on the Windows XP
machine (`C:\PALEOS~1\Mesure.exe`, banner: *Progr. MESURE, 1976-1991, version
5.51, aou91, Copyright 1987-1991 J. Angelier*) and the whole session was
photographed. This page transcribes it, because it settles several things the
data files alone could not.

The three typed records and their echoes are locked into
`tests/test_entry.py` as an archive-independent oracle.

## The session, step by step

```
FRANCAIS (1), ENGLISH (2) ?                        <- bilingual from the start

0 : STOP !
1 : CREATING DATA FILE ;
2 : READING DATA FILE ;
3 : MODIFICATIONS IN SITES OF DATA FILE ;
4 : ADDING SITES AT THE END OF DATA FILE ;
5 : CHECKING DATA FILE ;
6 : INFORMATION ON MEASUREMENTS ;
7 : TRANSLATION OF OLD TYPE DATA FILE ;
8 : IMPROVING RAW DATA FILE (MEASUREMENTS ONLY) ;
9 : ASCRIBING AGE NUMBER OF TECTONIC EVENT ? 1     <- the event number

ENTER THE NAME OF FILE THAT WILL BE CREATED (! = FILE "TECT") : test
WAS THE MAGNETIC DEVIATION CORRECTED BY THE COMPASS ? (Y/N) : Y
WILL YOU RECORD YOUR ORIGINAL DATA [RECOMMENDED] ? (Y/N) : Y

COMMON INFORMATION IN ALL FOLLOWING DATA SITES :
NAMES OF AUTHORS OF FIELD OBSERVATION ? : PANG
a) MAGNETIC DEVIATION, IN DEGREES ? (E+,W-) : +2   <- declination, east +
bc) DO YOU ADOPT USUAL ERROR [1+6 deg] ? (Y/N) : Y <- 1 deg instrument,
                                                      6 deg observer
NAME OF SITE ? (MAXI 8 CHARACTERS) [! = temporary name SCRATCH] : 01
POSSIBLE SUFFIX ? (MAXI 3 CHARACTERS) [if not, blank] :
DAY, MONTH, YEAR ? (SIX DIGITS; ex:010387) : 211212
PAGE OF NOTEBOOK ? (4 DIGITS; ex:0041) : 0505
ENTRY OF GEOGRAPHIC COORDINATES OF THE SITE : MODE 0-3, adopted 0

** SITE 01            DATE=211212    PAGE= 505    (GEO.,MAG.)=  2 **
** LATITUDE 0.000  LONGITUDE 0.000   ERREUR= 1 (INSTR.), 6(OBSERV.) **
DO YOU ACCEPT THIS ? (Y/N) : Y

GEOGRAPHICALLY DEFINE SITE LOCATION ! (! = HATCHET WORK...)
ENTER MEASUREMENT (?=HELP,!=NUMBER, +=COMMENT,/=END)
```

Measurements typed, with the program's echo on the left:

```
typed CD 090 50S 10E   ->   1 C1D  90 50S 10E  96  8
typed CD 090 50N 150   ->   2 C1D  90 50N 70W 330 46
typed CD 090 85N 150   ->   3 C1D  90 85N 87W 329 84
typed /                ->   -----> END OF SITE 01
                            DO YOU NEED A NEW SITE ? (Y/N)
```

Every trend-form entry (a bare number in field 4) triggers:

```
LINEATION : YOU SHOULD HAVE MEASURED A PITCH ;
DO YOU INSIST ? (Y/N) : Y
```

and each measurement gets a continuation prompt with a default code string:

```
CONT. ?        1CCC0C0T  0.000<----comment.---->
```

A malformed record gives `ERROR : STRUCTURE CODE  OR LINEATION !` then
`WRONG MEASUREMENT ! CANCELLED ! TRY AGAIN !` and the record is dropped.

## What this settles

**The echo format.** `n C1D strike dip+Q pitch+Q trend plunge`: MESURE always
computes and shows *both* representations, the pitch and the line's trend and
plunge, whatever form was typed. The echo shows the striae **axis in its
lower-hemisphere form**; the data file stores the rake with the
movement = rake + 180 convention. Same datum, two representations, and the
reason the file values differ from the screen by 180 on trend-form entries.

**The middle character of the code is the tectonic-event number.** `C1D` is
confidence C, event 1 (main-menu item 9), movement D. The two-digit numeric
code in the data files encodes confidence and rake-end instead; the event
number rides along elsewhere in the record.

**Pitch is the canonical measurement.** The program actively discourages
trend entry ("YOU SHOULD HAVE MEASURED A PITCH"). Both archive styles exist
(0406-7 pitches, L12 trends), and now we know the original's own preference.

**The site header fields.** Date DDMMYY, notebook page, coordinates (with a
mode switch for decimal degrees / deg-min / deg-min-sec), the declination
stored per file as `(GEO.,MAG.)`, and the adopted errors
`ERREUR= 1 (INSTR.), 6(OBSERV.)`. These are the fields the extension-less
site file's header line carries.

**Declination semantics: east positive, west negative, in degrees.** The
test file stored +2. The M mark measured off the archive HPGL sits at 1.95
degrees east of north, consistent with a stored declination of +2 drawn by
DESSIN. pyTECTOR's `decl` field follows the same convention.

## Validation

`tests/test_entry.py` reproduces all three echoes:

```
CD 090 50S 10E     pitch 10.0E  line  96.5/ 7.6    MESURE  10E  96/ 8
CD 090 50N 150     pitch 69.6W  line 330.0/45.9    MESURE  70W 330/46
CD 090 85N 150     pitch 87.1W  line 330.0/84.2    MESURE  87W 329/84
```

MESURE prints whole degrees; its 329 against an exact 330.0 is its own
rounding. Everything else agrees to a tenth of a degree.

# TENSOR 5.45 run as an oracle (2026-07-29)

`Tensor.exe`, same machine, on a synthetic five-fault file named `L12-2`,
site 01. The whole dialogue was photographed.

## The dialogue

```
FRANCAIS (1), ENGLISH (2) ? 2
WILL YOU NEED MOST ORDINARY RUN MODE ?
[IF NOT, ACCESS TO AUTOMATISM, TO REPEATED
 PROCESSES AND TO SPECIAL CHOICES]   (Y/N) : Y     <- N is where repeated
                                                      passes (NO 2+) live
WILL YOU CREATE A "MOHR" FILE ... ? (Y/N) : Y
FAULTS TO BE RETAINED FOR THE MOHR'S DIAGRAM ?
0 = ALL FAULTS, EVEN UNCONSISTENT (!-!!) [RUP 0-200 % or ANG 0-180 deg] ;
1 = FAULTS WELL OR MODERATELY CONSISTENT (!) [RUP 0-75 % or ANG 0-45 deg] ;
2 = FAULTS WELL CONSISTENT SOLELY [RUP 0-50 % or ANG 0-22.5 deg]  : 0

>>> FILE READY TO BE CREATED : INFO2               <- INFO1 existed, so the
>>> FILE READY TO BE CREATED : MOHR2                  number increments

DO YOU NEED INFORMATION ABOUT THE METHODS ? Y      <- see below

NAME OF DATA FILE ? (/=END) : L12-2
ENTER THE NAME OF NEEDED SITE ! (?=NEXT SITE,
 !=SAME SITE AS BEFORE, +=ENTIRE FILE, /=END) : 01
SITE SUFFIX ? [3 CHAR.; /=DOES NOT MATTER] : /
WILL YOU ADOPT THE FOLLOWING DEFAULT OPTION :
ALL CERTAINTIES, ALL WEIGHTS, ANY AGE ?
[IF NOT, SUCCESSIVE CHOICES] [A: AGE SOLELY] (Y/N) : Y
WHAT METHOD WILL YOU USE FOR TENSOR COMPUTATION ?
(INVD, R4DT, R4DS, R2DT, R2DS)      [help=?] : INVD
DATA WEIGHTING MODE ?
1=NO WEIGHTING ; 2=WEIGHT ; 3=WEIGHT+ERRORS;
4=WEIGHT+ERRORS+OFFSET; 5=ERRORS; 6=ERRORS+OFFSET;
7=OFFSET; 8=WEIGHT+OFFSET : 1
...
DO YOU PLAN RECORDING THIS RESULT ? (Y/N) : Y      <- THIS writes the 03 line
                                                      into the data file
```

## The result, readable off the photographs

```
SOLUTION PSIDIR          AXES OK !
LAMBDA= 0.87            TAUMAX= 0.85
S1= 0.77    S2= 0.16    S3=-0.94
AXIS SIGMA 1   D= 255.   P= 21.
AXIS SIGMA 2   D= 115.   P= 64.
AXIS SIGMA 3   D= 351.   P= 15.
RATIO PHI= 0.645

per fault (x100): SIGMA SIGMN TAU TAUST    RMU  RUP  OBL  ANG
  1.  76  9 75 75   812  16   7  5
  2.  77 24 73 73   303  16  18  2
  3.  73  3 73 73  2220  16   3  3
  4.  76 15 75 74   484  14  12  2
  5.  74 20 72 71   358  20  16  6
mean 75 14 73 73    835  16   11   4      s.dev 1 7 1 1  714  2  6  1

03INVD09254.820.7114.663.9350.715.30.645 3.7 16.10919  5.  501       2
```

So: σ₁ 254.8/20.7, σ₂ 114.6/63.9, σ₃ 350.7/15.3, Φ 0.645, mean ANG 3.7,
mean RUP 16.1, n = 5.

## What the session settles

- **Where multi-pass runs come from.** The ordinary run mode skips them;
  answering N at the first question opens "automatism, repeated processes and
  special choices", which is where the archive's NO 2-5 runs were made.
- **The `<75` / `<45` columns' thresholds are the program's own fault-quality
  bands** (0-50/0-75/0-200 RUP, 0-22.5/0-45/0-180 ANG), the same bands used
  to pick which faults a MOHR file keeps.
- **The 03 result line in every archive data file is written by the
  "DO YOU PLAN RECORDING THIS RESULT" step**, which is why data files carry
  their own results.
- **Output numbering**: INFO2/MOHR2 are created when INFO1/MOHR1 already
  exist, which explains the INFO2/MOHR2 files dotted through the archive.
- **Weighting modes 1-8** combine weight, the per-site instrument/observer
  errors, and offset. The archive runs used mode 1 (all weights 1.0).
- **TENSOR's own method credits**: INVDIR is "modified from a first method,
  now abandoned, by J. Angelier and J. Goguel (1979)" (C.R. Acad. Sci. Paris
  288(D), 307-310) and "described in detail" in the GJI paper (cited as 1988,
  its in-press year inside the jan91 binary; it appeared in 1990). R4DT/R4DS
  are the 4-D iterative searches minimising S2 (tan) or S3 (sin), the
  angle-only criteria; R2DT/R2DS constrain one axis to vertical. Companion
  programs named: DIEDRE (P-T dihedra), CONJUG (conjugate systems), and the
  post-processors ANATEN, TRIAGE, DIMOHR.

# The programs themselves: the 2008 workshop binaries (2026-07-29)

A RAR from a 2008-04-09 workshop distribution turned up with the complete
suite: `Mesure.exe`, `Tensor.exe`, `Diagra.exe`, `Dessin.exe`, `Vision.exe`,
`Tra.exe`, `Traduc.exe`. All are 16-bit DOS executables; the four big ones
are compiled Fortran with every dialogue text intact as FORMAT strings, so
the full embedded text could be extracted and read. The banners match the
XP machine exactly: MESURE 5.51 (aou91), TENSOR 5.45 (jan91), DIAGRA 5.39
(aou91). These are the very programs that produced the archive and the
fixture. (The binaries are not redistributable and are not committed; this
page records what they contain.)

## The drawing pipeline

- **DIAGRA** computes the diagram and writes a plot file in **CALCOMP**
  format (the fixture's `PLOT1`).
- **VISION** (Turbo Pascal, Turbo Graphix, French-only menus) reads a
  CALCOMP plot file — its default file name is literally `plot1` — and
  draws it on the screen: `Dessin de l'ensemble --> A`, `Dessin d'un
  diagramme --> [1-12]`.
- **TRADUC** translates CALCOMP to HPGL ("TRANSFER DES FICHERS
  (Calcomp --> HpLaser)"); its output contains the `PD;PA`, `PU;PA`,
  `DI 1,0;SI` commands we measured. **TRA** (Turbo C) is its batch
  front-end, spawning `traduc` and renaming the output `hpgl`.

So screen picture and HPGL plot are two renderings of the same CALCOMP
file, drawn once by DIAGRA. That is why the photograph of the VISION screen
agrees with the fixture HPGL element for element (next section).

## MESURE's own HELP: the complete structure-code system

The `?` help embedded in Mesure.exe gives the authoritative code table,
bilingual. A measurement is `(2A1,1X,I3,2(1X,I2,A1))`: two index letters,
strike, dip+quadrant, then optionally rake+quadrant or a bare azimuth
(000 forbidden).

**Index 1** (what the structure is):

| code | meaning |
|---|---|
| C | striated fault, sure sense |
| P | striated fault, probable sense |
| S | striated fault, supposed sense |
| * | striated fault, unknown sense ("no use for tensors") |
| F | fault without slickensides |
| J | any joint (fracture, gash, bedding) |
| M | metamorphic plane, with or without lineation |
| L | any single lineation |
| A | any axis (fold axis) |

**Index 2 for C, P, S faults**: N normal, I inverse/reverse, D dextral,
S sinistral — with two special cases spelled out by the program itself:
vertical striae take the letter of the **downgoing side** (N, E, W, S), and
a horizontal fault takes the **motion of the lower block** (N, E, W, S).

**Index 2 for J**: blank simple fracture; O, S, X, F, V tension gashes
(open / sediment-filled / mineralized / fibrous / dike); P stylolitic
peaks; N, I, * bedding (normal / overturned / undefined).

**Index 2 for M**: blank undefined, S schistosity, F mineral foliation,
M mylonitic, C cleavage; an index 3 (T, C, E, X, M) defines a lineation
borne on the plane.

**Index 2 for L**: blank undefined, F mineral fiber, P stylolite peak or
impact axis, T intersection, C crenulation, E extension, X mineral,
M mylonitic.

**Index 2 for A**: blank undefined, A anticline, S syncline.

**Input mode Z** (index 2 = Z) uses a signed rake instead: 0 to 180 for a
reverse fault (1-89 reverse-dextral, 91-179 reverse-sinistral), 0 to -180
for a normal fault. A third index letter marks double measurements (a plane
parallel to bedding, or a metamorphic plane with its lineation).

## The CONT. line decoded

The continuation prompt's default string `1CCC0C0T  0.000` is nine fields,
which the help enumerates:

| field | default | meaning |
|---|---|---|
| 1 | `1` | weight, 1-9 |
| 2-4 | `CCC` | error grades on strike, dip, rake/azimuth: A-E from excellent to bad, C average |
| 5 | `0` | chronological order (tectonic event), 1-9, 0 undefined |
| 6 | `C` | certainty of that order: C certain, P probable, S inferred |
| 7 | `0` | association index: rank within a sequence of associated measurements |
| 8 | `T` | type of separation: blank null, `-` as before, T total, L lateral, F dip-slip, V vertical |
| 9 | `0.000` | value of that separation component, metres |

plus a free comment. This is the tail our reader carries through unparsed.

## TENSOR's embedded text

The method help photographed on the XP machine is recovered verbatim, in
both languages (the French version cites the GJI paper as "J. Angelier
(1990)"; the English as 1988, its in-press year). Beyond what the
photographs showed, the strings hold the rest of the special-mode dialogue:

- search-grid menu for the iterative methods: `X` choice of each parameter
  ("difficult !"), `S` special autofocus grid, `B` mean grid rather mobile,
  `P` small mobile grid, `F` very small and mobile grid;
- selection of up to 5 tectonic events per run;
- lower and upper bounds on Phi for a constrained run;
- automatic (batch) processing over all sites of a file, with a warning
  that "NO in automatic mode" writes no results back;
- screen/file detail levels (minimum, brief, extensive).

The INVDIR/PSIDIR mathematics are compiled code, not strings, so the
PSIDIR criterion stays an open question.

## DIAGRA's embedded text

Projection menu: Schmidt lower/upper, Wulff lower/upper (1-4); up to 12
diagrams in a frame; a diagram is composed of up to 10 plottable types
drawn from a 16-entry list: poles to faults, fault striae, B/P/T axes of
faults, fracture joints, bedding, tension cracks, stylolitic joints,
fracture cleavage, fold axes, tension fibers, stylolitic peaks, metamorphic
foliation, metamorphic lineation, "non-faults". Diagram diameter is asked
in centimetres — the fixture's 10 gives the 2002-unit radius at 400
HPGL units per cm.

# DIAGRA 5.39 run as an oracle (2026-07-30)

`Diagra.exe` was run on the XP machine against the fixture site `L12-2`, site
`01`, and the whole dialogue photographed. It settles where the heavy stress
arrows come from, which the HPGL files alone could not.

## The composition menu, in full

Answering `100` at the first TYPE prompt prints the authoritative table:

```
CODES TO BE USED TO DEFINE STRUCTURES [0=END] :
  1=FAULTS, 2=STRIAE, 3=B-AXES, 4=P-AXES, 5=T-AXES,
  6=FRACTURE JOINTS, 7=BEDDING, 8=TENSION CRACKS,
  9=STYLOLITIC JOINTS, 10=FRACTURE CLEAVAGE,
  11=FOLD AXES, 12=TENSION FIBERS, 13=STYLOLITES OR
  IMPACT AXES, 14=ALL METAMORPHIC CLEAVAGES,
  15=METAMORPHIC LINEATIONS, 16=NON-FAULTS.
(to project planes instead of poles, use sign - !)

CODES FOR SEARCHING RESULTS [0=END] :
-> PALEOSTRESS AXES :
   31=INVD, 32=R4DT, 33=R4DS, 34=R2DT, 35=R2DS, 36=DIPT
-> MEAN AXIS (AM) OR MEAN PLANE (PM) :
   add 40 to corresponding structure code (41-55)
-> REVOLUTION AXIS (AR) OR REVOLUTION PLANE (PR) :
   add 60 to corresponding structure code (61-75)
(to project planes instead of poles, use sign - !)

SPECIAL CODES [0=END] :
-> BLACK ARROWS : -large : 81=COMPR., 82=EXT. ;
                  -small : 83=COMPR., 84=EXT. ;
-> OPEN ARROWS  : -large : 85=COMPR., 86=EXT. ;
                  -small : 87=COMPR., 88=EXT. .
```

## What this settles

**The heavy arrows are an operator annotation, not a computed result.** They
are `SPECIAL CODES`, entered at the same TYPE prompt as everything else, and
choosing one makes DIAGRA ask

```
AZIMUTH OF ARROWS [0-360] ? :
```

so the direction is typed in by hand, one arrow at a time, until `0` ends the
loop. Nothing ties an arrow to σ₁ or σ₃ except the operator's own reading of
INFO1. Measured on CH-01a's plate the σ₃ pair lands within 0.3° of the
solution while the σ₁ pair is 3.5° off in opposite senses, which is what
typing integers off a printout looks like.

This explains the five archive runs whose arrows do not follow from their
tensors: QS0711-1, 0406-7A and one back-tilted 0404-04C carry none at all,
LL-3b and CH-01e carry one pair where two would be expected. No geometric rule
separates them from the rest, and QS0216-14 proves none can: it draws its σ₃
pair at plunge 36.5° while QS0711-1, at 35.4° with all three axes within 2.3°
of it, draws nothing. pyTECTOR's `ARROW_PLUNGE_LIMIT` therefore describes a
habit of whoever made the plates, not an algorithm, and the interface carries
an **Arrows** switch so a plate without them can be reproduced.

**The stress axes are themselves an opt-in type.** `31=INVD` sits under
"codes for searching results", so the stars are plotted only when 31 is
entered. Choosing it makes DIAGRA ask

```
REFERENCE NUMBER OF RESULT TO BE PLOTTED ?
[options: 0=last acceptable one, 999=first acceptable] :
```

which is the plot-side counterpart of a site file holding more than one `03`
line: the operator chooses which stored solution the plate describes.

**A minus sign means "planes, not poles".** The session entered `-1`, and the
log confirms it drew the faults as great circles:

```
-> POLES TO FAULTS          5.planes  1 drawn, with   5. lineations !
-> tensor axis INVD [type 31] plotted !
```

Those two lines are the whole plate: `-1` and `31`, then `0` to finish. The
run wrote `PLOT2` rather than `PLOT1`, the same increment-if-it-exists rule
TENSOR uses for INFO1 and MOHR1.

# VISION: the screen display (2026-07-29)

The same machine has a program named VISION that draws the plot on screen,
and the user photographed it displaying the L12-2 diagram. Rendered side by
side with the fixture's HPGL file, the two pictures agree element for
element:

- the five fault great circles bowing east, with their slickenside marks;
- the stress axes as star outlines with five, four and three branches for
  sigma1 (255/21, lower left), sigma2 (115/64, right of centre) and
  sigma3 (351/15, top);
- the two heavy arrow pairs outside the circle, pointing inward along the
  sigma1 trend and outward along the sigma3 trend;
- the north arrow with the N and M flags, M sitting the declination east
  of N;
- the site caption along the top edge.

So the suite draws once: DIAGRA computes the picture (its keystroke log is
`diagra_keys.txt` in the fixture), the plotter gets it as HPGL, and VISION
puts the identical picture on the screen. The photograph is an independent
check of the symbol decoding in `pytector/plot.py`, against a real display
rather than our own reading of the HPGL bytes: the 5/4/3-branch star
convention, the eigenvalue-scaled star sizes, and the compression /
extension arrow pairs all match.

## The fixture is in the repository

The complete `L12-2` run is committed at `tests/fixtures/L12-2/`: the data
file, `INFO1`, `MOHR1`, `PLOT1`, the `HPGL` plot, and `Mesure_key.txt`, which
is the keystroke log of the MESURE session that created it (five records,
declination +2, date 090326, page 50). The site is synthetic, so unlike the
field archive it can be published.

`tests/test_fixture.py` runs against it with no environment variable at all:
the reader, the 03 line, the INFO1 fields, the forward model against every
MOHR1 row, the full INVDIR pipeline (axes to 0.05 degrees, Phi exact, printed
LAMBDA 0.73, INVDIR-stage Phi 0.674), S4MIN, and the HPGL geometry. Anyone
who clones the repository can verify pyTECTOR against the original program's
own output.

The photographed 2026-07-29 re-run of the same file reproduced the recorded
03 line digit for digit, so the fixture and the dialogue above describe the
same computation.
