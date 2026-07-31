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

        b = QtWidgets.QPushButton('Save image...')
        b.setToolTip('Write the map as it stands to a PNG')
        b.clicked.connect(self.save_png)
        row.addWidget(b)

        self.fig = Figure(figsize=(6, 7))
        self.canvas = Canvas(self.fig)
        # The axes fill the figure. A map does not want a title, tick labels
        # or a margin, and the default subplot padding was drawing four white
        # bands around it.
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.canvas.setCursor(QtCore.Qt.OpenHandCursor)
        lay.addWidget(self.canvas, 1)

        # Wheel to zoom, drag to pan. The matplotlib navigation bar was here
        # and has gone: home / back / forward / subplots / customise are not
        # what a map wants, and the two things it does want were behind modal
        # buttons that had to be turned on and off again.
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.canvas.mpl_connect('button_press_event', self._on_press)
        self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self._drag = None
        self._tile_timer = QtCore.QTimer(self)
        self._tile_timer.setSingleShot(True)
        self._tile_timer.setInterval(320)
        self._tile_timer.timeout.connect(self._refresh_tiles)

        self.lbl = QtWidgets.QLabel('')
        self.lbl.setObjectName('legend')
        self.lbl.setWordWrap(True)
        lay.addWidget(self.lbl)

    # ----------------------------------------------------------- gestures --
    def _on_scroll(self, ev):
        if ev.inaxes is not self.ax or ev.xdata is None:
            return
        f = 0.8 if ev.button == 'up' else 1.25
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        # keep the point under the cursor where it is, which is what makes
        # wheel zoom feel like a map rather than like a plot
        self.ax.set_xlim(ev.xdata + (x0 - ev.xdata) * f,
                         ev.xdata + (x1 - ev.xdata) * f)
        self.ax.set_ylim(ev.ydata + (y0 - ev.ydata) * f,
                         ev.ydata + (y1 - ev.ydata) * f)
        self._after_gesture()

    def _on_press(self, ev):
        if ev.inaxes is not self.ax or ev.button != 1 or ev.xdata is None:
            return
        self._drag = (ev.xdata, ev.ydata,
                      self.ax.get_xlim(), self.ax.get_ylim())
        self.canvas.setCursor(QtCore.Qt.ClosedHandCursor)

    def _on_motion(self, ev):
        if not self._drag or ev.x is None:
            return
        # work in pixels: the data coordinate under the cursor moves as the
        # limits move, so using ev.xdata here makes the map slide away
        x0, y0, xlim, ylim = self._drag
        inv = self.ax.transData.inverted()
        try:
            cx, cy = inv.transform((ev.x, ev.y))
        except Exception:
            return
        dx, dy = x0 - cx, y0 - cy
        self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
        self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
        self.canvas.draw_idle()

    def _on_release(self, ev):
        if not self._drag:
            return
        self._drag = None
        self.canvas.setCursor(QtCore.Qt.OpenHandCursor)
        self._after_gesture()

    def _after_gesture(self):
        """Redraw now, refetch tiles once the gesture has settled.

        Tiles are the slow part and a wheel is a stream of events, so the
        picture follows the hand immediately and the background catches up.
        """
        self.canvas.draw_idle()
        self._tile_timer.start()

    def _refresh_tiles(self):
        self.redraw(refetch=True)

    def save_png(self):
        p, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save the map', 'stress_map.png', 'PNG (*.png)')
        if p:
            self.fig.savefig(p, dpi=220, facecolor='white')
            self.lbl.setText('written to %s' % p)

    # ------------------------------------------------------------- layers --
    def load_tif(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'GeoTIFF', basemap.CACHE_DIR and os.path.dirname(
                basemap.CACHE_DIR) or '',
            'GeoTIFF (*.tif *.tiff);;All (*)')
        if not p:
            return
        force = None
        while True:
            try:
                img, ext, label = basemap.read_geotiff(p, force=force)
                break
            except Exception as exc:
                # Offer the choice rather than just refusing. The file's own
                # metadata is often the only thing missing, and the user can
                # read it in QGIS when this cannot.
                force = self._ask_crs(str(exc))
                if force is None:
                    return
        self.tif = (img, ext, label, p)
        self.btn_clear_tif.setEnabled(True)
        self.redraw(refit=True, refetch=True)

    #: what the manual chooser offers, label -> crs for basemap.to_merc
    CRS_CHOICES = [
        ('TWD97 / TM2 zone 121  (EPSG:3826)', 3826),
        ('UTM zone 51N, WGS84  (EPSG:32651)', 32651),
        ('Longitude / latitude, WGS84  (EPSG:4326)', 4326),
        ('Web Mercator  (EPSG:3857)', 3857),
        ('TWD67 / TM2 zone 121', (121.0, 0.9999, 250000.0, 0.0)),
    ]

    def _ask_crs(self, why):
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle('pyTECTOR')
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setText('This raster cannot be placed from what it says about '
                    'itself.')
        box.setInformativeText('%s\n\nChoose the projection it is in, if you '
                               'know it.' % why)
        combo = QtWidgets.QComboBox()
        combo.addItems([c[0] for c in self.CRS_CHOICES])
        box.layout().addWidget(combo, 1, 1)
        box.setStandardButtons(QtWidgets.QMessageBox.Ok
                               | QtWidgets.QMessageBox.Cancel)
        if box.exec_() != QtWidgets.QMessageBox.Ok:
            return None
        return self.CRS_CHOICES[combo.currentIndex()][1]

    def clear_tif(self):
        self.tif = None
        self.btn_clear_tif.setEnabled(False)
        self.redraw()

    # -------------------------------------------------------------- draw --
    def set_records(self, recs):
        self.recs = recs
        self.redraw(refit=True, refetch=True)

    def _fill(self, box):
        """Grow a box to the canvas's own shape.

        A map has to be at equal aspect or the axes come out at the wrong
        angles, and an equal-aspect axes whose limits are a different shape
        from the widget gets letterboxed: white bands down both sides, which
        is what this panel was doing. Widening the view instead of shrinking
        it means nothing that was visible disappears.
        """
        x0, x1, y0, y1 = box
        w, h = max(1.0, self.canvas.width()), max(1.0, self.canvas.height())
        want = w / h
        dx, dy = x1 - x0, y1 - y0
        if dy <= 0 or dx <= 0:
            return box
        if dx / dy < want:
            grow = (dy * want - dx) / 2.0
            return x0 - grow, x1 + grow, y0, y1
        grow = (dx / want - dy) / 2.0
        return x0, x1, y0 - grow, y1 + grow

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
        pad = max(1500.0, 0.12 * max(max(xs) - min(xs), max(ys) - min(ys)))
        box = self._fill((min(xs) - pad, max(xs) + pad,
                          min(ys) - pad, max(ys) + pad))

        # What will actually be on screen. After a pan or a zoom that is the
        # kept limits, not the extent of the data, and both the tiles and the
        # symbol length have to follow it or the background stays behind.
        if keep and not refit:
            view = (keep[0][0], keep[0][1], keep[1][0], keep[1][1])
        else:
            view = box

        if self.chk_base.isChecked():
            if refetch or self._basemap_box != view:
                w, s = basemap.merc_to_lonlat(view[0], view[2])
                e, n = basemap.merc_to_lonlat(view[1], view[3])
                px = max(400, self.canvas.width())
                self._basemap = basemap.basemap(w, s, e, n, px=px)
                self._basemap_box = view
            img, ext = self._basemap or (None, None)
            if img is not None:
                self.ax.imshow(img, extent=ext, origin='upper', zorder=0,
                               interpolation='bilinear')

        if self.tif:
            img, ext, _label, _p = self.tif
            self.ax.imshow(img, extent=ext, origin='upper', zorder=1,
                           alpha=self.sl_alpha.value() / 100.0,
                           interpolation='bilinear')

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

        self.ax.set_xlim(view[0], view[1])
        self.ax.set_ylim(view[2], view[3])
        self.ax.set_aspect('equal')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for s in self.ax.spines.values():
            s.set_color('#B9B2A0')
        if handles:
            self.ax.legend(handles=handles, loc='upper left', fontsize=7.5,
                           framealpha=0.9, borderpad=0.5)
        # no tight_layout: the axes already fill the figure, and calling it
        # would put the margins back
        self.canvas.draw_idle()

        bits = ['%d station(s) placed' % len(placed),
                '%d axis line(s)' % drawn]
        if steep:
            bits.append('%d too steep to draw' % steep)
        if self.tif:
            bits.append('GeoTIFF %s  %s'
                        % (self.tif[2], os.path.basename(self.tif[3])))
        if self.chk_base.isChecked() and self._basemap and \
                self._basemap[0] is None:
            bits.append('tiles unavailable, drawing without a background')
        self.lbl.setText(',  '.join(bits))
