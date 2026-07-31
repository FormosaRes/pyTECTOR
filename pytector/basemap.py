# -*- coding: utf-8 -*-
"""Slippy-map tiles and GeoTIFF reading, with no new dependencies.

A stress map is only readable against something: a coastline, a river, a
geological sheet. This fetches OpenStreetMap tiles for the background and
reads a north-up GeoTIFF for anything the user brings, using nothing beyond
what the program already installs. numpy and matplotlib were already required,
Pillow arrives with matplotlib, and the tile fetch is urllib.

rasterio and GDAL would do the second job better and are not here on purpose.
Both are large, both are awkward to install on Windows, and the one-click
setup promises four packages. A north-up GeoTIFF in a projection this module
knows is the common case and needs neither.

Projections, and what is deliberately not supported. Tiles are Web Mercator
and stations are longitude and latitude, so those two are always available.
For a GeoTIFF the module reads the projection out of the file's own keys and
handles the ones a Taiwanese data set actually arrives in:

    4326    longitude and latitude
    3857    Web Mercator, what the tiles use
    3826    TWD97 / TM2 zone 121, the national grid
    32651   UTM zone 51N, what a hand-held GPS exports here

Anything else is refused by name rather than being drawn in the wrong place.
A raster silently offset by a few hundred metres is worse than no raster: it
looks right.
"""
import io
import math
import os
import threading

import numpy as np

#: Earth radius used by Web Mercator, metres
R = 6378137.0
#: WGS84 ellipsoid, for the transverse Mercator cases
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2 - _F)

TILE = 256
#: Tile server. OSM asks for a real User-Agent and no bulk downloading; this
#: caches every tile to disk and a survey needs a few dozen, which is well
#: inside their policy for an application like this.
TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
USER_AGENT = 'pyTECTOR palaeostress tool (https://github.com/FormosaRes/pyTECTOR)'

#: Where fetched tiles are kept. Under py_data because that whole tree is
#: already gitignored, and a tile cache is not source.
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'py_data', '.tilecache')

#: EPSG -> (central meridian, scale factor, false easting, false northing)
_TM = {3826: (121.0, 0.9999, 250000.0, 0.0),
       32651: (123.0, 0.9996, 500000.0, 0.0)}
SUPPORTED = 'EPSG 4326, 3857, 3826 (TWD97 TM2) and 32651 (UTM 51N)'


# ------------------------------------------------------------ projections --

def lonlat_to_merc(lon, lat):
    """Longitude and latitude to Web Mercator metres."""
    lat = max(-85.05112878, min(85.05112878, float(lat)))
    x = R * math.radians(float(lon))
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def merc_to_lonlat(x, y):
    return (math.degrees(x / R),
            math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2))


