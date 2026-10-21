"""Joins GND pour groups that zone_stitch could not reach with a via: for each
isolated group, finds the shortest straight GND track on either face from one
of its fragments to the main ground fragment that clears every other net."""
import pcbnew
from shapely.geometry import Point
from shapely.ops import nearest_points, unary_union
import zone_stitch as zs
from shapely.geometry import Point as _P
import fix_islands
from fix_islands import capsules, line_clear

W, CLR = 0.3, 0.22


def bridge(b):
    gnd = b.FindNet('GND'); g = gnd.GetNetCode()
    added = 0
    for _ in range(4):
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        F, B = zs.fragments(b, pcbnew.F_Cu), zs.fragments(b, pcbnew.B_Cu)
        groups = zs.components(F, B, zs.connectors(b))
        frag = lambda s, i: (F if s == 'F' else B)[i]
        groups.sort(key=lambda gr: -sum(frag(s, i).area for s, i in gr))
        if len(groups) < 2:
            break
        main = groups[0]
        progress = 0
        for gr in groups[1:]:
            best = None
            for s, i in gr:
                layer = pcbnew.F_Cu if s == 'F' else pcbnew.B_Cu
                mains = unary_union([frag(t, j) for t, j in main if t == s])
                if mains.is_empty:
                    continue
                obs = capsules(b, layer, g)
                src = frag(s, i).buffer(-W)
                if src.is_empty:
                    continue
                # candidate start points along the fragment, nearest main point for each
                parts = list(src.geoms) if hasattr(src, 'geoms') else [src]
                pts = [q.exterior.interpolate(k / 40, normalized=True) for q in parts for k in range(40)] + [src.representative_point()]
                for p in pts:
                    q = nearest_points(p, mains.buffer(-W))[1]
                    d = p.distance(q)
                    if best is not None and d >= best[0]:
                        continue
                    if line_clear(p.x, p.y, q.x, q.y, obs, W / 2 + CLR):
                        best = (d, layer, p, q)
            if best is None:
                # fall back: give each GND pad in the group its own via to the other face
                rep = ''
                for fp in b.GetFootprints():
                    for pad in fp.Pads():
                        if pad.GetNetCode() != g:
                            continue
                        q = pad.GetPosition(); pt = _P(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
                        if any(frag(s, i).distance(pt) < 0.1 for s, i in gr):
                            rep += f'Pad {pad.GetNumber()} [GND] of {fp.GetReference()} on\n'
                n = fix_islands.fix(b, rep) if rep else 0
                if not n and rep:
                    # last resort: maze-route each stranded pad to the main pour
                    import re as _re, route_one
                    mF = unary_union([frag(t, j) for t, j in main if t == 'F']).buffer(-0.35)
                    mB = unary_union([frag(t, j) for t, j in main if t == 'B']).buffer(-0.35)
                    for num, ref in _re.findall(r'Pad (\S+) \[GND\] of (\S+) on', rep):
                        n += route_one.route_net(b, ref, num, ref, num, margin=6.0, goal_area={0: mF, 1: mB}) > 0
                added += n; progress += n
                continue
            _, layer, p, q = best
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p.x), pcbnew.FromMM(p.y)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(q.x), pcbnew.FromMM(q.y)))
            t.SetLayer(layer); t.SetWidth(pcbnew.FromMM(W)); t.SetNet(gnd); b.Add(t)
            added += 1; progress += 1
        if not progress:
            break
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return added


if __name__ == '__main__':
    import os, route
    b = pcbnew.LoadBoard(route.BOARD)
    print('GND bridges:', bridge(b))
    pcbnew.SaveBoard(route.BOARD, b)
    rpt = os.path.join(route.WORK, 'drc.rpt')
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print(route.summary(rpt))
