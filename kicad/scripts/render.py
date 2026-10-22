"""Photo-style PNG renders of both faces (black mask, white silk, HASL pads).

Each layer is plotted to SVG with kicad-cli, rasterised with rsvg-convert,
and the masks are composited with PIL."""
import os, subprocess, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
BOARD = os.path.join(PROJ, 'jar-radio.kicad_pcb')
IMG = os.path.join(PROJ, '..', 'docs', 'img')

COL = dict(bg=(0, 0, 0, 0), mask=(22, 24, 23), cu_under=(44, 50, 46), pad=(205, 205, 200),
           silk=(240, 240, 236), hole=(0, 0, 0, 0))


def layer_png(layer, d, width, mirror):
    svg = os.path.join(d, layer + '.svg'); png = os.path.join(d, layer + '.png')
    cmd = ['kicad-cli', 'pcb', 'export', 'svg', BOARD, '-o', svg, '--layers', layer + ',Edge.Cuts' if layer != 'Edge.Cuts' else layer,
           '--black-and-white', '--exclude-drawing-sheet', '--page-size-mode', '2', '--drill-shape-opt', '2']
    if mirror:
        cmd.append('--mirror')
    subprocess.run(cmd, capture_output=True, check=True)
    subprocess.run(['rsvg-convert', '-w', str(width), '-b', 'white', svg, '-o', png], check=True)
    a = np.asarray(Image.open(png).convert('L')) < 128
    return a


def render(face, width=1400):
    f = 'F' if face == 'top' else 'B'
    mirror = face == 'bottom'
    with tempfile.TemporaryDirectory() as d:
        edge = layer_png('Edge.Cuts', d, width, mirror)
        svg_text = open(os.path.join(d, 'Edge.Cuts.svg')).read()
        cu = layer_png(f + '.Cu', d, width, mirror)
        mask = layer_png(f + '.Mask', d, width, mirror)
        silk = layer_png(f + '.SilkS', d, width, mirror)
    h, w = edge.shape
    # board area: rasterise the real outline (outer edge minus cutouts) below;
    # drilled holes are punched afterwards from the real hole list
    from PIL import ImageDraw
    import pcbnew
    b = pcbnew.LoadBoard(BOARD)
    # kicad-cli plots onto a canvas a little larger than the board (the
    # edge line plus a margin); map holes through that same canvas
    import re as _re
    vb = [float(v) for v in _re.search(r'viewBox="([^"]+)"', svg_text).group(1).split()]
    bb = b.GetBoardEdgesBoundingBox()
    cxm = pcbnew.ToMM(bb.GetLeft()) + pcbnew.ToMM(bb.GetWidth()) / 2
    cym = pcbnew.ToMM(bb.GetTop()) + pcbnew.ToMM(bb.GetHeight()) / 2
    x0, y0 = cxm - vb[2] / 2, cym - vb[3] / 2
    sx = w / vb[2]
    def px(x, y):
        X = (x - x0) * sx
        return (w - X if mirror else X), (y - y0) * sx
    outl = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outl)
    mask_im = Image.new('L', (w, h), 0); md = ImageDraw.Draw(mask_im)
    for i in range(outl.OutlineCount()):
        ring = outl.Outline(i)
        md.polygon([px(pcbnew.ToMM(ring.CPoint(k).x), pcbnew.ToMM(ring.CPoint(k).y)) for k in range(ring.PointCount())], fill=255)
        for hh in range(outl.HoleCount(i)):
            hr = outl.Hole(i, hh)
            md.polygon([px(pcbnew.ToMM(hr.CPoint(k).x), pcbnew.ToMM(hr.CPoint(k).y)) for k in range(hr.PointCount())], fill=0)
    board = np.asarray(mask_im) > 0
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[board] = (*COL['mask'], 255)
    out[board & cu & ~mask] = (*COL['cu_under'], 255)
    out[board & mask] = (*COL['pad'], 255)
    out[board & silk & ~mask] = (*COL['silk'], 255)
    out[edge] = (60, 60, 60, 255)
    img = Image.fromarray(out, 'RGBA'); dr = ImageDraw.Draw(img)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetDrillSize().x <= 0:
                continue
            c = pad.GetPosition(); dx, dy = pcbnew.ToMM(pad.GetDrillSize().x) / 2, pcbnew.ToMM(pad.GetDrillSize().y) / 2
            ang = pad.GetOrientation().AsDegrees() % 180
            if 45 < ang < 135:
                dx, dy = dy, dx
            cx, cy = px(pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))
            r = min(dx, dy) * sx
            hx, hy = dx * sx, dy * sx
            dr.rounded_rectangle([cx - hx, cy - hy, cx + hx, cy + hy], radius=r, fill=(0, 0, 0, 0))
    out = np.asarray(img)
    Image.fromarray(out, 'RGBA').save(os.path.join(IMG, f'board-{face}.png'))
    return os.path.join(IMG, f'board-{face}.png')


if __name__ == '__main__':
    os.makedirs(IMG, exist_ok=True)
    print(render('top')); print(render('bottom'))
