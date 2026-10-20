"""Small legalizer: moves non-fixed parts to the nearest clear spot.

A spot is clear when the part's courtyard (plus a margin) stays inside the
usable circle for its face, stays out of the speaker footprint on the inside
face, and overlaps no courtyard already placed on that face. Through-hole
parts and holes block both faces.
"""
import math
import pcbnew
from gen_pcb import CX, CY, SPK, GEOM, P

MARGIN = pcbnew.FromMM(0.1)


def bbox(fp):
    fp.BuildCourtyardCaches()
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    c = fp.GetCourtyard(layer)
    if c.OutlineCount() == 0:
        c = fp.GetCourtyard(pcbnew.F_CrtYd if fp.IsFlipped() else pcbnew.B_CrtYd)
    bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False, False)
    return (bb.GetLeft() - MARGIN, bb.GetTop() - MARGIN, bb.GetRight() + MARGIN, bb.GetBottom() + MARGIN)


def is_tht(fp):
    return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())


def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def inside(bb, face):
    cx, cy = pcbnew.FromMM(CX), pcbnew.FromMM(CY)
    rmax = pcbnew.FromMM((GEOM['bot_keep'] if face == 'B' else GEOM['top_keep']) - 0.2)
    for x, y in ((bb[0], bb[1]), (bb[2], bb[1]), (bb[0], bb[3]), (bb[2], bb[3])):
        if math.hypot(x - cx, y - cy) > rmax:
            return False
    if face == 'B':
        sx, sy = pcbnew.FromMM(CX + SPK[0]), pcbnew.FromMM(CY - SPK[1])
        nx = min(max(sx, bb[0]), bb[2]); ny = min(max(sy, bb[1]), bb[3])
        if math.hypot(nx - sx, ny - sy) < pcbnew.FromMM(25.4):
            return False
    return True


def legalize(board, placed, mech, PLACE):
    blocked = {'F': [], 'B': []}

    def block(fp, faces):
        bb = bbox(fp)
        for f in faces:
            blocked[f].append(bb)

    for fp in mech:
        if fp.GetFPID().GetLibItemName() in ('Speaker_D49_Keepout',) or 'Logo' in str(fp.GetFPID().GetLibItemName()) \
                or 'Grille' in str(fp.GetFPID().GetLibItemName()):
            continue
        block(fp, 'FB')
    auto = []
    for ref, fp in placed.items():
        spec = PLACE[ref]
        if len(spec) > 4 and spec[4] == 'fix':
            face = 'B' if fp.IsFlipped() else 'F'
            block(fp, 'FB' if is_tht(fp) else face)
        else:
            auto.append((ref, fp))
    # biggest parts first
    auto.sort(key=lambda rf: -((lambda b: (b[2] - b[0]) * (b[3] - b[1]))(bbox(rf[1]))))
    failed = []
    for ref, fp in auto:
        x0, y0, rot, side = PLACE[ref][:4]
        face = side
        ok = False
        d = 0.0
        while d <= 45 and not ok:
            n = 1 if d == 0 else max(8, int(2 * math.pi * d / 0.5))
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = x0 + d * math.cos(a), y0 + d * math.sin(a)
                for r in (rot, rot + 90, rot + 180, rot + 270):
                    fp.SetPosition(P(x, y))
                    fp.SetOrientationDegrees(r)
                    bb = bbox(fp)
                    if not inside(bb, face):
                        continue
                    faces = 'FB' if is_tht(fp) else face
                    if any(overlap(bb, o) for f in faces for o in blocked[f]):
                        continue
                    for f in faces:
                        blocked[f].append(bb)
                    ok = True
                    break
                if ok:
                    break
            d += 0.5
        if not ok:
            failed.append(ref)
            fp.SetPosition(P(x0, y0)); fp.SetOrientationDegrees(rot)
        elif d > 0.6:
            print(f'  {ref}: moved {d - 0.5:.1f} mm')
    if failed:
        print('COULD NOT PLACE:', failed)
    return failed
