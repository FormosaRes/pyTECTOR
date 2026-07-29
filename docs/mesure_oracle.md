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
DESSIN. pyTENSOR's `decl` field follows the same convention.

## Validation

`tests/test_entry.py` reproduces all three echoes:

```
CD 090 50S 10E     pitch 10.0E  line  96.5/ 7.6    MESURE  10E  96/ 8
CD 090 50N 150     pitch 69.6W  line 330.0/45.9    MESURE  70W 330/46
CD 090 85N 150     pitch 87.1W  line 330.0/84.2    MESURE  87W 329/84
```

MESURE prints whole degrees; its 329 against an exact 330.0 is its own
rounding. Everything else agrees to a tenth of a degree.

## Why this matters for the repository

The field archive cannot be published, so until now every regression fixture
needed `PYTENSOR_ARCHIVE`. A synthetic site typed into the real MESURE, run
through the real TENSOR, photographed or copied out, is an oracle with no
privacy constraint at all. The three records above are the first piece. If
the same `test` site is run through `Tensor.exe` and its INFO1 and MOHR1 are
brought over, the whole pipeline gains a public fixture.