def _tm_inverse(east, north, lon0, k0, fe, fn):
    """Transverse Mercator to longitude and latitude, WGS84.

    Standard series solution. Accurate to well under a metre inside a zone,
    which is far better than the data being plotted on it.
    """
    x, y = east - fe, north - fn
    e2 = _E2
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    m = y / k0
    mu = m / (_A * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    phi1 = (mu
            + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    s, c, t = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    ep2 = e2 / (1 - e2)
    c1 = ep2 * c * c
    t1 = t * t
    n1 = _A / math.sqrt(1 - e2 * s * s)
    r1 = _A * (1 - e2) / (1 - e2 * s * s) ** 1.5
    d = x / (n1 * k0)
    lat = phi1 - (n1 * t / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2
           - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d
           - (1 + 2 * t1 + c1) * d ** 3 / 6
           + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2
              + 24 * t1 ** 2) * d ** 5 / 120) / c
    return math.degrees(lon) + lon0, math.degrees(lat)


def to_merc(x, y, epsg):
    """Any supported CRS to Web Mercator metres."""
    epsg = int(epsg)
    if epsg == 3857:
        return float(x), float(y)
    if epsg == 4326:
        return lonlat_to_merc(x, y)
    if epsg in _TM:
        return lonlat_to_merc(*_tm_inverse(x, y, *_TM[epsg]))
    raise ValueError('unsupported CRS EPSG:%d. Supported: %s'
                     % (epsg, SUPPORTED))


# ------------------------------------------------------------------ tiles --

def _tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(max(-85.05112878, min(85.05112878, lat)))
    y = (1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n
    return x, y


def _tile_bounds_merc(x, y, z):
    """Web Mercator extent of one tile."""
    n = 2 ** z
    span = 2 * math.pi * R / n
    return (-math.pi * R + x * span, math.pi * R - (y + 1) * span,
            -math.pi * R + (x + 1) * span, math.pi * R - y * span)


def _fetch_tile(z, x, y, timeout=8.0):
    """One tile as an RGB array, from the disk cache when possible."""
    from PIL import Image
    path = os.path.join(CACHE_DIR, str(z), str(x), '%d.png' % y)
    if os.path.exists(path):
        try:
            with Image.open(path) as im:
                return np.asarray(im.convert('RGB'))
        except Exception:
            pass                       # a truncated cache file, refetch it

    try:
        from urllib.request import Request, urlopen
    except ImportError:              # pragma: no cover
        return None
    url = TILE_URL.format(z=z, x=x, y=y)
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT})
        data = urlopen(req, timeout=timeout).read()
    except Exception:
        return None
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        try:
            os.makedirs(d)
        except OSError:
            pass
    try:
        with open(path, 'wb') as fh:
            fh.write(data)
    except OSError:
        pass
    try:
        with Image.open(io.BytesIO(data)) as im:
            return np.asarray(im.convert('RGB'))
    except Exception:
        return None


def pick_zoom(west, south, east, north, px=900, zmax=17):
    """The largest zoom whose tiles still fit a canvas of about `px` pixels."""
    lon_span = max(1e-6, east - west)
    for z in range(zmax, 0, -1):
        if (lon_span / 360.0) * (2 ** z) * TILE <= px * 1.6:
            return z
    return 1


def basemap(west, south, east, north, zoom=None, px=900, max_tiles=64):
    """OSM tiles covering a longitude/latitude box.

    Returns (image, extent_in_mercator_metres) or (None, None) when the tiles
    cannot be had: no network, or the box needs more of them than max_tiles.
    Failing to a blank background is correct; the stations are the data and
    they must still draw.
    """
    if zoom is None:
        zoom = pick_zoom(west, south, east, north, px)
    x0, y1 = _tile_xy(west, south, zoom)
    x1, y0 = _tile_xy(east, north, zoom)
    xa, xb = int(math.floor(min(x0, x1))), int(math.floor(max(x0, x1)))
    ya, yb = int(math.floor(min(y0, y1))), int(math.floor(max(y0, y1)))
    n = 2 ** zoom
    xa, xb = max(0, xa), min(n - 1, xb)
    ya, yb = max(0, ya), min(n - 1, yb)
    nx, ny = xb - xa + 1, yb - ya + 1
    if nx * ny > max_tiles:
        return None, None

    canvas = np.full((ny * TILE, nx * TILE, 3), 255, np.uint8)
    got = 0
    results = {}

    def work(tx, ty):
        results[(tx, ty)] = _fetch_tile(zoom, tx, ty)

    threads = []
    for ty in range(ya, yb + 1):
        for tx in range(xa, xb + 1):
            t = threading.Thread(target=work, args=(tx, ty))
            t.daemon = True
            t.start()
            threads.append(t)
    for t in threads:
        t.join(timeout=12.0)

    for ty in range(ya, yb + 1):
        for tx in range(xa, xb + 1):
            img = results.get((tx, ty))
            if img is None:
                continue
            r, c = (ty - ya) * TILE, (tx - xa) * TILE
            canvas[r:r + TILE, c:c + TILE] = img[:TILE, :TILE]
            got += 1
    if not got:
        return None, None

    w0, s0, _e0, _n0 = _tile_bounds_merc(xa, yb, zoom)
    _w1, _s1, e1, n1 = _tile_bounds_merc(xb, ya, zoom)
    return canvas, (w0, e1, s0, n1)


# --------------------------------------------------------------- GeoTIFF --

