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

from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

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


def layers_icon(px=30):
    """The stacked-sheets mark every web map uses for its layer control.

    Drawn rather than shipped as a file: it is four strokes, and a PNG in the
    repository would be one more thing to keep in step with the interface's
    own colours.
    """
    img = QtGui.QPixmap(px, px)
    img.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    pen = QtGui.QPen(QtGui.QColor('#1E1E1C'))
    pen.setWidthF(px * 0.085)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    cx, w, h = px / 2.0, px * 0.32, px * 0.17
    for i, cy in enumerate((px * 0.34, px * 0.53, px * 0.70)):
        if i == 0:                      # the top sheet is a full diamond
            path = QtGui.QPainterPath()
            path.moveTo(cx, cy - h)
            path.lineTo(cx + w, cy)
            path.lineTo(cx, cy + h)
            path.lineTo(cx - w, cy)
            path.closeSubpath()
            p.drawPath(path)
        else:                           # the ones under it are just a chevron
            path = QtGui.QPainterPath()
            path.moveTo(cx - w, cy - h * 0.35)
            path.lineTo(cx, cy + h * 0.55)
            path.lineTo(cx + w, cy - h * 0.35)
            p.drawPath(path)
    p.end()
    return QtGui.QIcon(img)


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
        b = QtWidgets.QPushButton('Fit')
        b.setToolTip('Zoom to the stations')
        b.clicked.connect(lambda: self.redraw(refit=True, refetch=True))
        row.addWidget(b)
        b = QtWidgets.QPushButton('Save image...')
        b.setToolTip('Write the map as it stands to a PNG')
        b.clicked.connect(self.save_png)
        row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

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

        self._build_layers()

    # ------------------------------------------------------------ layers --
    def _build_layers(self):
        """The layer control, floating over the map as a web map's does.

        A row of checkboxes and combo boxes above the figure was taking the
        height the map wanted and still did not say what was a layer and what
        was a drawing option. Here they are grouped and out of the way until
        the button is pressed.
        """
        self.btn_layers = QtWidgets.QToolButton(self.canvas)
        self.btn_layers.setIcon(layers_icon(30))
        self.btn_layers.setIconSize(QtCore.QSize(26, 26))
        self.btn_layers.setFixedSize(36, 36)
        self.btn_layers.setCursor(QtCore.Qt.ArrowCursor)
        self.btn_layers.setToolTip('Layers')
        self.btn_layers.setStyleSheet(
            'QToolButton{background:rgba(255,255,255,235);'
            'border:1px solid #C9C4B4;border-radius:18px;}'
            'QToolButton:hover{background:#FFFFFF;}')
        self.btn_layers.clicked.connect(self._toggle_layers)

        self.pnl_layers = QtWidgets.QFrame(self.canvas)
        self.pnl_layers.setStyleSheet(
            'QFrame{background:rgba(255,255,255,242);'
            'border:1px solid #C9C4B4;border-radius:6px;}')
        self.pnl_layers.setVisible(False)
        v = QtWidgets.QVBoxLayout(self.pnl_layers)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(5)

        def heading(text):
            la = QtWidgets.QLabel(text)
            la.setStyleSheet('border:none;color:#7A776F;font-size:10px;')
            return la

        v.addWidget(heading('BASE MAP'))
        self.chk_base = QtWidgets.QCheckBox('OpenStreetMap')
        self.chk_base.setChecked(True)
        self.chk_base.setStyleSheet('border:none;')
        self.chk_base.setToolTip(
            'Tiles, cached in py_data/.tilecache after the first fetch. Needs '
            'the network only the first time for a given area.')
        self.chk_base.stateChanged.connect(lambda _s: self.redraw(refetch=True))
        v.addWidget(self.chk_base)

        v.addWidget(heading('OVERLAY'))
        rw = QtWidgets.QHBoxLayout()
        rw.setSpacing(4)
        self.chk_tif = QtWidgets.QCheckBox('(no raster)')
        self.chk_tif.setChecked(True)
        self.chk_tif.setEnabled(False)
        self.chk_tif.setStyleSheet('border:none;')
        self.chk_tif.stateChanged.connect(lambda _s: self.redraw())
        rw.addWidget(self.chk_tif, 1)
        b = QtWidgets.QToolButton()
        b.setText('...')
        b.setToolTip('Load a north-up GeoTIFF. Supported: %s'
                     % basemap.SUPPORTED)
        b.clicked.connect(self.load_tif)
        rw.addWidget(b)
        self.btn_clear_tif = QtWidgets.QToolButton()
        self.btn_clear_tif.setText('x')
        self.btn_clear_tif.setToolTip('Remove the raster')
        self.btn_clear_tif.setEnabled(False)
        self.btn_clear_tif.clicked.connect(self.clear_tif)
        rw.addWidget(self.btn_clear_tif)
        v.addLayout(rw)

        self.sl_alpha = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sl_alpha.setRange(0, 100)
        self.sl_alpha.setValue(70)
        self.sl_alpha.setToolTip('Raster opacity')
        self.sl_alpha.setStyleSheet('border:none;')
        self.sl_alpha.valueChanged.connect(lambda _v: self.redraw())
        v.addWidget(self.sl_alpha)

        v.addWidget(heading('SYMBOLS'))
        for w, tip in ((self._combo('cmb_axis',
                                    ['axis by regime', 'sigma1', 'sigma3',
                                     'sigma1 + sigma3']),
                        'Which axis to draw. By regime is sigma3 for a normal '
                        'phase and sigma1 for a thrust or strike-slip one, '
                        'decided per phase from the type column.'),
                       (self._combo('cmb_style',
                                    ['line', 'arrows']),
                        'A plain line, or the usual palaeostress arrows: '
                        'sigma1 pointing inwards for compression, sigma3 '
                        'outwards for extension.'),
                       (self._combo('cmb_len', list(LENGTH_STEPS), 'normal'),
                        'Symbol length, relative to the width of the view.')):
            w.setToolTip(tip)
            v.addWidget(w)

        v.addWidget(heading('PHASES'))
        self.phase_box = QtWidgets.QWidget()
        self.phase_box.setStyleSheet('border:none;')
        self.phase_lay = QtWidgets.QVBoxLayout(self.phase_box)
        self.phase_lay.setContentsMargins(0, 0, 0, 0)
        self.phase_lay.setSpacing(2)
        v.addWidget(self.phase_box)
        self.phase_checks = {}

        rw = QtWidgets.QHBoxLayout()
        rw.setSpacing(4)
        for text, on in (('all', True), ('none', False)):
            b = QtWidgets.QToolButton()
            b.setText(text)
            b.clicked.connect(lambda _c, s=on: self._set_all_phases(s))
            rw.addWidget(b)
        rw.addStretch(1)
        v.addLayout(rw)
        self._place_layers()

    def _combo(self, name, items, current=None):
        c = QtWidgets.QComboBox()
        c.addItems(items)
        if current:
            c.setCurrentText(current)
        c.setStyleSheet('border:1px solid #C9C4B4;')
        c.currentIndexChanged.connect(lambda _i: self.redraw())
        setattr(self, name, c)
        return c

    def _toggle_layers(self):
        self.pnl_layers.setVisible(not self.pnl_layers.isVisible())
        self._place_layers()

    def _place_layers(self):
        w = self.canvas.width()
        self.btn_layers.move(max(6, w - 46), 10)
        self.btn_layers.raise_()
        self.pnl_layers.adjustSize()
        self.pnl_layers.move(max(6, w - self.pnl_layers.width() - 10), 52)
        self.pnl_layers.raise_()

    def resizeEvent(self, ev):
        super(MapPanel, self).resizeEvent(ev)
        self._place_layers()

    def _set_all_phases(self, on):
        for c in self.phase_checks.values():
            c.blockSignals(True)
            c.setChecked(on)
            c.blockSignals(False)
        self.redraw()

    def _sync_phase_checks(self, order, counts, colours):
        """Rebuild the phase list, keeping whatever was already unticked."""
        want = list(order)
        if want == list(self.phase_checks):
            for ph in want:
                self.phase_checks[ph].setText('%s  (%d)' % (ph, counts[ph]))
            return
        prev = {ph: c.isChecked() for ph, c in self.phase_checks.items()}
        for c in self.phase_checks.values():
            self.phase_lay.removeWidget(c)
            c.deleteLater()
        self.phase_checks = {}
        for ph in want:
            c = QtWidgets.QCheckBox('%s  (%d)' % (ph, counts[ph]))
            c.setChecked(prev.get(ph, True))
            c.setStyleSheet('border:none;color:%s;' % colours[ph])
            c.stateChanged.connect(lambda _s: self.redraw())
            self.phase_lay.addWidget(c)
            self.phase_checks[ph] = c
        self._place_layers()

    def visible_phases(self):
        return {ph for ph, c in self.phase_checks.items() if c.isChecked()}

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
        self.chk_tif.setText(os.path.basename(p))
        self.chk_tif.setChecked(True)
        self.chk_tif.setEnabled(True)
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
        self.chk_tif.setText('(no raster)')
        self.chk_tif.setEnabled(False)
        self.btn_clear_tif.setEnabled(False)
        self.redraw()

    # -------------------------------------------------------------- draw --
    def set_records(self, recs):
        self.recs = recs
        self.redraw(refit=True, refetch=True)

    def _arrow_pair(self, mx, my, dx, dy, colour, inward):
        """The palaeostress arrow pair, both halves of one axis.

        Convention, and it is not decoration: sigma1 is drawn pointing IN
        towards the station because compression pushes, sigma3 pointing OUT
        because extension pulls. Two arrows rather than one, for the same
        reason the plain symbol is a line through the station and not a
        half-line: an axis has no single sense, and one arrow would assert a
        direction the data does not contain.
        """
        gap = 0.22            # leave the station dot visible in the middle
        for sx, sy in ((1.0, 1.0), (-1.0, -1.0)):
            outer = (mx + dx * sx, my + dy * sy)
            inner = (mx + dx * gap * sx, my + dy * gap * sy)
            tail, head = (outer, inner) if inward else (inner, outer)
            self.ax.add_patch(FancyArrowPatch(
                tail, head, arrowstyle='-|>', mutation_scale=9,
                color=colour, lw=1.5, zorder=4, shrinkA=0, shrinkB=0,
                joinstyle='miter'))

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

        if self.tif and self.chk_tif.isChecked():
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
        colours = {ph: (UNASSIGNED if ph == '(unassigned)'
                        else PHASE_COLOURS[i % len(PHASE_COLOURS)])
                   for i, ph in enumerate(order)}
        self._sync_phase_checks(order, {p: len(by_phase[p]) for p in order},
                                colours)
        shown = self.visible_phases()
        arrows = self.cmb_style.currentText() == 'arrows'

        drawn = steep = hidden = 0
        handles = []
        for phase in order:
            items = by_phase[phase]
            if phase not in shown:
                hidden += len(items)
                continue
            colour = colours[phase]
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
                    if arrows:
                        self._arrow_pair(mx, my, dx, dy, colour,
                                         inward=(lab == 'sigma1'))
                    else:
                        # dashed only when both axes are drawn at once, where
                        # the two would otherwise be indistinguishable
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
                '%d symbol(s)' % drawn]
        if hidden:
            bits.append('%d hidden by the phase filter' % hidden)
        if steep:
            bits.append('%d too steep to draw' % steep)
        if self.tif:
            bits.append('GeoTIFF %s  %s'
                        % (self.tif[2], os.path.basename(self.tif[3])))
        if self.chk_base.isChecked() and self._basemap and \
                self._basemap[0] is None:
            bits.append('tiles unavailable, drawing without a background')
        self.lbl.setText(',  '.join(bits))
