# -*- coding: utf-8 -*-
"""The map panel: stations and their stress axes over OpenStreetMap.

A table of azimuths is not a stress map. The question a set of determinations
is actually asked, whether the direction turns along a structure or holds
across it, is spatial, and until it is drawn in place it cannot be answered.

What is drawn, from the bottom up:

    OpenStreetMap tiles      background, fetched and cached by basemap
    a GeoTIFF                whatever the user brings, at a chosen opacity
    stress axes              a line per station, along the axis, both ways
    stations                 a dot per station, coloured by phase

Everything is in Web Mercator metres, which is what the tiles are in, so no
layer is resampled to sit on another.

The axis lines are the point of the figure. They run both ways from the
station because a stress axis has no arrowhead, and axes plunging past the
shallow limit are left out rather than drawn: their trend is close to
arbitrary and a map of confident lines that mean nothing is worse than a gap.
"""
import math
import os

from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavBar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from . import basemap, rose, survey

#: Half-length of a drawn axis, as a fraction of the width of the view.
#:
#: Not a fixed distance on the ground. A stress axis is a symbol, not a
#: measured length, and 700 m of it vanished under the station dot the moment
#: the whole study area was on screen: at that zoom the entire set spans 80 km
#: and the symbol has to grow with the view or it cannot be read at all.
HALF_FRAC = 0.018
#: and the user can scale that up or down
LENGTH_STEPS = {'short': 0.5, 'normal': 1.0, 'long': 1.8, 'longer': 3.0}

#: one colour per phase, in the order phases are usually numbered. Chosen to
#: stay apart on a printed map and on the pale OSM background.
PHASE_COLOURS = ['#1F4E79', '#B03A2E', '#1E8449', '#6C3483', '#B9770E',
                 '#17706E', '#7D6608']
UNASSIGNED = '#8A8A8A'


