# -*- coding: utf-8 -*-
"""pyTECTOR - a Python reconstruction of J. Angelier's TENSOR palaeostress
inversion program (TENSOR 5.45, jan91), written from the published method
rather than by disassembling the 16-bit DOS binary.

Two modes:
  invdir  Mode A, faithful to what TENSOR 5.45 actually computed
  modern  Mode B, the same criterion minimised properly

Named in tribute to the original.
"""
__version__ = '0.3.0'

from . import core, invdir, modern, tensorfile          # noqa: F401
from .core import LAMBDA, describe, estimators, summary, S4   # noqa: F401
from .tensorfile import read_site, read_mohr, discover        # noqa: F401