#: TIFF tags that carry the georeferencing
_TAG_PIXEL_SCALE = 33550
_TAG_TIEPOINT = 33922
_TAG_TRANSFORM = 34264
_TAG_GEOKEYS = 34735
#: GeoKey ids for the projected and the geographic CRS
_KEY_PROJECTED = 3072
_KEY_GEOGRAPHIC = 2048


def _geokeys(tags):
    """{key id: value} out of the GeoKeyDirectory, ints only.

    The directory is a flat list of 4-tuples after a 4-value header. Entries
    whose location field is non-zero point into other tags for a string or a
    double; those are not needed here and are skipped.
    """
    raw = tags.get(_TAG_GEOKEYS)
    if not raw or len(raw) < 8:
        return {}
    out = {}
    for i in range(4, len(raw) - 3, 4):
        key, loc, count, value = raw[i:i + 4]
        if loc == 0 and count == 1:
            out[int(key)] = int(value)
    return out


def read_geotiff(path, max_px=2400):
    """A north-up GeoTIFF as (image, extent_in_mercator, epsg).

    extent is (left, right, bottom, top) in Web Mercator metres, ready for
    imshow on the same axes as the basemap.

    Raises ValueError with a plain reason when the file cannot be placed:
    no georeferencing, a rotated or sheared transform, or a CRS this module
    does not know. Every one of those would otherwise put the raster somewhere
    convincing and wrong.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(path)
    tags = dict(getattr(im, 'tag_v2', {}) or {})

    scale = tags.get(_TAG_PIXEL_SCALE)
    tie = tags.get(_TAG_TIEPOINT)
    if scale and tie and len(tie) >= 6:
        sx, sy = float(scale[0]), float(scale[1])
        i, j, _k, x0, y0, _z0 = [float(v) for v in tie[:6]]
        left = x0 - i * sx
        top = y0 + j * sy
    elif tags.get(_TAG_TRANSFORM) and len(tags[_TAG_TRANSFORM]) >= 16:
        m = [float(v) for v in tags[_TAG_TRANSFORM]]
        if abs(m[1]) > 1e-9 or abs(m[4]) > 1e-9:
            raise ValueError(
                'the raster is rotated or sheared. This reader only places '
                'north-up images; reproject it to north-up first.')
        sx, sy = abs(m[0]), abs(m[5])
        left, top = m[3], m[7]
    else:
        raise ValueError(
            'no georeferencing in this TIFF: it has neither a pixel scale '
            'with a tie point nor a model transform. A plain TIFF cannot be '
            'placed on a map.')

    gk = _geokeys(tags)
    epsg = gk.get(_KEY_PROJECTED) or gk.get(_KEY_GEOGRAPHIC)
    if not epsg:
        # A file with metre-sized pixels is projected; degrees-sized is not.
        # Guessing between grids would be reckless, so only the geographic
        # case is assumed, and only when the numbers can be nothing else.
        if sx < 0.01 and abs(left) <= 180:
            epsg = 4326
        else:
            raise ValueError(
                'this TIFF carries no CRS. Supported: %s. Assign one in QGIS '
                'and export again.' % SUPPORTED)
    if int(epsg) not in (4326, 3857) and int(epsg) not in _TM:
        raise ValueError('CRS EPSG:%d is not supported. Supported: %s.'
                         % (int(epsg), SUPPORTED))

    w, h = im.size
    step = max(1, int(math.ceil(max(w, h) / float(max_px))))
    if step > 1:
        im = im.resize((max(1, w // step), max(1, h // step)), Image.BILINEAR)
    arr = np.asarray(im.convert('RGBA'))

    right = left + w * sx
    bottom = top - h * sy
    # corners are enough: the supported projections are all conformal and
    # north-up here, so the box maps to a box closely enough for a backdrop
    xs, ys = [], []
    for cx, cy in ((left, bottom), (right, bottom), (left, top), (right, top)):
        mx, my = to_merc(cx, cy, epsg)
        xs.append(mx)
        ys.append(my)
    return arr, (min(xs), max(xs), min(ys), max(ys)), int(epsg)
