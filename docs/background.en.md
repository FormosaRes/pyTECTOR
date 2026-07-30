# Why it was rebuilt from the papers, and why it is called pyTECTOR

Two questions about the project's provenance: why the original binary was not
decompiled, and where the name comes from.

Back to the [README](../README.md).

---

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
