"""Builds jar-radio.kicad_pcb from circuit.py: outline, placement, nets,
zones, clamp-ring keepout, holes and artwork. Routing is done afterwards by
route.py (Freerouting).

Coordinates in PLACE are millimetres from the board centre, X right and
Y UP as seen from the top (outside) face. All parts sit on the top face; the
inside face carries only the battery outline.
Board geometry is from the measured wide-mouth jar (see GEOM).
"""
import math, os
import pcbnew
import circuit

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
STD = '/usr/share/kicad/footprints'
OWN = os.path.join(PROJ, 'lib', 'jar-radio.pretty')

GEOM = dict(
    od=84.0,          # wide-mouth lid measured 84.3 mm
    top_keep=36.0,    # band window measured 74.0 mm
    bot_keep=36.0,    # jar ID measured 74.3 mm
    clamp=37.2,       # outside this radius: solid GND both sides, no tracks
)
CX, CY = 150.0, 100.0     # board centre in KiCad page coordinates
SPK = (0.0, -14.0)        # speaker centre: Ø40 HDK-4008BB-2 on the top face, back down over a cutout
GRILLE_R = 20.8           # top-face keep-out: the speaker itself
SPK_R = 20.8              # through-hole parts can't sit under the speaker either
BATT = (-9.25, 7.75, 52.0)   # 102050 LiPo on the inside face: centre x, y and long-axis angle.
                              # Diagonal is the only way a 50 mm cell clears the speaker cup, pot,
                              # USB-C legs and whip nut; this pose has the most clearance (~1.5 mm)
BATT_SIZE = (51.0, 21.0)      # 50 x 20 cell + 0.5 mm all round
SOCK = (-13.5, 20.5)          # PH2.0 socket on the top face, mouth facing -x at the plug cutout

