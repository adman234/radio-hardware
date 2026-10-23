"""Trace a raster logo into a KiCad silkscreen footprint.

    python3 logo2fp.py SRC.png NAME HEIGHT_MM MODE

MODE picks which pixels are ink:
  dark    - anything that isn't near-white (KOPN logo on white)
  orange  - saturated orange on a dark background (CGW gear)
  disc    - light art inside a black disc (KOPN circle logo), plus a thin
            ring at the disc edge so the circle still reads on a black board

The bitmap is upscaled, thresholded and traced with potrace (geojson
backend), then each polygon with holes is cut into hole-free pieces so
KiCad can fill it, and written as fp_poly on F.SilkS. Placed on the bottom
side, KiCad mirrors it so it reads correctly from inside the jar.
"""
import json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, MultiPolygon, LineString, box
from shapely.ops import split, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'lib', 'jar-radio.pretty')


def ink_mask(img, mode):
    a = np.asarray(img.convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    if mode == 'dark':
        return (r + g + b) / 3 < 200
    if mode == 'orange':
        return (r > 120) & (r - b > 60) & (r - g > 40)
    if mode == 'disc':
        dark = (r + g + b) / 3 < 60
        ys, xs = np.nonzero(dark)
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        rad = (xs.max() - xs.min()) / 2
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        d = np.hypot(xx - cx, yy - cy)
        light = (r + g + b) / 3 > 110
        ring = (d <= rad) & (d > rad * (1 - 0.016))          # ~0.25 mm at 15.5 mm
        return (light & (d < rad * 0.985)) | ring
    raise SystemExit('unknown mode ' + mode)


def trace(mask, scale):
    with tempfile.TemporaryDirectory() as d:
        im = Image.fromarray(np.where(mask, 0, 255).astype('uint8'))
        im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
        im = im.point(lambda v: 0 if v < 128 else 255).convert('1')
        pbm = os.path.join(d, 'in.pbm')
        im.save(pbm)
        out = os.path.join(d, 'out.json')
        subprocess.run(['potrace', '-b', 'geojson', '-t', str(4 * scale), '-a', '1.0',
                        '-O', '0.4', '-o', out, pbm], check=True)
        gj = json.load(open(out))
        return gj, im.height


def rings_to_polys(gj):
    """potrace geojson gives rings; nest them by containment (even-odd)."""
    rings = []
    for f in gj['features']:
        geo = f['geometry']
        coords = geo['coordinates']
        if geo['type'] == 'Polygon':
            coords = [coords]
        for poly in coords:
            for ring in poly:
                p = Polygon(ring)
                if p.is_valid and p.area > 0:
                    rings.append(p)
                elif p.area > 0:
                    rings.append(p.buffer(0))
    rings.sort(key=lambda p: -p.area)
    depth = []
    for i, p in enumerate(rings):
        depth.append(sum(1 for q in rings[:i] if q.contains(p.representative_point())))
    shapes = None
    for p, d in zip(rings, depth):
        shapes = p if shapes is None else (shapes.union(p) if d % 2 == 0 else shapes.difference(p))
    return shapes


def no_holes(geom):
    """Cut polygons along vertical lines through each hole until none remain."""
    todo = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    done = []
    while todo:
        p = todo.pop()
        if p.is_empty or p.area < 1e-6:
            continue
        if not p.interiors:
            done.append(p)
            continue
        x = Polygon(p.interiors[0]).representative_point().x
        minx, miny, maxx, maxy = p.bounds
        parts = split(p, LineString([(x, miny - 1), (x, maxy + 1)]))
        for q in parts.geoms:
            if isinstance(q, Polygon):
                todo.append(q)
    return done


def main(src, name, height_mm, mode, scale=4):
    img = Image.open(src)
    mask = ink_mask(img, mode)
    ys, xs = np.nonzero(mask)
    pad = 2
    mask = mask[max(ys.min() - pad, 0):ys.max() + pad + 1, max(xs.min() - pad, 0):xs.max() + pad + 1]
    gj, hpx = trace(mask, scale)
    shapes = rings_to_polys(gj)
    minx, miny, maxx, maxy = shapes.bounds
    k = height_mm / (maxy - miny)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    polys = no_holes(shapes.simplify(0.6 / k * 0.05))
    lines = [f'(footprint "{name}" (version 20221018) (generator jar_radio_gen)',
             '  (layer "F.Cu")', f'  (descr "Silkscreen artwork traced from {os.path.basename(src)}, {height_mm} mm tall")',
             '  (attr exclude_from_pos_files exclude_from_bom allow_missing_courtyard)',
             '  (fp_text reference "REF**" (at 0 0) (layer "F.SilkS") hide (effects (font (size 1 1) (thickness 0.15))))',
             f'  (fp_text value "{name}" (at 0 1) (layer "F.Fab") hide (effects (font (size 1 1) (thickness 0.15))))']
    for p in polys:
        # potrace y axis points up; KiCad y points down
        pts = ' '.join(f'(xy {(x - cx) * k:.3f} {-(y - cy) * k:.3f})' for x, y in list(p.exterior.coords)[:-1])
        lines.append(f'  (fp_poly (pts {pts}) (stroke (width 0) (type solid)) (fill solid) (layer "F.SilkS"))')
    lines.append(')')
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + '.kicad_mod')
    open(path, 'w').write('\n'.join(lines) + '\n')
    w = (maxx - minx) * k
    print(f'{path}: {len(polys)} polygons, {w:.1f} x {height_mm} mm')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4])
