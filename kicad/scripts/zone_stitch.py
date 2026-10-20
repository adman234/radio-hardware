"""Joins GND pour fragments: every filled fragment on either face that is
not connected to the main ground gets a via placed inside it, at a spot where
the other face's main ground fragment is also present."""
import math
import pcbnew
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

mm = pcbnew.ToMM
VIA, DRILL = 0.6, 0.3


def fragments(b, layer):
    out = []
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != 'GND' or not z.IsOnLayer(layer):
            continue
        ps = z.GetFilledPolysList(layer)
        for i in range(ps.OutlineCount()):
            def ring(ch):
                return [(mm(ch.CPoint(k).x), mm(ch.CPoint(k).y)) for k in range(ch.PointCount())]
            outer = ring(ps.Outline(i))
            holes = [ring(ps.Hole(i, h)) for h in range(ps.HoleCount(i))]
            poly = Polygon(outer, holes).buffer(0)
            if not poly.is_empty:
                out.append(poly)
    return out


def connectors(b):
    """points (x, y) where F and B GND copper is joined: GND vias and GND THT pads"""
    pts = []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND':
            p = t.GetPosition(); pts.append((mm(p.x), mm(p.y)))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == 'GND' and pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                p = pad.GetPosition(); pts.append((mm(p.x), mm(p.y)))
    return pts


def components(F, B, pts):
    nodes = [('F', i) for i in range(len(F))] + [('B', i) for i in range(len(B))]
    parent = {n: n for n in nodes}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]; n = parent[n]
        return n
    for x, y in pts:
        p = Point(x, y)
        fi = [i for i, f in enumerate(F) if f.distance(p) < 0.05]
        bi = [i for i, f in enumerate(B) if f.distance(p) < 0.05]
        for i in fi:
            for j in bi:
                parent[find(('F', i))] = find(('B', j))
    groups = {}
    for n in nodes:
        groups.setdefault(find(n), []).append(n)
    return list(groups.values())


def stitch(b):
    added = 0
    for _ in range(6):
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        F, B = fragments(b, pcbnew.F_Cu), fragments(b, pcbnew.B_Cu)
        groups = components(F, B, connectors(b))
        area = lambda g: sum((F if s == 'F' else B)[i].area for s, i in g)
        groups.sort(key=area, reverse=True)
        main = groups[0]
        mainF = unary_union([F[i] for s, i in main if s == 'F'] or [Polygon()])
        mainB = unary_union([B[i] for s, i in main if s == 'B'] or [Polygon()])
        progress = 0
        for gi, g in enumerate(groups[1:], 1):
            # prefer joining the main ground; otherwise any other group (merges later)
            others = [main] + [h for h in groups if h is not g and h is not main]
            spot = None
            for h in others:
                oF = unary_union([F[i] for s, i in h if s == 'F'] or [Polygon()])
                oB = unary_union([B[i] for s, i in h if s == 'B'] or [Polygon()])
                for s, i in g:
                    frag = (F if s == 'F' else B)[i]
                    other = oB if s == 'F' else oF
                    sp = frag.buffer(-(VIA / 2 + 0.05)).intersection(other.buffer(-(VIA / 2 + 0.05)))
                    if not sp.is_empty:
                        spot = sp
                        break
                if spot is not None:
                    break
            if spot is None:
                continue
            if True:
                p = spot.representative_point()
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(p.x), pcbnew.FromMM(p.y)))
                v.SetWidth(pcbnew.FromMM(VIA)); v.SetDrill(pcbnew.FromMM(DRILL)); v.SetNet(b.FindNet('GND'))
                b.Add(v); added += 1; progress += 1
        if not progress:
            break
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return added


def bridge(b, W=0.3, CLR=0.22, G=0.1):
    """Fallback: join each leftover fragment to the main ground with a short
    track on its own face (grid Dijkstra around other-net copper)."""
    import heapq
    import fix_islands as fi
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    F, B = fragments(b, pcbnew.F_Cu), fragments(b, pcbnew.B_Cu)
    groups = components(F, B, connectors(b))
    area = lambda g: sum((F if s == 'F' else B)[i].area for s, i in g)
    groups.sort(key=area, reverse=True)
    main = groups[0]
    gnd = b.FindNet('GND'); added = 0
    for g in groups[1:]:
        for s, i in g:
            layer = pcbnew.F_Cu if s == 'F' else pcbnew.B_Cu
            frag = (F if s == 'F' else B)[i]
            target = unary_union([(F if t == 'F' else B)[j] for t, j in main if t == s])
            obs = fi.capsules(b, layer, gnd.GetNetCode())
            x0, y0, x1, y1 = frag.bounds
            X0, Y0, X1, Y1 = x0 - 8, y0 - 8, x1 + 8, y1 + 8
            nx, ny = int((X1 - X0) / G) + 1, int((Y1 - Y0) / G) + 1
            rad = W / 2 + CLR

            def free(i_, j_):
                x, y = X0 + i_ * G, Y0 + j_ * G
                return all(fi.dseg(x, y, o) >= rad for o in obs if abs(o[0] - x) < 4 or abs(o[2] - x) < 4)
            src = [(i_, j_) for i_ in range(nx) for j_ in range(ny)
                   if frag.contains(Point(X0 + i_ * G, Y0 + j_ * G))][::3]
            tg = target.buffer(-0.15)
            dist, prev, pq = {}, {}, []
            for c in src:
                dist[c] = 0; heapq.heappush(pq, (0, c))
            found = None
            seen = 0
            while pq and seen < 60000:
                d, c = heapq.heappop(pq); seen += 1
                if d > dist.get(c, 1e9):
                    continue
                if tg.contains(Point(X0 + c[0] * G, Y0 + c[1] * G)):
                    found = c; break
                for di, dj, w in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.41), (1, -1, 1.41), (-1, 1, 1.41), (-1, -1, 1.41)):
                    n = (c[0] + di, c[1] + dj)
                    if 0 <= n[0] < nx and 0 <= n[1] < ny and d + w < dist.get(n, 1e9):
                        inside = frag.contains(Point(X0 + n[0] * G, Y0 + n[1] * G))
                        if inside or free(*n):
                            dist[n] = d + w; prev[n] = c; heapq.heappush(pq, (d + w, n))
            if not found:
                continue
            path = [found]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            pts = [path[0]]
            for k in range(1, len(path) - 1):
                if (path[k][0] - path[k - 1][0], path[k][1] - path[k - 1][1]) != (path[k + 1][0] - path[k][0], path[k + 1][1] - path[k][1]):
                    pts.append(path[k])
            pts.append(path[-1])
            V = lambda c: pcbnew.VECTOR2I(pcbnew.FromMM(X0 + c[0] * G), pcbnew.FromMM(Y0 + c[1] * G))
            for a, c in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(b); t.SetStart(V(a)); t.SetEnd(V(c)); t.SetLayer(layer)
                t.SetWidth(pcbnew.FromMM(W)); t.SetNet(gnd); b.Add(t)
            added += 1
            break
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return added
