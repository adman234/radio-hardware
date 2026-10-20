"""After routing with GND as copper pours, some GND pads end up in pour
islands. For each one, drop a via next to the pad (short track on the pad's
layer) so it reaches the solid pour on the other side."""
import math, re
import pcbnew

mm = pcbnew.ToMM
W, CLR, VIA, DRILL = 0.3, 0.22, 0.6, 0.3


def capsules(b, layer, skip_net=None):
    obs = []
    for t in b.GetTracks():
        if skip_net is not None and t.GetNetCode() == skip_net:
            continue
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition(); obs.append((mm(p.x), mm(p.y), mm(p.x), mm(p.y), mm(t.GetWidth()) / 2))
        elif t.GetLayer() == layer:
            a, e = t.GetStart(), t.GetEnd(); obs.append((mm(a.x), mm(a.y), mm(e.x), mm(e.y), mm(t.GetWidth()) / 2))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if skip_net is not None and pad.GetNetCode() == skip_net and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue
            if not pad.IsOnLayer(layer) and pad.GetDrillSize().x == 0:
                continue
            bb = pad.GetBoundingBox(); x0, y0, x1, y1 = mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())
            r = min(x1 - x0, y1 - y0) / 2
            if x1 - x0 > y1 - y0:
                obs.append((x0 + r, (y0 + y1) / 2, x1 - r, (y0 + y1) / 2, r))
            else:
                obs.append(((x0 + x1) / 2, y0 + r, (x0 + x1) / 2, y1 - r, r))
    return obs


def dseg(px, py, s):
    ax, ay, bx, by, r = s
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy) - r


def line_clear(ax, ay, bx, by, obs, rad):
    n = max(2, int(math.hypot(bx - ax, by - ay) / 0.05))
    for k in range(n + 1):
        x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
        if any(dseg(x, y, s) < rad for s in obs):
            return False
    return True


def fix(b, report_text):
    gnd = b.FindNet('GND'); g = gnd.GetNetCode()
    pads = set(re.findall(r'Pad (\S+) \[GND\] of (\S+) on', report_text))
    fixed = 0
    oF, oB = capsules(b, pcbnew.F_Cu, g), capsules(b, pcbnew.B_Cu, g)
    for num, ref in sorted(pads):
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            continue
        pad = [p for p in fp.Pads() if p.GetNumber() == num]
        if not pad:
            continue
        pad = pad[0]
        layer = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
        own = oB if layer == pcbnew.B_Cu else oF
        c = pad.GetPosition(); cx, cy = mm(c.x), mm(c.y)
        done = False
        for r in [0.9 + 0.1 * k for k in range(20)]:
            for a in range(0, 360, 15):
                x, y = cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))
                if any(dseg(x, y, s) < VIA / 2 + CLR for s in oF + oB):
                    continue
                if not line_clear(cx, cy, x, y, own, W / 2 + CLR):
                    continue
                t = pcbnew.PCB_TRACK(b); t.SetStart(c); t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                t.SetLayer(layer); t.SetWidth(pcbnew.FromMM(W)); t.SetNet(gnd); b.Add(t)
                v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                v.SetWidth(pcbnew.FromMM(VIA)); v.SetDrill(pcbnew.FromMM(DRILL)); v.SetNet(gnd); b.Add(v)
                oF.append((x, y, x, y, VIA / 2)); oB.append((x, y, x, y, VIA / 2))
                own.append((cx, cy, x, y, W / 2))
                fixed += 1; done = True
                break
            if done:
                break
    return fixed
