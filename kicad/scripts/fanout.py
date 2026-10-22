"""Pre-route GND fan-out: every SMD GND pad gets a short locked stub and a via
to the inside-face pour before Freerouting runs, so no ground pin can end up
walled in by signal tracks (Freerouting leaves GND pins to the pours)."""
import math
import pcbnew
from shapely.geometry import Point, LineString
import edges

mm = pcbnew.ToMM
W, CLR, VIA, DRILL = 0.3, 0.22, 0.6, 0.3


def _rect_dist(x, y, bb):
    dx = max(bb[0] - x, 0, x - bb[2]); dy = max(bb[1] - y, 0, y - bb[3])
    return math.hypot(dx, dy)


def fanout(b):
    gnd = b.FindNet('GND'); g = gnd.GetNetCode()
    others = []      # (bbox) of every non-GND pad, both faces
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() != g or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                bb = p.GetBoundingBox()
                others.append((mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())))
    vias = [(mm(t.GetPosition().x), mm(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    added = 0
    area = edges.usable(b, VIA / 2 + 0.35)
    tarea = edges.usable(b, W / 2 + 0.25)
    for fp in b.GetFootprints():
        fc = fp.GetPosition()
        for p in fp.Pads():
            if p.GetNetCode() != g or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            c = p.GetPosition(); cx, cy = mm(c.x), mm(c.y)
            bb = p.GetBoundingBox(); hw, hh = (mm(bb.GetWidth()) / 2, mm(bb.GetHeight()) / 2)
            # try outward first (away from the footprint centre), then the other directions
            ox, oy = cx - mm(fc.x), cy - mm(fc.y)
            base = math.atan2(oy, ox) if (ox or oy) else 0.0
            done = False
            for d in (0.9, 1.1, 1.3, 1.6, 2.0, 2.5):
                for k in range(0, 360, 15):
                    a = base + math.radians(k if k <= 180 else k - 360)
                    reach = d + min(abs(hw / math.cos(a)) if math.cos(a) else 1e9, abs(hh / math.sin(a)) if math.sin(a) else 1e9)
                    x, y = cx + reach * math.cos(a), cy + reach * math.sin(a)
                    if not area.contains(Point(x, y)) or not tarea.contains(LineString([(cx, cy), (x, y)])):
                        continue
                    if any(_rect_dist(x, y, o) < VIA / 2 + CLR for o in others):
                        continue
                    if any(math.hypot(x - vx, y - vy) < VIA + CLR for vx, vy in vias):
                        continue
                    # the stub must clear other-net pads too
                    n = 12
                    if any(_rect_dist(cx + (x - cx) * i / n, cy + (y - cy) * i / n, o) < W / 2 + CLR
                           for i in range(n + 1) for o in others):
                        continue
                    t = pcbnew.PCB_TRACK(b); t.SetStart(c); t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                    t.SetLayer(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
                    t.SetWidth(pcbnew.FromMM(W)); t.SetNet(gnd); t.SetLocked(True); b.Add(t)
                    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                    v.SetWidth(pcbnew.FromMM(VIA)); v.SetDrill(pcbnew.FromMM(DRILL)); v.SetNet(gnd); v.SetLocked(True); b.Add(v)
                    vias.append((x, y)); others.append((x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2))
                    added += 1; done = True
                    break
                if done:
                    break
    return added
