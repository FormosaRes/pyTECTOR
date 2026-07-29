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