# ref: (x, y_up, rotation_deg_seen_from_top, side[, 'fix'])
# Everything sits on the top face. Parts without 'fix' are a starting point:
# place.py moves them to the nearest spot where their courtyard is clear.
PLACE = {
    # --- fixed: controls, connectors, hand-wired pads
    'RV1': (25.0, 5.0, 0, 'F', 'fix'), 'J1': (-27.0, 10.0, 90, 'F', 'fix'), 'ANT1': (22.5, 24.0, 0, 'F', 'fix'),
    'J2': (SOCK[0], SOCK[1], 270, 'F', 'fix'), 'J3': (7.0, 31.0, 0, 'F', 'fix'), 'J4': (SPK[0], SPK[1], 90, 'F', 'fix'),
    # --- battery protection, between the socket and the whip mount
    'U6': (-1.0, 27.5, 0, 'F'), 'R18': (3.0, 24.5, 90, 'F'), 'C22': (3.0, 28.5, 90, 'F'), 'F1': (-5.5, 24.0, 90, 'F'),
    # --- tuner, upper right between the logo and the knob
    'U1': (15.5, 15.5, 90, 'F'), 'Y1': (11.0, 9.5, 0, 'F'), 'C1': (9.5, 12.0, 90, 'F'), 'C2': (13.0, 12.0, 90, 'F'),
    'C3': (16.0, 20.5, 0, 'F'), 'C4': (18.5, 20.5, 0, 'F'), 'R1': (21.0, 20.0, 90, 'F'), 'C5': (22.5, 20.0, 90, 'F'),
    'U5': (24.0, 17.0, 90, 'F'),
    'R2': (22.0, 13.5, 90, 'F'), 'R3': (23.5, 13.5, 90, 'F'), 'R4': (25.0, 13.5, 90, 'F'),
    'C6': (26.5, 13.5, 90, 'F'), 'C7': (28.0, 13.5, 90, 'F'), 'C21': (29.5, 14.0, 90, 'F'),
    'R5': (11.0, 18.0, 90, 'F'), 'R17': (9.5, 18.0, 90, 'F'), 'R6': (12.5, 18.0, 90, 'F'), 'C8': (14.0, 9.5, 0, 'F'),
    'RV2': (27.0, 19.0, 90, 'F'),
    # --- antenna network next to the whip mount
    'C9': (16.0, 24.0, 0, 'F'), 'L1': (13.5, 24.0, 0, 'F'), 'D4': (18.5, 24.0, 0, 'F'),
    # --- audio, right side between the knob and the speaker pads
    'C10': (18.0, 4.0, 90, 'F'), 'R22': (19.5, 1.0, 90, 'F'), 'C11': (21.0, -6.5, 0, 'F'), 'R7': (21.0, -8.5, 0, 'F'),
    'R8': (28.0, -9.0, 90, 'F'), 'U2': (24.0, -13.5, 90, 'F'), 'C12': (19.5, -11.0, 90, 'F'), 'C13': (29.0, -14.0, 90, 'F'),
    'C14': (29.0, -17.5, 90, 'F'), 'R9': (20.0, -15.0, 90, 'F'), 'R10': (20.0, -18.0, 90, 'F'),
    # --- LDO between the knob switch and the tuner
    'U4': (16.0, -1.0, 0, 'F'), 'C18': (13.0, 0.5, 90, 'F'), 'C19': (19.0, -2.5, 0, 'F'), 'C20': (12.5, -2.5, 0, 'F'),
    # --- USB-C input, charger, load sharing: upper left
    'R11': (-23.0, 6.5, 90, 'F'), 'R12': (-23.0, 13.5, 90, 'F'), 'C15': (-22.5, 10.0, 90, 'F'),
    'U3': (-15.5, 14.0, 0, 'F'), 'R13': (-12.0, 18.5, 90, 'F'), 'R21': (-19.0, 18.5, 90, 'F'), 'R20': (-17.0, 18.5, 90, 'F'),
    'RT1': (-15.0, 18.5, 90, 'F'), 'D2': (-10.5, 20.0, 90, 'F'), 'D3': (-10.5, 23.0, 90, 'F'), 'R14': (-12.5, 21.0, 0, 'F'),
    'R15': (-12.5, 23.5, 0, 'F'), 'C16': (-17.0, 17.0, 90, 'F'),
    'Q1': (-15.0, 7.0, 0, 'F'), 'R16': (-18.5, 7.0, 90, 'F'), 'D1': (-11.0, 5.5, 0, 'F'), 'C17': (-7.0, 5.0, 90, 'F'),
}

# mechanical items: (footprint, x, y_up, rot, side)
MECH = [
    ('Battery_LiPo_102050_Outline', BATT[0], BATT[1], BATT[2], 'B'),
    ('Logo_KOPN_15mm', 0.0, 14.0, 0, 'F'),
    ('Logo_CGW_11mm', -26.5, -1.4, 0, 'F'),
]

POWER_NETS = {'GND', 'VBUS', 'VBAT', 'VSYS', 'VSW', 'SPK+', 'SPK-', 'BAT_P', 'BAT_N'}


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(CX + x), pcbnew.FromMM(CY - y))


