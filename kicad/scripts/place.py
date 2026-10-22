"""Small legalizer: moves non-fixed parts to the nearest clear spot.

A spot is clear when the part's courtyard (plus a margin) stays inside the
usable circle for its face, stays out of the speaker footprint on the inside
face, and overlaps no courtyard already placed on that face. Through-hole
parts and holes block both faces.
"""
import math
import pcbnew
from gen_pcb import CX, CY, SPK, GEOM, P, GRILLE_R, SPK_R, BATT, BATT_SIZE

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


def _circle_hits(bb, cx_mm, cy_mm, r_mm):
    sx, sy = pcbnew.FromMM(CX + cx_mm), pcbnew.FromMM(CY - cy_mm)
    nx = min(max(sx, bb[0]), bb[2]); ny = min(max(sy, bb[1]), bb[3])
    return math.hypot(nx - sx, ny - sy) < pcbnew.FromMM(r_mm)


def _battery():
    from shapely.geometry import box
    from shapely import affinity
    w, h = BATT_SIZE
    return affinity.rotate(box(BATT[0] - w / 2, BATT[1] - h / 2, BATT[0] + w / 2, BATT[1] + h / 2), BATT[2], origin=BATT[:2])


def _mm_box(bb):
    """Courtyard bbox (KiCad units, y down) as a shapely box in mm, y up."""
    from shapely.geometry import box
    return box(pcbnew.ToMM(bb[0]) - CX, CY - pcbnew.ToMM(bb[3]), pcbnew.ToMM(bb[2]) - CX, CY - pcbnew.ToMM(bb[1]))


def inside(bb, face, tht=False):
    """Courtyard inside the usable circle and clear of the grille (top face);
    through-hole parts must also clear the speaker and the battery that
    sit against the inside face."""
    cx, cy = pcbnew.FromMM(CX), pcbnew.FromMM(CY)
    rmax = pcbnew.FromMM((GEOM['bot_keep'] if face == 'B' else GEOM['top_keep']) - 0.2)
    for x, y in ((bb[0], bb[1]), (bb[2], bb[1]), (bb[0], bb[3]), (bb[2], bb[3])):
        if math.hypot(x - cx, y - cy) > rmax:
            return False
    if face == 'F' and _circle_hits(bb, SPK[0], SPK[1], GRILLE_R):
        return False
    if tht or face == 'B':
        if _circle_hits(bb, SPK[0], SPK[1], SPK_R):
            return False
        if _battery().intersects(_mm_box(bb)):
            return False
    return True


def legalize(board, placed, mech, PLACE):
    blocked = {'F': [], 'B': []}

    def block(fp, faces):
        bb = bbox(fp)
        for f in faces:
            blocked[f].append(bb)

    for fp in mech:
        name = str(fp.GetFPID().GetLibItemName())
        if name.startswith('Logo') and not fp.IsFlipped():
            block(fp, 'F')          # top logo: keep parts off it
        elif not any(k in name for k in ('Speaker', 'Grille', 'Holder', 'Battery', 'Logo')):
            block(fp, 'FB')         # holes
    auto = []
    for ref, fp in placed.items():
        spec = PLACE[ref]
        if len(spec) > 4 and spec[4] == 'fix':
            if 'Speaker' in str(fp.GetFPID().GetLibItemName()):
                continue            # round keep-out (GRILLE_R) covers it, not its square bbox
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
                    if not inside(bb, face, is_tht(fp)):
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
