"""Routes one leftover two-pad connection with a small grid A* maze router
(F.Cu/B.Cu, vias allowed), clear of every other net. Used for the odd net
Freerouting leaves unrouted.

    python3 route_one.py REF PAD REF PAD
"""
import heapq, math, sys
import pcbnew
from fix_islands import dseg

W, CLR, VIA, DRILL, STEP = 0.25, 0.22, 0.6, 0.3, 0.1
mm = pcbnew.ToMM


def obstacles(b, layer, skip_net):
    """('c', capsule) for tracks/vias, ('r', x0, y0, x1, y1) for pads (true corners)."""
    out = []
    for t in b.GetTracks():
        if t.GetNetCode() == skip_net:
            continue
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition(); out.append(('c', (mm(p.x), mm(p.y), mm(p.x), mm(p.y), mm(t.GetWidth()) / 2)))
        elif t.GetLayer() == layer:
            a, e = t.GetStart(), t.GetEnd(); out.append(('c', (mm(a.x), mm(a.y), mm(e.x), mm(e.y), mm(t.GetWidth()) / 2)))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == skip_net and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue
            if not pad.IsOnLayer(layer) and pad.GetDrillSize().x == 0:
                continue
            bb = pad.GetBoundingBox()
            out.append(('r', mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())))
    return out


def dobs(x, y, o):
    if o[0] == 'c':
        return dseg(x, y, o[1])
    _, x0, y0, x1, y1 = o
    dx = max(x0 - x, 0, x - x1); dy = max(y0 - y, 0, y - y1)
    return math.hypot(dx, dy)


def route_net(b, a_ref, a_pad, b_ref, b_pad, margin=8.0):
    pa = [p for p in b.FindFootprintByReference(a_ref).Pads() if p.GetNumber() == a_pad][0]
    pb = [p for p in b.FindFootprintByReference(b_ref).Pads() if p.GetNumber() == b_pad][0]
    net = pa.GetNetCode()
    obs = {pcbnew.F_Cu: obstacles(b, pcbnew.F_Cu, net), pcbnew.B_Cu: obstacles(b, pcbnew.B_Cu, net)}
    # the target pads' own copper must not block the path
    A, Bp = pa.GetPosition(), pb.GetPosition()
    ax, ay, bx, by = mm(A.x), mm(A.y), mm(Bp.x), mm(Bp.y)
    x0, y0 = min(ax, bx) - margin, min(ay, by) - margin
    nx, ny = int((abs(ax - bx) + 2 * margin) / STEP) + 1, int((abs(ay - by) + 2 * margin) / STEP) + 1
    layers = [pcbnew.F_Cu, pcbnew.B_Cu]
    free = {}

    def ok(i, j, L):
        k = (i, j, L)
        if k not in free:
            x, y = x0 + i * STEP, y0 + j * STEP
            free[k] = all(dobs(x, y, s) >= W / 2 + CLR + 0.02 for s in obs[layers[L]])
        return free[k]

    def via_ok(i, j):
        x, y = x0 + i * STEP, y0 + j * STEP
        return all(dobs(x, y, s) >= VIA / 2 + CLR + 0.02 for L in layers for s in obs[L])
    ga = (round((ax - x0) / STEP), round((ay - y0) / STEP))
    gb = (round((bx - x0) / STEP), round((by - y0) / STEP))
    la = 0 if pa.IsOnLayer(pcbnew.F_Cu) else 1
    goals = {(gb[0], gb[1], L) for L in (0, 1) if pb.IsOnLayer(layers[L])}
    start = (ga[0], ga[1], la)
    h = lambda n: math.hypot(n[0] - gb[0], n[1] - gb[1])
    dist, prev, pq = {start: 0}, {}, [(h(start), start)]
    near = lambda n, g: math.hypot(n[0] - g[0], n[1] - g[1]) * STEP < 0.3   # inside the pads
    while pq:
        _, n = heapq.heappop(pq)
        if n in goals:
            break
        i, j, L = n
        steps = [(di, dj, L, math.hypot(di, dj)) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]
        steps.append((0, 0, 1 - L, 30))
        for di, dj, L2, c in steps:
            m = (i + di, j + dj, L2)
            if not (0 <= m[0] < nx and 0 <= m[1] < ny):
                continue
            if L2 != L:
                if not via_ok(i, j):
                    continue
            elif not (ok(m[0], m[1], L2) or near(m, ga) or near(m, gb)):
                continue
            d = dist[n] + c
            if d < dist.get(m, 1e18):
                dist[m] = d; prev[m] = n
                heapq.heappush(pq, (d + h(m), m))
    end = next((g for g in goals if g in prev), None)
    if end is None:
        return 0
    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    # merge collinear steps into tracks, add vias at layer changes
    pt = lambda n: pcbnew.VECTOR2I(pcbnew.FromMM(x0 + n[0] * STEP), pcbnew.FromMM(y0 + n[1] * STEP))
    added, seg0 = 0, path[0]
    for k in range(1, len(path)):
        a, c = path[k - 1], path[k]
        if c[2] != a[2]:
            v = pcbnew.PCB_VIA(b); v.SetPosition(pt(a)); v.SetWidth(pcbnew.FromMM(VIA)); v.SetDrill(pcbnew.FromMM(DRILL))
            v.SetNet(pa.GetNet()); b.Add(v); seg0 = c; continue
        nxt = path[k + 1] if k + 1 < len(path) else None
        if nxt is None or nxt[2] != c[2] or (nxt[0] - c[0], nxt[1] - c[1]) != (c[0] - a[0], c[1] - a[1]):
            if seg0[:2] != c[:2]:
                t = pcbnew.PCB_TRACK(b); t.SetStart(pt(seg0)); t.SetEnd(pt(c)); t.SetLayer(layers[c[2]])
                t.SetWidth(pcbnew.FromMM(W)); t.SetNet(pa.GetNet()); b.Add(t); added += 1
            seg0 = c
    # snap both ends exactly onto the pad centres
    for pad, n in ((pa, path[0]), (pb, path[-1])):
        if pt(n) != pad.GetPosition():
            t = pcbnew.PCB_TRACK(b); t.SetStart(pad.GetPosition()); t.SetEnd(pt(n)); t.SetLayer(layers[n[2]])
            t.SetWidth(pcbnew.FromMM(W)); t.SetNet(pa.GetNet()); b.Add(t); added += 1
    return added


if __name__ == '__main__':
    import os, route
    b = pcbnew.LoadBoard(route.BOARD)
    n = route_net(b, *sys.argv[1:5])
    print('tracks added:', n)
    import island_bridge
    print('GND bridges:', island_bridge.bridge(b))
    pcbnew.SaveBoard(route.BOARD, b)
    rpt = os.path.join(route.WORK, 'drc.rpt')
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print(route.summary(rpt))
