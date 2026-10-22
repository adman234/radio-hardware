"""Writes the project-specific footprints into lib/jar-radio.pretty."""
import os, math

OUT = os.path.join(os.path.dirname(__file__), '..', 'lib', 'jar-radio.pretty')


def _hdr(name, descr, attr='through_hole'):
    return [f'(footprint "{name}" (version 20221018) (generator jar_radio_gen)',
            '  (layer "F.Cu")', f'  (descr "{descr}")', f'  (attr {attr})',
            f'  (fp_text reference "REF**" (at 0 -3) (layer "F.SilkS") hide (effects (font (size 1 1) (thickness 0.15))))',
            f'  (fp_text value "{name}" (at 0 3) (layer "F.Fab") hide (effects (font (size 1 1) (thickness 0.15))))']


def _circle(cx, cy, r, layer, w=0.12):
    return f'  (fp_circle (center {cx:.3f} {cy:.3f}) (end {cx + r:.3f} {cy:.3f}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))'


def _line(x1, y1, x2, y2, layer, w=0.12):
    return f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}"))'


def _text(s, x, y, layer, size=1.0, mirror=False):
    j = ' (justify mirror)' if mirror else ''
    return f'  (fp_text user "{s}" (at {x:.3f} {y:.3f}) (layer "{layer}") (effects (font (size {size} {size}) (thickness {size*0.15:.3f})){j}))'


def write(name, lines):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + '.kicad_mod'), 'w') as f:
        f.write('\n'.join(lines + [')']) + '\n')


def pth(num, x, y, drill, pad, shape='circle'):
    return f'  (pad "{num}" thru_hole {shape} (at {x:.3f} {y:.3f}) (size {pad} {pad}) (drill {drill}) (layers "*.Cu" "*.Mask"))'


def npth(x, y, drill):
    return f'  (pad "" np_thru_hole circle (at {x:.3f} {y:.3f}) (size {drill} {drill}) (drill {drill}) (layers "*.Cu" "*.Mask"))'


def npth_slot(x, y, w, h, angle=0):
    # oval slot w x h
    return f'  (pad "" np_thru_hole oval (at {x:.3f} {y:.3f} {angle}) (size {w} {h}) (drill oval {w} {h}) (layers "*.Cu" "*.Mask"))'


def zip_tie_pair(name='ZipTie_Slots_4mm_pitch12', pitch=12.0, slot_w=1.6, slot_l=4.5):
    """Two oval slots for a zip tie up to ~3.6 mm wide, centres `pitch` apart."""
    L = _hdr(name, f'Pair of NPTH slots for a <=3.6mm zip tie, {pitch}mm apart', 'exclude_from_pos_files exclude_from_bom')
    for sx in (-pitch / 2, pitch / 2):
        L.append(npth_slot(sx, 0, slot_w, slot_l))
        L.append(_line(sx - 1.6, -3.0, sx + 1.6, -3.0, 'B.SilkS'))
        L.append(_line(sx - 1.6, 3.0, sx + 1.6, 3.0, 'B.SilkS'))
    L.append(_text('TIE', 0, 0, 'B.SilkS', 0.8, mirror=True))
    write(name, L)


def sound_grille(name, dia_field, hole=1.8, pitch=3.0, bars=()):
    """Hex grid of NPTH holes filling a circle of diameter dia_field.

    bars: X offsets of solid vertical strips (5 mm wide) left free of holes,
    where a zip tie crosses the face of the lid."""
    L = _hdr(name, f'Speaker grille: {hole}mm NPTH holes, {pitch}mm hex pitch, {dia_field}mm field', 'exclude_from_pos_files exclude_from_bom')
    r = dia_field / 2 - hole / 2
    n = 0
    rows = int(r / (pitch * math.sin(math.pi / 3))) + 1
    for j in range(-rows, rows + 1):
        y = j * pitch * math.sin(math.pi / 3)
        off = (pitch / 2) if j % 2 else 0
        cols = int(r / pitch) + 2
        for i in range(-cols, cols + 1):
            x = i * pitch + off
            if math.hypot(x, y) <= r and all(abs(x - b) > 2.5 + hole / 2 for b in bars):
                L.append(npth(x, y, hole)); n += 1
    for b in bars:
        h = math.sqrt(max(r * r - b * b, 0))
        L.append(_line(b - 2.0, -h, b - 2.0, h, 'F.SilkS', 0.15))
        L.append(_line(b + 2.0, -h, b + 2.0, h, 'F.SilkS', 0.15))
    L.append(_circle(0, 0, dia_field / 2 + 0.6, 'F.SilkS', 0.2))
    write(name, L)
    return n


