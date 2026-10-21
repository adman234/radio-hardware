"""Builds jar-radio.kicad_pcb from circuit.py: outline, placement, nets,
zones, clamp-ring keepout, holes and artwork. Routing is done afterwards by
route.py (Freerouting).

Coordinates in PLACE are millimetres from the board centre, X right and
Y UP as seen from the top (outside) face. All parts sit on the top face; the
inside face carries only the speaker and 18650 holder outlines.
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
SPK = (0.0, -14.0)        # speaker centre (inside face, under the grille)
GRILLE_R = 17.0           # top-face keep-out around the grille
SPK_R = 20.5              # inside-face keep-out: Ø40 speaker
SLOT = (0.0, 23.5)        # 18650 holder foot slot, 180 deg from the speaker
HOLDER = (-10.6, 8.0, 10.6, 23.2)   # inside-face holder end face (x0, y0, x1, y1), y up

# ref: (x, y_up, rotation_deg_seen_from_top, side[, 'fix'])
# Everything sits on the top face. Parts without 'fix' are a starting point:
# place.py moves them to the nearest spot where their courtyard is clear.
PLACE = {
    # --- fixed: controls, connectors, hand-wired pads
    'RV1': (25.0, 5.0, 0, 'F', 'fix'), 'J1': (-27.0, 10.0, 90, 'F', 'fix'), 'ANT1': (16.0, 27.5, 0, 'F', 'fix'),
    'J2': (SLOT[0], SLOT[1], 180, 'F', 'fix'), 'J3': (16.0, 20.0, 0, 'F', 'fix'), 'J4': (21.5, -23.0, 90, 'F', 'fix'),
    # --- battery protection, by the holder slot
    'U6': (8.0, 29.0, 0, 'F'), 'R18': (5.5, 23.0, 90, 'F'), 'C22': (7.5, 24.0, 90, 'F'), 'F1': (-8.0, 27.0, 90, 'F'),
    # --- tuner, upper middle
    'U1': (8.0, 13.0, 0, 'F'), 'Y1': (15.5, 12.0, 90, 'F'), 'C1': (17.5, 15.0, 0, 'F'), 'C2': (17.5, 9.0, 0, 'F'),
    'C3': (13.5, 17.5, 0, 'F'), 'C4': (13.5, 19.5, 0, 'F'), 'R1': (13.5, 6.0, 0, 'F'), 'C5': (13.5, 4.5, 0, 'F'),
    'U5': (11.0, 4.5, 0, 'F'),
    'R2': (1.0, 18.0, 90, 'F'), 'R3': (-1.0, 16.0, 90, 'F'), 'R4': (-1.0, 13.0, 90, 'F'),
    'C6': (2.0, 14.5, 90, 'F'), 'C7': (-3.5, 18.0, 90, 'F'), 'C21': (-3.5, 14.0, 90, 'F'),
    'R5': (1.0, 10.5, 0, 'F'), 'R17': (1.0, 8.5, 0, 'F'), 'R6': (-2.0, 8.5, 0, 'F'), 'C8': (2.0, 6.5, 0, 'F'),
    'RV2': (-12.0, 25.0, 90, 'F'),
    # --- antenna network, upper right next to the wire hole
    'C9': (12.0, 21.0, 90, 'F'), 'L1': (10.0, 19.5, 90, 'F'), 'D4': (12.5, 24.0, 0, 'F'),
    # --- audio, right side between the knob and the speaker pads
    'C10': (18.0, 4.0, 90, 'F'), 'R22': (19.5, 1.0, 90, 'F'), 'C11': (21.0, -6.5, 0, 'F'), 'R7': (21.0, -8.5, 0, 'F'),
    'R8': (28.0, -9.0, 90, 'F'), 'U2': (24.0, -13.5, 90, 'F'), 'C12': (19.5, -11.0, 90, 'F'), 'C13': (29.0, -14.0, 90, 'F'),
    'C14': (29.0, -17.5, 90, 'F'), 'R9': (20.0, -15.0, 90, 'F'), 'R10': (20.0, -18.0, 90, 'F'),
    # --- LDO between the knob switch and the tuner
    'U4': (16.0, -1.0, 0, 'F'), 'C18': (13.0, 0.5, 90, 'F'), 'C19': (19.0, -2.5, 0, 'F'), 'C20': (12.5, -2.5, 0, 'F'),
    # --- USB-C input, charger, load sharing: upper left
    'R11': (-23.0, 6.5, 90, 'F'), 'R12': (-23.0, 13.5, 90, 'F'), 'C15': (-22.5, 10.0, 90, 'F'),
    'U3': (-15.5, 14.0, 0, 'F'), 'R13': (-12.0, 18.5, 90, 'F'), 'R21': (-19.0, 18.5, 90, 'F'), 'R20': (-17.0, 18.5, 90, 'F'),
    'RT1': (-15.0, 18.5, 90, 'F'), 'D2': (-9.5, 21.0, 0, 'F'), 'D3': (-9.5, 23.5, 0, 'F'), 'R14': (-12.5, 21.0, 0, 'F'),
    'R15': (-12.5, 23.5, 0, 'F'), 'C16': (-11.0, 22.0, 90, 'F'),
    'Q1': (-15.0, 7.0, 0, 'F'), 'R16': (-18.5, 7.0, 90, 'F'), 'D1': (-11.0, 5.5, 0, 'F'), 'C17': (-7.0, 5.0, 90, 'F'),
}

# mechanical items: (footprint, x, y_up, rot, side)
MECH = [
    ('Speaker_D40_Outline', SPK[0], SPK[1], 0, 'B'),
    ('Speaker_Grille_D32', SPK[0], SPK[1], 0, 'F'),
    ('Holder_18650_EndFace_Outline', SLOT[0], SLOT[1], 180, 'B'),
    ('Logo_KOPN_15mm', -24.0, -9.0, 0, 'F'),
    ('Logo_CGW_14mm', -19.0, 16.0, 0, 'B'),
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
    text(board, 'COLUMBIA, MO', 0.0, -33.2, 1.1, pcbnew.F_SilkS, bold=True)
    text(board, 'BAT+', -5.0, 23.5, 0.8, pcbnew.F_SilkS)
    text(board, 'BAT-', -3.0, 29.0, 0.8, pcbnew.F_SilkS)
    text(board, 'CHG', -16.0, 21.0, 0.8, pcbnew.F_SilkS)
    text(board, 'FULL', -16.5, 23.5, 0.8, pcbnew.F_SilkS)
    text(board, 'KOPN 89.5 JAR RADIO rev B', 21.0, 15.5, 0.8, pcbnew.B_SilkS)
    text(board, 'COLUMBIA GADGET WORKS', 21.0, 13.5, 0.8, pcbnew.B_SilkS)
    text(board, 'CERN-OHL-S-2.0', 21.0, 11.5, 0.8, pcbnew.B_SilkS)
    text(board, 'after The Public Radio', 21.0, 9.8, 0.8, pcbnew.B_SilkS)
    text(board, 'PROTECTED 18650 ONLY', -24.0, 4.0, 0.8, pcbnew.B_SilkS)

    board.SetFileName(out_path)
    pcbnew.SaveBoard(out_path, board)
    return board