def load(fpid):
    lib, name = fpid.split(':')
    path = OWN if lib == 'jar-radio' else os.path.join(STD, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit('missing footprint ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def put(board, fp, x, y, rot, side):
    board.Add(fp)
    fp.SetPosition(P(x, y))
    if side == 'B':
        fp.Flip(fp.GetPosition(), False)
    fp.SetOrientationDegrees(rot)


def circle_poly(r, n=96):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def add_zone(board, net, layer, outer, hole=None, rule=False, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in outer:
        ol.Append(P(x, y))
    if hole:
        ol.NewHole()
        for x, y in hole:
            ol.Append(P(x, y))
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowFootprints(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowCopperPour(False)
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
    else:
        z.SetNet(net)
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.4))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
        z.SetAssignedPriority(prio)
    board.Add(z)
    return z


def text(board, s, x, y, size, layer, rot=0, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * (0.2 if bold else 0.15)))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def build(sch_parts, out_path):
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.2)
    ds.m_ViasMinSize = pcbnew.FromMM(0.6)
    ds.m_MinThroughDrill = pcbnew.FromMM(0.3)
    ds.m_MinClearance = pcbnew.FromMM(0.2)
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.2)
    ds.m_HoleClearance = pcbnew.FromMM(0.2)
    ds.m_SolderMaskExpansion = pcbnew.FromMM(0.05)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetTrackWidth(pcbnew.FromMM(0.25)); nc.SetClearance(pcbnew.FromMM(0.2))
    nc.SetViaDiameter(pcbnew.FromMM(0.6)); nc.SetViaDrill(pcbnew.FromMM(0.3))
    pw = pcbnew.NETCLASS('Power')
    pw.SetTrackWidth(pcbnew.FromMM(0.5)); pw.SetClearance(pcbnew.FromMM(0.2))
    pw.SetViaDiameter(pcbnew.FromMM(0.8)); pw.SetViaDrill(pcbnew.FromMM(0.4))
    ds.m_NetSettings.m_NetClasses['Power'] = pw
    # nets
    names = sorted({n for p in circuit.P for n in p['nets'].values()})
    nets = {}
    for n in names:
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        nets[n] = ni

    # outline
    c = pcbnew.PCB_SHAPE(board)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetCenter(P(0, 0)); c.SetEnd(P(GEOM['od'] / 2, 0))
    c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(pcbnew.FromMM(0.1))
    board.Add(c)

    uuid = {p['ref']: p['uuid'] for p in sch_parts}
    placed = {}
    for p in circuit.P:
        ref = p['ref']
        if ref not in PLACE:
            raise SystemExit('no placement for ' + ref)
        fp = load(p['footprint'])
        fp.SetReference(ref)
        fp.SetValue(p['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + uuid[ref]))
        fp.SetProperty('LCSC', p['lcsc'])
        fp.SetProperty('MPN', p['mpn'])
        if p.get('dnp') or p.get('hand'):
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        x, y, rot, side = PLACE[ref][:4]
        put(board, fp, x, y, rot, side)
        placed[ref] = fp
        for pad in fp.Pads():
            n = p['nets'].get(pad.GetNumber())
            if n:
                pad.SetNet(nets[n])
        fp.Reference().SetVisible(True)   # top face is the product face: refs go on the fab layer, not silk
        fp.Reference().SetLayer(pcbnew.F_Fab)

    mech_fps = []
    for name, x, y, rot, side in MECH:
        fp = load('jar-radio:' + name)
        mech_fps.append(fp)
        fp.SetReference(f'MK{len(mech_fps)}')   # the Specctra export needs a reference
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
        fp.Reference().SetVisible(False)
        put(board, fp, x, y, rot, side)

    import place
    place.legalize(board, placed, mech_fps, PLACE)

    # copper: GND pour on both faces, clamp ring kept free of tracks
    R = GEOM['od'] / 2 - 0.4
    add_zone(board, nets['GND'], pcbnew.F_Cu, circle_poly(R))
    add_zone(board, nets['GND'], pcbnew.B_Cu, circle_poly(R))
    # KiCad 7 crashes on a rule area with a hole, so the ring is 12 sectors
    ro, ri = GEOM['od'] / 2 + 1, GEOM['clamp']
    for k in range(12):
        a0, a1 = 2 * math.pi * k / 12, 2 * math.pi * (k + 1) / 12
        arc = [a0 + (a1 - a0) * i / 8 for i in range(9)]
        poly = [(ro * math.cos(a), ro * math.sin(a)) for a in arc] + [(ri * math.cos(a), ri * math.sin(a)) for a in reversed(arc)]
        add_zone(board, None, pcbnew.F_Cu, poly, rule=True)
    # stitching vias around the clamp ring
    for i in range(36):
        a = 2 * math.pi * (i + 0.5) / 36
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(P(39.5 * math.cos(a), 39.5 * math.sin(a)))
        v.SetWidth(pcbnew.FromMM(0.8)); v.SetDrill(pcbnew.FromMM(0.4))
        v.SetNet(nets['GND'])
        board.Add(v)

    # guide circles on the fab layers for the keep-in radii
    for r, layer in ((GEOM['top_keep'], pcbnew.F_Fab), (GEOM['bot_keep'], pcbnew.B_Fab), (GEOM['clamp'], pcbnew.Dwgs_User)):
        g = pcbnew.PCB_SHAPE(board); g.SetShape(pcbnew.SHAPE_T_CIRCLE)
        g.SetCenter(P(0, 0)); g.SetEnd(P(r, 0)); g.SetLayer(layer); g.SetWidth(pcbnew.FromMM(0.1))
        board.Add(g)

    # silkscreen text
    text(board, 'COLUMBIA', -26.5, -8.3, 0.9, pcbnew.F_SilkS, bold=True)          # under the CGW logo
    text(board, 'GADGET WORKS', -26.5, -9.7, 0.9, pcbnew.F_SilkS, bold=True)
    # LED labels: beside wherever the legalizer put the LEDs, on the first
    # side (right, left, above, below) where they overlap no other part
    def mmbox(fp):
        bb = fp.GetBoundingBox(False, False)
        return (pcbnew.ToMM(bb.GetLeft()) - CX, CY - pcbnew.ToMM(bb.GetBottom()), pcbnew.ToMM(bb.GetRight()) - CX, CY - pcbnew.ToMM(bb.GetTop()))
    others = [mmbox(f) for f in board.GetFootprints() if not f.IsFlipped()]
    labels = []
    for ref, label in (('D2', 'CHG'), ('D3', 'FULL')):
        x0, y0, x1, y1 = mmbox(placed[ref]); cy = (y0 + y1) / 2; cx = (x0 + x1) / 2
        hw, hh = 0.36 * len(label) + 0.1, 0.5
        for tx, ty in ((x1 + 0.3 + hw, cy), (x0 - 0.3 - hw, cy), (cx, y1 + 0.3 + hh), (cx, y0 - 0.3 - hh)):
            box = (tx - hw, ty - hh, tx + hw, ty + hh)
            if not any(box[0] < o[2] and o[0] < box[2] and box[1] < o[3] and o[1] < box[3] for o in others + labels):
                break
        labels.append(box)
        text(board, label, tx, ty, 0.8, pcbnew.F_SilkS)
    # speaker placement ring: what goes there and how big the cutout is
    text(board, '40mm SPEAKER', SPK[0], SPK[1] - 15.5, 1.0, pcbnew.F_SilkS)
    text(board, 'CUTOUT \u00d816.8mm', SPK[0], SPK[1] - 10.3, 0.8, pcbnew.F_SilkS)
    # inside face, below the speaker cup (the battery covers the middle)
    text(board, 'KOPN 89.5 JAR RADIO rev B', 0.0, -25.0, 0.8, pcbnew.B_SilkS)
    text(board, 'COLUMBIA, MO', 0.0, -26.8, 0.8, pcbnew.B_SilkS)
    text(board, 'CERN-OHL-S-2.0', 0.0, -28.6, 0.8, pcbnew.B_SilkS)
    text(board, 'after The Public Radio', 0.0, -30.4, 0.8, pcbnew.B_SilkS)
    # plug cutout, seen from the inside face: the battery plug goes up through here
    text(board, 'BATT PLUG UP', SOCK[0] - 9.0, SOCK[1] + 5.0, 0.8, pcbnew.B_SilkS)
    text(board, 'red = +', SOCK[0] - 9.0, SOCK[1] - 5.0, 0.8, pcbnew.B_SilkS)

    board.SetFileName(out_path)
    pcbnew.SaveBoard(out_path, board)
    return board