def antenna_mount(name='Antenna_Telescopic_M3_or_Wire'):
    """Plated M3 hole for a screw-base telescopic antenna plus a wire pad.

    Pad 1 = antenna (both the M3 ring and the wire hole are the same net).
    The M3 annulus is large on the top (outside) face so the antenna's base
    nut/lug clamps onto copper. The wire hole takes up to 22 AWG solid/stranded.
    """
    L = _hdr(name, 'Telescopic antenna (M3 screw/lug, 3.2mm PTH) OR wire antenna (1.0mm PTH) - same net')
    L.append(f'  (pad "1" thru_hole circle (at 0 0) (size 6.5 6.5) (drill 3.2) (layers "*.Cu" "*.Mask"))')
    L.append(f'  (pad "1" thru_hole circle (at 5.2 0) (size 2.0 2.0) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    # strain-relief hole for the wire (NPTH): wire loops through it before the pad
    L.append(npth(8.2, 0, 1.6))
    L.append(_text('ANT', 0, -4.6, 'F.SilkS', 1.0))
    L.append(_text('M3', 0, 4.6, 'F.SilkS', 0.8))
    L.append(_text('WIRE', 6.7, -2.2, 'F.SilkS', 0.7))
    L.append(_text('ANT / WIRE', 4, 4.6, 'B.SilkS', 0.8, mirror=True))
    L.append(_circle(0, 0, 4.2, 'F.CrtYd', 0.05))
    write(name, L)


def two_pads(name, pitch, drill, pad, labels=('+', '-'), descr='', relief=None):
    L = _hdr(name, descr)
    L.append(f'  (pad "1" thru_hole rect (at {-pitch/2:.3f} 0) (size {pad} {pad}) (drill {drill}) (layers "*.Cu" "*.Mask"))')
    L.append(pth('2', pitch / 2, 0, drill, pad))
    L.append(_text(labels[0], -pitch / 2, -pad, 'B.SilkS', 0.9, mirror=True))
    L.append(_text(labels[1], pitch / 2, -pad, 'B.SilkS', 0.9, mirror=True))
    if relief:
        L.append(npth(0, relief, 1.6))
    write(name, L)


if __name__ == '__main__':
    zip_tie_pair('ZipTie_Slots_P12', 12.0)
    zip_tie_pair('ZipTie_Slots_P20', 20.0)
    zip_tie_pair('ZipTie_Slots_P30', 30.0)
    antenna_mount()
    two_pads('Speaker_Wire_Pads_P5', 5.0, 1.1, 2.2, ('SPK+', 'SPK-'), 'Speaker lead solder pads (hand solder)')


def smd(num, x, y, w, h, layer='F', shape='roundrect'):
    lay = f'"{layer}.Cu" "{layer}.Paste" "{layer}.Mask"'
    rr = ' (roundrect_rratio 0.25)' if shape == 'roundrect' else ''
    return f'  (pad "{num}" smd {shape} (at {x:.3f} {y:.3f}) (size {w} {h}) (layers {lay}){rr})'


def rect(x1, y1, x2, y2, layer, w=0.12):
    return [_line(x1, y1, x2, y1, layer, w), _line(x2, y1, x2, y2, layer, w),
            _line(x2, y2, x1, y2, layer, w), _line(x1, y2, x1, y1, layer, w)]


def usb_c_vertical_6p():
    """SHOU HAN TYPE-C 6PLTH6.8-DJ (LCSC C5156600), vertical, from its
    recommended PCB layout: 6 pads in a row (GND VBUS CC1 CC2 VBUS GND),
    two 0.6x1.6 mm plated shell slots 8.64 mm apart."""
    name = 'USB_C_Receptacle_ShouHan_TYPE-C-6PLTH6.8-DJ_Vertical'
    L = _hdr(name, 'USB-C 6-pin power-only receptacle, vertical, SHOU HAN TYPE-C 6PLTH6.8-DJ (LCSC C5156600)', 'smd')
    pads = [('1', -2.75, 0.80), ('2', -1.51, 0.76), ('3', -0.50, 0.72),
            ('4', 0.50, 0.72), ('5', 1.51, 0.76), ('6', 2.75, 0.80)]
    for n, x, w in pads:
        L.append(smd(n, x, 0, w, 1.33))
    for sx in (-4.32, 4.32):
        L.append(f'  (pad "S" thru_hole oval (at {sx:.3f} -0.65) (size 1.0 2.2) (drill oval 0.6 1.6) (layers "*.Cu" "*.Mask"))')
    # receptacle outline (8.34 x 2.56 opening, body ~8.9 x 3.2)
    L += rect(-4.45, -2.6, 4.45, 0.75, 'F.Fab', 0.1)
    L += [_line(-3.6, -2.75, 3.6, -2.75, 'F.SilkS'), _line(-3.6, 0.95, -3.3, 0.95, 'F.SilkS'), _line(3.3, 0.95, 3.6, 0.95, 'F.SilkS')]
    L += rect(-5.2, -3.1, 5.2, 1.2, 'F.CrtYd', 0.05)
    L.append(_text('USB-C 5V', 0, -4.0, 'F.SilkS', 0.8))
    write(name, L)


def usb_c_vertical_6p_108():
    """SHOU HAN TYPE-C 6P LTH6.8 108 (LCSC C30167335), vertical, from its
    recommended PCB layout: 6 pads 0.80 x 1.30 at 1.10 mm pitch
    (GND VBUS CC1 CC2 VBUS GND), two 0.55 x 1.25 plated shell slots 8.60 mm
    apart, 0.68 mm behind the pad row."""
    name = 'USB_C_Receptacle_ShouHan_TYPE-C-6P-LTH6.8-108_Vertical'
    L = _hdr(name, 'USB-C 6-pin power-only receptacle, vertical, SHOU HAN TYPE-C 6P LTH6.8 108 (LCSC C30167335)', 'smd')
    for i in range(6):
        L.append(smd(str(i + 1), -2.75 + 1.10 * i, 0, 0.80, 1.30))
    for sx in (-4.30, 4.30):
        L.append(f'  (pad "S" thru_hole oval (at {sx:.3f} -0.68) (size 1.05 1.75) (drill oval 0.55 1.25) (layers "*.Cu" "*.Mask"))')
    # receptacle outline (8.35 x 2.56 opening, shell 8.85 x 3.06)
    L += rect(-4.43, -2.6, 4.43, 0.75, 'F.Fab', 0.1)
    L += [_line(-3.6, -2.75, 3.6, -2.75, 'F.SilkS'), _line(-3.6, 0.95, -3.3, 0.95, 'F.SilkS'), _line(3.3, 0.95, 3.6, 0.95, 'F.SilkS')]
    L += rect(-5.2, -3.1, 5.2, 1.2, 'F.CrtYd', 0.05)
    L.append(_text('USB-C 5V', 0, -4.0, 'F.SilkS', 0.8))
    write(name, L)


def xh_smd_gswitch():
    """G-Switch GT-A2501WRS-102SBT01 (LCSC C23067528): 2.5 mm XH-compatible,
    2-pin, SMD right angle. From the drawing's recommended PCB layout:
    1.30 x 4.50 signal pads, 1.80 x 3.90 mounting tabs, 11.0 mm overall."""
    name = 'Connector_XH-SMD_GSwitch_GT-A2501WRS-102_1x02_P2.50mm_Horizontal'
    L = _hdr(name, 'XH 2.50mm SMD right-angle 2-pin, G-Switch GT-A2501WRS-102SBT01 (LCSC C23067528)', 'smd')
    L.append(smd('1', -1.25, -3.25, 1.30, 4.50))
    L.append(smd('2', 1.25, -3.25, 1.30, 4.50))
    for tx in (-4.45, 4.45):
        L.append(smd('MP', tx, 3.55, 1.80, 3.90))
    L += rect(-2.95, -1.0, 2.95, 5.6, 'F.Fab', 0.1)
    L += rect(-5.6, -5.8, 5.6, 5.9, 'F.CrtYd', 0.05)
    L += [_line(-3.1, 1.2, -3.1, -0.6, 'F.SilkS'), _line(3.1, 1.2, 3.1, -0.6, 'F.SilkS'), _line(-3.1, 5.75, 3.1, 5.75, 'F.SilkS')]
    L.append(_text('opening', 0, 4.4, 'F.Fab', 0.6))
    write(name, L)


def rv097ns():
    """RV097NS 9 mm vertical pot with SPST switch, 5 pins.

    PROVISIONAL: no manufacturer drawing was available. Pot pins assumed at
    2.5 mm pitch, 6.5 mm in front of the shaft; switch pins 5.0 mm apart,
    6.5 mm behind the shaft; two support legs at +/-5.0 mm beside it. Holes are
    oversized (1.2 mm) to absorb clone variation. Measure a real part and
    correct this before ordering boards."""
    name = 'Potentiometer_RV097NS_Switch_Vertical_PROVISIONAL'
    L = _hdr(name, 'RV097NS 9mm pot + SPST switch, vertical, shaft at origin. PROVISIONAL: verify against a real part')
    for n, x in (('1', -2.5), ('2', 0.0), ('3', 2.5)):
        L.append(f'  (pad "{n}" thru_hole {"rect" if n == "1" else "circle"} (at {x} 6.5) (size 2.0 2.0) (drill 1.2) (layers "*.Cu" "*.Mask"))')
    for n, x in (('S1', -2.5), ('S2', 2.5)):
        L.append(f'  (pad "{n}" thru_hole circle (at {x} -6.5) (size 2.0 2.0) (drill 1.2) (layers "*.Cu" "*.Mask"))')
    for x in (-5.0, 5.0):
        L.append(f'  (pad "MP" thru_hole oval (at {x} 0) (size 2.2 3.4) (drill oval 1.4 2.6) (layers "*.Cu" "*.Mask"))')
    L += rect(-4.8, -7.5, 4.8, 7.5, 'F.Fab', 0.1)
    L.append(_circle(0, 0, 3.0, 'F.Fab', 0.1))
    L.append(_circle(0, 0, 8.0, 'F.SilkS', 0.15))   # 16 mm knob
    L += rect(-6.5, -8.0, 6.5, 8.0, 'F.CrtYd', 0.05)
    L.append(_text('VOL', 0, -9.2, 'F.SilkS', 0.9))
    write(name, L)


def zip_slot(name='ZipTie_Slot_4x1.6'):
    L = _hdr(name, 'Single NPTH slot for a <=3.6 mm zip tie (long axis along X)', 'exclude_from_pos_files exclude_from_bom')
    L.append(npth_slot(0, 0, 4.2, 1.6))
    L.append(f'  (pad "" np_thru_hole oval (at 0 0) (size 4.2 1.6) (drill oval 4.2 1.6) (layers "*.Cu" "*.Mask"))')
    L.pop(-2)
    L.append(_circle(0, 0, 2.6, 'F.CrtYd', 0.05))
    write(name, L)


def wire_exit(name='Antenna_Wire_Exit_D3.0'):
    L = _hdr(name, '3.0 mm hole for feeding the antenna wire out of the lid', 'exclude_from_pos_files exclude_from_bom')
    L.append(npth(0, 0, 3.0))
    L.append(_text('ANT OUT', 0, 3.2, 'F.SilkS', 0.7))
    write(name, L)


def ant_m3(name='Antenna_Telescopic_M3'):
    L = _hdr(name, 'Plated 3.2 mm hole for an M3 screw-base telescopic antenna (same net as the wire socket)')
    L.append(f'  (pad "1" thru_hole circle (at 0 0) (size 6.5 6.5) (drill 3.2) (layers "*.Cu" "*.Mask"))')
    L.append(_text('WHIP', 0, -4.4, 'F.SilkS', 0.8))
    L.append(_circle(0, 0, 3.6, 'F.CrtYd', 0.05))
    write(name, L)


def speaker_ring(name='Speaker_D49_Keepout'):
    """Courtyard/outline marker for the INGHAi GSPK4935 (Ø49 x 35 mm cavity
    speaker) or a generic Ø40 driver, mounted face-down on the back side."""
    L = _hdr(name, 'Speaker outline, Ø49 cavity speaker (GSPK4935) or Ø40 driver; place on B side', 'exclude_from_pos_files exclude_from_bom')
    L.append(_circle(0, 0, 24.5, 'F.SilkS', 0.15))
    L.append(_circle(0, 0, 20.0, 'F.Fab', 0.1))
    L.append(_circle(0, 0, 25.0, 'F.CrtYd', 0.05))
    L.append(_text('SPEAKER', 0, 22.5, 'F.SilkS', 1.0))
    write(name, L)


def build_all():
    usb_c_vertical_6p(); usb_c_vertical_6p_108(); xh_smd_gswitch(); rv097ns(); zip_slot(); wire_exit(); ant_m3(); speaker_ring()
    two_pads('Speaker_Wire_Pads_P5', 5.0, 1.1, 2.2, ('SPK+', 'SPK-'), 'Speaker lead solder pads (hand solder)')


def ant_solder(name='Antenna_Wire_Solder_D1.0'):
    """Solder hole for a single antenna wire, with a strain-relief hole the
    wire loops through first."""
    L = _hdr(name, 'Antenna wire solder hole (1.0 mm PTH) + 1.6 mm strain-relief hole')
    L.append(f'  (pad "1" thru_hole circle (at 0 0) (size 2.0 2.0) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    L.append(npth(3.0, 0, 1.6))
    L.append(_text('ANT', 0, -2.0, 'F.SilkS', 0.8))
    L.append(_circle(1.5, 0, 3.0, 'F.CrtYd', 0.05))
    write(name, L)


def batt_tab_slot(name='Battery_Holder_Tab_Slot_Plus_Wire'):
    """18650 holder BH-18650-B1BA002: its end tab goes through a plated oval
    slot and is hand-soldered (holder hot-glued to the inside face); the far
    terminal comes back on a jumper wire to the round pad.
    PROVISIONAL slot size until the holder drawing is checked."""
    L = _hdr(name, 'Plated oval slot for an 18650 holder solder tab + 1.2 mm pad for the return jumper wire')
    L.append('  (pad "1" thru_hole oval (at 0 0) (size 7.6 2.4) (drill oval 6.4 1.2) (layers "*.Cu" "*.Mask"))')
    L.append('  (pad "2" thru_hole circle (at 0 6.0) (size 2.4 2.4) (drill 1.2) (layers "*.Cu" "*.Mask"))')
    L.append(npth(3.5, 6.0, 1.6))
    L.append(_text('TAB', -5.2, 0, 'F.SilkS', 0.8))
    L.append(_text('WIRE', -5.2, 6.0, 'F.SilkS', 0.8))
    L += rect(-4.6, -1.8, 5.8, 7.8, 'F.CrtYd', 0.05)
    write(name, L)


def ptv09_rear(name='Potentiometer_Bourns_PTV09A-4_RearMount'):
    """Bourns PTV09A-4 (horizontal/rear mount, bushingless): shaft
    perpendicular to the board. From the datasheet's recommended layout:
    3 pins ø1.0 at 2.5 mm pitch, 7.0 mm below two 2.2 x 1.8 mounting slots
    10.6 mm apart; shaft centred between the slots."""
    L = _hdr(name, 'Bourns PTV09A-4 9mm pot, rear mount (shaft up), no switch')
    for n, x in (('1', -2.5), ('2', 0.0), ('3', 2.5)):
        L.append(f'  (pad "{n}" thru_hole {"rect" if n == "1" else "circle"} (at {x} 7.0) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    for x in (-5.3, 5.3):
        L.append(f'  (pad "MP" thru_hole oval (at {x} 0) (size 2.8 3.2) (drill oval 1.8 2.2) (layers "*.Cu" "*.Mask"))')
    L += rect(-5.0, -5.5, 5.0, 5.9, 'F.Fab', 0.1)
    L.append(_circle(0, 0, 3.0, 'F.Fab', 0.1))
    L.append(_circle(0, 0, 8.0, 'F.SilkS', 0.15))
    L += rect(-6.6, -6.0, 6.6, 8.3, 'F.CrtYd', 0.05)
    L.append(_text('VOL', 0, -9.2, 'F.SilkS', 0.9))
    write(name, L)


def ant_solder_tie(name='Antenna_Wire_Solder_D1.0'):
    """Antenna wire solder hole + a pair of zip-tie holes for strain relief."""
    L = _hdr(name, 'Antenna wire solder hole (1.0 mm PTH) + 2 zip-tie holes for strain relief')
    L.append('  (pad "1" thru_hole circle (at 0 0) (size 2.0 2.0) (drill 1.0) (layers "*.Cu" "*.Mask"))')
    for x in (3.5, 7.5):
        L.append(f'  (pad "" np_thru_hole oval (at {x} 0) (size 1.4 3.0) (drill oval 1.4 3.0) (layers "*.Cu" "*.Mask"))')
    L.append(_text('ANT', 0, -2.0, 'F.SilkS', 0.8))
    L += rect(-1.3, -2.0, 8.6, 2.0, 'F.CrtYd', 0.05)
    write(name, L)


def batt_tab_slot_v2(name='Battery_Holder_Tab_Slot_Plus_Wire'):
    """MYOUNG BH-18650-B1BA002 standing on end: its 6.35 x 0.35 mm SMT foot
    goes through this plated slot and is soldered on top; the other end
    returns on a jumper wire to pad 2."""
    L = _hdr(name, 'Plated slot for the 18650 holder foot (6.35 x 0.35 mm) + pad for the return wire')
    L.append('  (pad "1" thru_hole oval (at 0 0) (size 8.4 2.2) (drill oval 7.0 1.0) (layers "*.Cu" "*.Mask"))')
    L.append('  (pad "2" thru_hole circle (at 0 5.5) (size 2.4 2.4) (drill 1.2) (layers "*.Cu" "*.Mask"))')
    L.append(npth(3.5, 5.5, 1.6))
    L.append(_text('BAT+', -6.0, 0, 'F.Fab', 0.8))
    L.append(_text('BAT-', -3.0, 5.5, 'F.Fab', 0.8))
    L += rect(-4.6, -1.6, 5.0, 7.2, 'F.CrtYd', 0.05)
    write(name, L)


def r09512ns_rear(name='Potentiometer_CTR_R09512NS_RearMount_Switch'):
    """CTR R09512NS (LCSC C18213422): 9 mm pot + rotary SPST switch, rear
    mount, shaft perpendicular to the board. From the datasheet's mounting
    hole detail (shaft axis at origin): two 1.8 x 1.2 mm tab slots 11.3 mm
    over their outer edges on the axis line; switch pins 5 mm apart 6.45 mm
    from the axis; pot pins 1-2-3 at 2.5 mm pitch 2.5 mm further out.
    Holes 1.0 +0.2 mm."""
    L = _hdr(name, 'CTR R09512NS 9mm pot with rotary switch, rear mount (shaft up), LCSC C18213422')
    for n, x in (('1', -2.5), ('2', 0.0), ('3', 2.5)):
        L.append(f'  (pad "{n}" thru_hole {"rect" if n == "1" else "circle"} (at {x} 8.95) (size 1.8 1.8) (drill 1.1) (layers "*.Cu" "*.Mask"))')
    for n, x in (('S1', -2.5), ('S2', 2.5)):
        L.append(f'  (pad "{n}" thru_hole circle (at {x} 6.45) (size 1.8 1.8) (drill 1.1) (layers "*.Cu" "*.Mask"))')
    for x in (-4.75, 4.75):
        L.append(f'  (pad "MP" thru_hole oval (at {x} 0) (size 2.6 2.0) (drill oval 1.8 1.2) (layers "*.Cu" "*.Mask"))')
    L += rect(-5.3, -4.8, 5.3, 6.0, 'F.Fab', 0.1)
    L.append(_circle(0, 0, 3.0, 'F.Fab', 0.1))
    L.append(_circle(0, 0, 8.0, 'F.Fab', 0.1))   # 16 mm knob
    L += rect(-6.3, -10.2, 6.3, 10.2, 'F.CrtYd', 0.05)   # includes the VOL / OFF label
    L.append(_text('VOL / OFF', 0, -9.2, 'F.SilkS', 0.9))
    write(name, L)


def speaker_d40(name='Speaker_D40_Outline'):
    """Inside-face outline of the Dragonstate HDK-4008BB-2 (Ø40 x 5.3 mm),
    hot-glued face-down under the grille."""
    L = _hdr(name, 'Ø40 speaker outline, inside face (place on B)', 'exclude_from_pos_files exclude_from_bom')
    L.append(_circle(0, 0, 20.0, 'F.SilkS', 0.15))
    L.append(_circle(0, 0, 20.5, 'F.CrtYd', 0.05))
    L.append(_text('SPEAKER (glue)', 0, 17.0, 'F.SilkS', 1.0))
    write(name, L)


def holder_18650_outline(name='Holder_18650_EndFace_Outline'):
    """Inside-face outline of the BH-18650-B1BA002 end face (20.65 x 14.9 mm)
    standing on end; origin = the foot slot, body on the +Y side."""
    L = _hdr(name, '18650 holder end face outline, inside face (place on B); origin at foot slot', 'exclude_from_pos_files exclude_from_bom')
    L += rect(-10.33, 0.5, 10.33, 15.4, 'F.SilkS', 0.15)
    L += rect(-10.6, 0.3, 10.6, 15.6, 'F.CrtYd', 0.05)
    L.append(_text('18650 HOLDER', 0, 7.0, 'F.SilkS', 1.0))
    L.append(_text('+ end at slot, glue', 0, 9.0, 'F.SilkS', 0.8))
    write(name, L)


def build_f12():
    sound_grille('Speaker_Grille_D32', 32.0, hole=1.8, pitch=2.6)
    speaker_d40(); holder_18650_outline(); r09512ns_rear(); usb_c_vertical_6p_108()


# Dragonstate HDK-4008BB-2 back face, from the user's DXF ("rendering 2", KiCad
# axes: y down, terminal block pointing +y). Two exposed triangular tab pads
# flank the potted terminal block; the magnet cup is Ø16.2 x 3 mm.
SPK_PADS = {'1': [(-7.78, 12.63), (-4.33, 8.67), (-4.85, 14.28)],
            '2': [(4.12, 14.43), (3.97, 9.03), (7.14, 13.02)]}
SPK_BLOCK = [(-4.33, 8.67), (3.97, 9.03), (4.12, 14.43), (4.12, 15.75), (-4.85, 15.36), (-4.85, 14.28)]
# the DXF's second rendering, rotated onto the first and aligned on the block
SPK_PADS_ALT = {'1': [(-7.33, 13.45), (-4.29, 9.39), (-4.45, 14.71)],
                '2': [(3.72, 14.12), (3.88, 8.90), (6.58, 12.38)]}
SPK_BLOCK_ALT = [(-4.29, 9.39), (3.88, 8.90), (3.72, 14.12), (3.73, 15.26), (-4.49, 15.97), (-4.45, 14.71)]


def speaker_top(name='Speaker_HDK-4008BB-2_TopMount'):
    """HDK-4008BB-2 sitting on the top face, back down. Board cutout: a
    Ø16.8 hole for the Ø16.2 magnet cup, joined to a slot for the potted
    terminal block. The two tab pads are mirror images about the speaker's
    centre line (the DXF's slight asymmetry is drafting, not the part), each
    covering both renderings of both tabs. Pads are plated through with copper
    on both faces: heat from the inside face and solder flows up into the
    speaker's tabs."""
    from shapely.geometry import Polygon, Point, box
    from shapely.ops import unary_union
    from shapely import affinity
    L = _hdr(name, 'Dragonstate HDK-4008BB-2 Ø40 speaker, top mount, soldered by its two back tabs; board cutout included')
    mirror = lambda g: affinity.scale(g, xfact=-1, origin=(0, 0))
    # left tab: hull of every rendering of both tabs, folded onto the left side
    tabs = [Polygon(SPK_PADS['1']), Polygon(SPK_PADS_ALT['1']),
            mirror(Polygon(SPK_PADS['2'])), mirror(Polygon(SPK_PADS_ALT['2']))]
    left = unary_union(tabs).convex_hull
    blk = unary_union([Polygon(SPK_BLOCK), Polygon(SPK_BLOCK_ALT)])
    bw = max(-blk.bounds[0], blk.bounds[2]) + 0.35                 # symmetric slot half-width
    cup_r = 16.8 / 2                                               # Ø16.2 cup + 0.3 per side
    slot = box(-bw, 0, bw, blk.bounds[3] + 0.35)
    hole = unary_union([Point(0, 0).buffer(cup_r, resolution=64), slot])
    hole = hole.buffer(0.5, resolution=8).buffer(-0.5, resolution=8)       # round inside corners (router bit)
    ring = list(hole.exterior.coords)
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        L.append(_line(x1, y1, x2, y2, 'Edge.Cuts', 0.1))
    cu_l = left.buffer(0.4, join_style=2).difference(hole.buffer(0.45, join_style=2))
    cu_l = cu_l.buffer(0.15).buffer(-0.15)
    if cu_l.geom_type != 'Polygon':
        cu_l = max(cu_l.geoms, key=lambda g: g.area)
    for k, cu in (('1', cu_l), ('2', mirror(cu_l))):
        # anchor: the point deepest inside the pad, for the plated hole
        best, bd = cu.representative_point(), -1
        x0, y0, x1, y1 = cu.bounds
        for i in range(41):
            for j in range(41):
                p = Point(x0 + (x1 - x0) * i / 40, y0 + (y1 - y0) * j / 40)
                if cu.contains(p) and cu.exterior.distance(p) > bd:
                    best, bd = p, cu.exterior.distance(p)
        ax, ay = best.x, best.y
        if k == '1':
            anchor = (ax, ay)
        else:
            ax, ay = -anchor[0], anchor[1]                            # exact mirror of pad 1
        pts = ' '.join(f'(xy {x - ax:.3f} {y - ay:.3f})' for x, y in list(cu.exterior.coords)[:-1])
        L.append(f'  (pad "{k}" thru_hole custom (at {ax:.3f} {ay:.3f}) (size 1.6 1.6) (drill 1.0) (layers "*.Cu" "*.Mask")'
                 f' (options (clearance outline) (anchor circle))'
                 f' (primitives (gr_poly (pts {pts}) (width 0) (fill yes))))')
    L.append(_circle(0, 0, 20.0, 'F.Fab', 0.1))
    L.append(_circle(0, 0, 20.2, 'F.SilkS', 0.15))            # placement ring, hidden once the speaker is on
    L.append(_circle(0, 0, 20.6, 'F.CrtYd', 0.05))
    L.append(_text('SPEAKER', 0, -17.5, 'F.Fab', 1.0))
    write(name, L)
