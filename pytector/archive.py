# -*- coding: utf-8 -*-
"""Where the reference TENSOR runs live.

The scripts that derive pyTECTOR's constants, and the regression tests that
check them, read real output from the original program. That archive is
unpublished field data, so its location is not baked into the source: set

    PYTECTOR_ARCHIVE=<folder containing the TENSOR run folders>

Each run is a folder holding an extension-less site file plus INFO1, MOHR1,
PLOT1 and HPGL. Without the variable set, tests and derivation scripts skip
rather than fail, so the package is still usable and testable on its own.
"""
import os

#: Root of the reference archive, or '' when it is not available. The
#: PYTENSOR_ARCHIVE spelling is honoured too: the project was called pyTENSOR
#: before the clash with Delvaux's TENSOR program and PyMC's pytensor package
#: forced a rename, and existing shells still export the old name.
ARCHIVE_ROOT = (os.environ.get('PYTECTOR_ARCHIVE')
                or os.environ.get('PYTENSOR_ARCHIVE', ''))

#: Backwards-compatible alias; most scripts call it ROOT.
ROOT = ARCHIVE_ROOT


def available():
    return bool(ARCHIVE_ROOT) and os.path.isdir(ARCHIVE_ROOT)


def require(what='this script'):
    """Raise a clear message rather than a confusing FileNotFoundError."""
    if not available():
        raise SystemExit(
            '%s needs the reference archive.\n'
            'Set PYTECTOR_ARCHIVE to the folder holding the original TENSOR '
            'runs, for example\n'
            '    set PYTECTOR_ARCHIVE=D:\\paleostress\\runs\n'
            'Current value: %r' % (what, ARCHIVE_ROOT))
    return ARCHIVE_ROOT