class MapPanel(QtWidgets.QWidget):
    """Right-hand map. Owns no data: it is handed records and draws them."""

    def __init__(self, parent=None):
        super(MapPanel, self).__init__(parent)
        self.recs = []
        self.tif = None              # (image, extent, epsg, path)
        self._basemap = None         # (image, extent) for the current view
        self._basemap_box = None
        self._build()

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)

        self.chk_base = QtWidgets.QCheckBox('OpenStreetMap')
        self.chk_base.setChecked(True)
        self.chk_base.setToolTip(
            'Background tiles, cached in py_data/.tilecache after the first '
            'fetch. Needs the network only the first time for a given area.')
        self.chk_base.stateChanged.connect(lambda _s: self.redraw(refetch=True))
        row.addWidget(self.chk_base)

        b = QtWidgets.QPushButton('GeoTIFF...')
        b.setToolTip('Lay a north-up GeoTIFF under the data. Supported: %s'
                     % basemap.SUPPORTED)
        b.clicked.connect(self.load_tif)
        row.addWidget(b)

        self.btn_clear_tif = QtWidgets.QPushButton('x')
        self.btn_clear_tif.setFixedWidth(24)
        self.btn_clear_tif.setToolTip('Remove the GeoTIFF layer')
        self.btn_clear_tif.clicked.connect(self.clear_tif)
        self.btn_clear_tif.setEnabled(False)
        row.addWidget(self.btn_clear_tif)

        lab = QtWidgets.QLabel('opacity')
        lab.setObjectName('legend')
        row.addWidget(lab)
        self.sl_alpha = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sl_alpha.setRange(0, 100)
        self.sl_alpha.setValue(70)
        self.sl_alpha.setFixedWidth(90)
        self.sl_alpha.valueChanged.connect(lambda _v: self.redraw())
        row.addWidget(self.sl_alpha)

        self.cmb_axis = QtWidgets.QComboBox()
        self.cmb_axis.addItems(['axis by regime', 'sigma1', 'sigma3',
                                'sigma1 + sigma3'])
        self.cmb_axis.setToolTip(
            'Which axis to draw. By regime means sigma3 for a normal phase '
            'and sigma1 for a thrust or strike-slip one, decided per phase '
            'from the type column.')
        self.cmb_axis.currentIndexChanged.connect(lambda _i: self.redraw())
        row.addWidget(self.cmb_axis)

        self.cmb_len = QtWidgets.QComboBox()
        self.cmb_len.addItems(list(LENGTH_STEPS))
        self.cmb_len.setCurrentText('normal')
        self.cmb_len.setToolTip(
            'Length of the axis symbols, relative to the width of the view. '
            'They scale with the zoom: a fixed ground length disappears under '
            'the station dot once the whole area is on screen.')
        self.cmb_len.currentIndexChanged.connect(lambda _i: self.redraw())
        row.addWidget(self.cmb_len)

        b = QtWidgets.QPushButton('Fit')
        b.setToolTip('Zoom to the stations')
        b.clicked.connect(lambda: self.redraw(refit=True, refetch=True))
        row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

        self.fig = Figure(figsize=(6, 7))
        self.canvas = Canvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        lay.addWidget(NavBar(self.canvas, self))
        lay.addWidget(self.canvas, 1)

        self.lbl = QtWidgets.QLabel('')
        self.lbl.setObjectName('legend')
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)

    # ------------------------------------------------------------- layers --
    def load_tif(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'GeoTIFF', basemap.CACHE_DIR and os.path.dirname(
                basemap.CACHE_DIR) or '',
            'GeoTIFF (*.tif *.tiff);;All (*)')
        if not p:
            return
        try:
            img, ext, epsg = basemap.read_geotiff(p)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                self, 'pyTECTOR',
                'Could not place this raster.\n\n%s' % exc)
            return
        self.tif = (img, ext, epsg, p)
        self.btn_clear_tif.setEnabled(True)
        self.redraw(refit=True, refetch=True)

    def clear_tif(self):
        self.tif = None
        self.btn_clear_tif.setEnabled(False)
        self.redraw()

    # -------------------------------------------------------------- draw --
    def set_records(self, recs):
        self.recs = recs
        self.redraw(refit=True, refetch=True)

    def _placed(self):
        out = []
        for r in self.recs:
            lon = survey._num(r.get('longitude'))
            lat = survey._num(r.get('latitude'))
            if lon is not None and lat is not None:
                out.append((r, lon, lat))
        return out

    def _phase_axis(self, phase, items):
        """Which axis to draw for one phase, honouring the selector."""
        mode = self.cmb_axis.currentText()
        if mode == 'sigma1':
            return ['sigma1']
        if mode == 'sigma3':
            return ['sigma3']
        if mode.startswith('sigma1 +'):
            return ['sigma1', 'sigma3']
        groups = {}
        for lab in ('sigma1', 'sigma3'):
            i = int(lab[-1])
            pairs = []
            for r in items:
                t = survey._num(r.get('s%d_trend' % i))
                p = survey._num(r.get('s%d_plunge' % i))
                if t is not None and p is not None:
                    pairs.append((t, p))
            groups[lab] = pairs
        lab, _why = rose.axis_for_regime([r.get('type') for r in items], groups)
        return [lab] if lab else []

    def redraw(self, refit=False, refetch=False):
        keep = None
        if not refit and self.ax.has_data():
            keep = (self.ax.get_xlim(), self.ax.get_ylim())
        self.ax.clear()

        placed = self._placed()
        if not placed:
            self.ax.set_axis_off()
            self.ax.text(0.5, 0.5,
                         'No station has coordinates yet.\n\nType them into '
                         'the lon and lat columns, or put a\n'
                         'coordinates.csv in py_data.',
                         ha='center', va='center', fontsize=9.5,
                         color='#7A776F', transform=self.ax.transAxes)
            self.canvas.draw_idle()
            self.lbl.setText('')
            return

        xs, ys = [], []
        for _r, lon, lat in placed:
            mx, my = basemap.lonlat_to_merc(lon, lat)
            xs.append(mx)
            ys.append(my)
        pad = max(1500.0, 0.18 * max(max(xs) - min(xs), max(ys) - min(ys)))
        box = (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)

        if self.chk_base.isChecked():
            if refetch or self._basemap_box != box:
                w, s = basemap.merc_to_lonlat(box[0], box[2])
                e, n = basemap.merc_to_lonlat(box[1], box[3])
                self._basemap = basemap.basemap(w, s, e, n)
                self._basemap_box = box
            img, ext = self._basemap or (None, None)
            if img is not None:
                self.ax.imshow(img, extent=ext, origin='upper', zorder=0,
                               interpolation='bilinear')

        if self.tif:
            img, ext, _epsg, _p = self.tif
            self.ax.imshow(img, extent=ext, origin='upper', zorder=1,
                           alpha=self.sl_alpha.value() / 100.0,
                           interpolation='bilinear')

        # The symbol length follows the view that is about to be shown, not
        # the one being replaced, so a Fit and a zoom both land right.
        view = keep[0] if (keep and not refit) else (box[0], box[1])
        half = (view[1] - view[0]) * HALF_FRAC * LENGTH_STEPS[
            self.cmb_len.currentText()]

        by_phase = {}
        for r, lon, lat in placed:
            by_phase.setdefault(str(r.get('stage', '')).strip()
                                or '(unassigned)', []).append((r, lon, lat))
        order = sorted(by_phase, key=lambda s: (s == '(unassigned)', s))

        drawn = steep = 0
        handles = []
        for i, phase in enumerate(order):
            items = by_phase[phase]
            colour = (UNASSIGNED if phase == '(unassigned)'
                      else PHASE_COLOURS[i % len(PHASE_COLOURS)])
            labels = self._phase_axis(phase, [r for r, _lo, _la in items])
            px, py = [], []
            for r, lon, lat in items:
                mx, my = basemap.lonlat_to_merc(lon, lat)
                px.append(mx)
                py.append(my)
                for lab in labels:
                    k = int(lab[-1])
                    t = survey._num(r.get('s%d_trend' % k))
                    p = survey._num(r.get('s%d_plunge' % k))
                    if t is None or p is None:
                        continue
                    if p >= rose.SHALLOW_LIMIT:
                        steep += 1
                        continue
                    # half is already in Mercator metres, the same units the
                    # axes are in, so no latitude correction belongs here:
                    # applying one would make the symbol a ground length again
                    th = math.radians(t)
                    dx, dy = half * math.sin(th), half * math.cos(th)
                    # dashed only when both axes are drawn at once, where the
                    # two would otherwise be indistinguishable
                    dashed = len(labels) > 1 and lab == 'sigma3'
                    self.ax.plot([mx - dx, mx + dx], [my - dy, my + dy],
                                 color=colour, lw=1.7, zorder=4,
                                 solid_capstyle='round',
                                 linestyle='--' if dashed else '-')
                    drawn += 1
            self.ax.plot(px, py, 'o', ms=3.4, color=colour, zorder=5,
                         markeredgecolor='white', markeredgewidth=0.6)
            handles.append(Line2D([], [], color=colour, marker='o', ms=5,
                                  lw=1.9,
                                  label='%s  (%d)' % (phase, len(items))))

        self.ax.set_xlim(box[0], box[1])
        self.ax.set_ylim(box[2], box[3])
        if keep and not refit:
            self.ax.set_xlim(*keep[0])
            self.ax.set_ylim(*keep[1])
        self.ax.set_aspect('equal')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for s in self.ax.spines.values():
            s.set_color('#B9B2A0')
        if handles:
            self.ax.legend(handles=handles, loc='upper left', fontsize=7.5,
                           framealpha=0.9, borderpad=0.5)
        self.fig.tight_layout(pad=0.6)
        self.canvas.draw_idle()

        bits = ['%d station(s) placed' % len(placed),
                '%d axis line(s)' % drawn]
        if steep:
            bits.append('%d too steep to draw' % steep)
        if self.tif:
            bits.append('GeoTIFF EPSG:%d  %s'
                        % (self.tif[2], os.path.basename(self.tif[3])))
        if self.chk_base.isChecked() and self._basemap and \
                self._basemap[0] is None:
            bits.append('tiles unavailable, drawing without a background')
        self.lbl.setText(',  '.join(bits))
