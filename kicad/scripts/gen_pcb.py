"""Builds jar-radio.kicad_pcb from circuit.py: outline, placement, nets,
zones, clamp-ring keepout, holes and artwork. Routing is done afterwards by
route.py (Freerouting).

Coordinates in PLACE are millimetres from the board centre, X right and
Y UP as seen from the top (outside) face. 'B' parts sit on the inside face.
Board geometry is provisional until the jar is measured (see GEOM).
"""
import math, os
import pcbnew
import circuit

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
STD = '/usr/share/kicad/footprints'
OWN = os.path.join(PROJ, 'lib', 'jar-radio.pretty')

GEOM = dict(
    od=85.5,          # board diameter = wide-mouth flat lid (MEASURE)
    top_keep=34.0,    # radius of the visible window inside the band lip (MEASURE)
    bot_keep=36.0,    # radius usable inside the jar mouth (MEASURE)
    clamp=36.5,       # outside this radius: solid GND both sides, no tracks
)
CX, CY = 150.0, 100.0     # board centre in KiCad page coordinates
SPK = (-11.0, 0.0)        # speaker centre

# ref: (x, y_up, rotation_deg_seen_from_top, side[, 'fix'])
# Parts without 'fix' are a starting point: place.py moves them to the
# nearest spot where their courtyard is clear of everything else.
PLACE = {
    # --- top face, hand-soldered, fixed
    'RV1': (10.0, -23.0, 0, 'F', 'fix'), 'J1': (27.0, -11.0, 90, 'F', 'fix'), 'ANT1': (27.0, 15.0, 0, 'F', 'fix'),
    # --- tuner, right middle (inside face)
    'U1': (22.0, 4.0, 0, 'B'), 'Y1': (30.0, 2.0, 90, 'B'), 'C1': (31.0, 6.0, 90, 'B'), 'C2': (31.0, -2.0, 90, 'B'),
    'C3': (26.0, 10.5, 0, 'B'), 'C4': (24.0, 11.0, 0, 'B'), 'R1': (20.0, 11.0, 0, 'B'), 'C5': (18.0, 11.0, 0, 'B'),
    'U5': (21.0, 13.5, 0, 'B'),
    'R2': (16.0, 6.0, 90, 'B'), 'R3': (16.0, 2.5, 90, 'B'), 'R4': (16.0, -1.0, 90, 'B'),
    'C6': (17.5, 9.0, 90, 'B'), 'C7': (14.5, 9.0, 90, 'B'), 'R5': (16.0, -4.0, 0, 'B'), 'R6': (18.5, -4.5, 0, 'B'),
    'C8': (18.0, -2.0, 0, 'B'), 'RV2': (13.5, -7.0, 90, 'B'),
    # --- antenna input, upper right
    'J3': (15.0, 23.0, 0, 'B'), 'D4': (10.0, 20.0, 90, 'B'), 'C9': (12.5, 16.5, 90, 'B'), 'L1': (15.0, 15.5, 0, 'B'),
    # --- audio
    'U2': (22.0, -12.0, 90, 'B'), 'C10': (27.0, -4.0, 0, 'B'), 'C11': (18.0, -9.0, 0, 'B'), 'R7': (18.0, -11.0, 0, 'B'),
    'R8': (18.0, -13.0, 0, 'B'), 'C12': (18.0, -15.0, 0, 'B'), 'C13': (26.0, -15.0, 0, 'B'), 'C14': (26.0, -13.5, 0, 'B'),
    'R9': (19.0, -17.0, 0, 'B'), 'R10': (21.0, -17.5, 0, 'B'), 'J4': (28.0, -3.0, 90, 'B'),
    # --- power, lower area
    'R11': (31.0, -8.0, 90, 'B'), 'R12': (31.0, -14.0, 90, 'B'), 'C15': (24.0, -7.0, 0, 'B'),
    'U3': (21.0, -24.0, 90, 'B'), 'R13': (17.0, -26.0, 90, 'B'),
    'D2': (23.5, -15.0, 90, 'B'), 'D3': (23.5, -19.0, 90, 'B'), 'C21': (14.0, 24.0, 90, 'B'), 'R14': (26.0, -19.0, 90, 'B'), 'R15': (26.5, -22.0, 90, 'B'),
    'C16': (5.0, -32.0, 0, 'B'), 'J2': (0.0, -30.0, 0, 'B'),
    'Q1': (24.0, -28.0, 0, 'B'), 'R16': (27.5, -25.0, 90, 'B'), 'D1': (19.0, -31.0, 0, 'B'),
    'C17': (15.0, -32.0, 0, 'B'), 'C18': (29.5, -17.5, 90, 'B'), 'U4': (28.5, -21.0, 0, 'B'),
    'C19': (31.0, -19.5, 90, 'B'), 'C20': (27.0, -27.0, 0, 'B'),
}

# mechanical items: (footprint, x, y_up, rot, side)
MECH = [
    ('Speaker_D49_Keepout', SPK[0], SPK[1], 0, 'B'),
    ('Speaker_Grille_D36_2Bars', SPK[0], SPK[1], 0, 'F'),
    # zip ties across the speaker + battery stack: slots above and below the speaker
    ('ZipTie_Slot_4x1.6', SPK[0] - 8, 26.8, 0, 'F'), ('ZipTie_Slot_4x1.6', SPK[0] - 8, -26.8, 0, 'F'),
    ('ZipTie_Slot_4x1.6', SPK[0] + 8, 26.8, 0, 'F'), ('ZipTie_Slot_4x1.6', SPK[0] + 8, -26.8, 0, 'F'),
    ('Antenna_Wire_Exit_D3.0', 31.5, -2.0, 0, 'F'),
    ('Logo_KOPN_15mm', 14.5, 11.0, 0, 'F'),
    ('Logo_CGW_14mm', -11.0, 0.0, 0, 'B'),
]

POWER_NETS = {'GND', 'VBUS', 'VBAT', 'VSYS', 'VSW', 'SPK+', 'SPK-'}


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
        fp.Reference().SetVisible(not fp.IsFlipped())   # inside face: refs live on the fab layer only
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))

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
    text(board, 'COLUMBIA, MO', 14.5, 1.6, 1.3, pcbnew.F_SilkS, bold=True)
    
    text(board, 'KOPN 89.5 JAR RADIO  rev A', -11.0, -12.0, 1.0, pcbnew.B_SilkS)
    text(board, 'COLUMBIA GADGET WORKS', -11.0, 10.0, 1.0, pcbnew.B_SilkS)
    for ref, label in (('J2', 'BATT +/-'), ('J4', 'SPEAKER'), ('J3', 'ANTENNA')):
        fp = placed[ref]; c = fp.GetPosition()
        text(board, label, pcbnew.ToMM(c.x) - CX, CY - pcbnew.ToMM(c.y) - 5.6, 0.9, pcbnew.B_SilkS)
    text(board, 'CERN-OHL-S-2.0  after The Public Radio', -11.0, -14.0, 0.8, pcbnew.B_SilkS)

    board.SetFileName(out_path)
    pcbnew.SaveBoard(out_path, board)
    return board
