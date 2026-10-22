"""Adds GND stitching vias wherever they fit, so the inside-face ground
islands between parts join the solid ground on the outside face."""
import math
import pcbnew
from gen_pcb import CX, CY, P, GEOM
from shapely.geometry import Point
import edges

VIA_D, VIA_DRILL, CLR = 0.6, 0.3, 0.3


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def add_stitching(board, pitch=3.0, rmax=None, locked=False):
    rmax = rmax or GEOM['clamp'] - 1.0
    gnd = board.FindNet('GND')
    obst = []   # (kind, data)
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            obst.append(('c', pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), pcbnew.ToMM(t.GetWidth()) / 2))
        else:
            a, b = t.GetStart(), t.GetEnd()
            obst.append(('s', pcbnew.ToMM(a.x), pcbnew.ToMM(a.y), pcbnew.ToMM(b.x), pcbnew.ToMM(b.y), pcbnew.ToMM(t.GetWidth()) / 2))
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            obst.append(('r', pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
        # keep vias out from under component bodies on the inside face
        if fp.IsFlipped():
            c = fp.GetCourtyard(pcbnew.B_CrtYd)
            if c.OutlineCount() and 'Speaker' not in str(fp.GetFPID().GetLibItemName()):
                bb = c.BBox()
                obst.append(('r', pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
    n = 0
    R = VIA_D / 2 + CLR
    area = edges.usable(board, VIA_D / 2 + 0.35)
    steps = int(rmax / pitch) + 1
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            x, y = i * pitch + (pitch / 2 if j % 2 else 0), j * pitch * 0.866
            if math.hypot(x, y) > rmax:
                continue
            px, py = CX + x, CY - y
            if not area.contains(Point(px, py)):
                continue
            ok = True
            for o in obst:
                if o[0] == 'c':
                    d = math.hypot(px - o[1], py - o[2]) - o[3]
                elif o[0] == 's':
                    d = seg_dist(px, py, o[1], o[2], o[3], o[4]) - o[5]
                else:
                    dx = max(o[1] - px, 0, px - o[3]); dy = max(o[2] - py, 0, py - o[4])
                    d = math.hypot(dx, dy)
                if d < R:
                    ok = False
                    break
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(P(x, y)); v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetDrill(pcbnew.FromMM(VIA_DRILL)); v.SetNet(gnd)
                v.SetLocked(locked)
                board.Add(v); n += 1
                obst.append(('c', px, py, VIA_D / 2))
    return n
