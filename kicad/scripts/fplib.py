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


def sound_grille(name, dia_field, hole=1.8, pitch=3.0):
    """Hex grid of NPTH holes filling a circle of diameter dia_field."""
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
            if math.hypot(x, y) <= r:
                L.append(npth(x, y, hole)); n += 1
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
