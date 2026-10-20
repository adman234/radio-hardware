"""Tiny KiCad 7 schematic writer.

Every symbol is generated here (box symbols with pins on the left/right,
two-pin parts vertical), and every pin is tied to its net with a short wire
stub and a local label. That keeps the generated schematic readable without
needing an auto-router for wires.
"""
import uuid as _uuid

G = 2.54  # grid

def uid():
    return str(_uuid.uuid4())

def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

FONT = '(effects (font (size 1.27 1.27)))'
FONT_HIDE = '(effects (font (size 1.27 1.27)) hide)'


class SymDef:
    """A symbol definition. pins: list of (number, name, side, slot).

    side is one of L, R, T, B. slot is the position along that side in grid
    units (0 = top/left-most)."""

    def __init__(self, name, ref_prefix, pins, width=None, height=None,
                 two_pin=False, body='box', show_pin_names=True):
        self.name = name
        self.ref_prefix = ref_prefix
        self.two_pin = two_pin
        self.body = body
        self.show_pin_names = show_pin_names
        self.pins = []  # (num, name, x, y, angle)  in symbol coords (y up)
        if two_pin:
            # vertical part: pin 1 on top, pin 2 at bottom
            (n1, nm1, *_), (n2, nm2, *_) = pins
            self.pins = [(n1, nm1, 0, 3.81, 270), (n2, nm2, 0, -3.81, 90)]
            self.w, self.h = 1.016, 2.54
            return
        left = [p for p in pins if p[2] == 'L']
        right = [p for p in pins if p[2] == 'R']
        top = [p for p in pins if p[2] == 'T']
        bot = [p for p in pins if p[2] == 'B']
        nrows = max([p[3] for p in left + right] + [0]) + 1
        ncols = max([p[3] for p in top + bot] + [0]) + 1
        self.h = height or (nrows + 1) * G
        self.w = width or max(4 * G, (ncols + 1) * G)
        hw, hh = self.w / 2, self.h / 2
        for num, nm, side, slot in pins:
            if side == 'L':
                self.pins.append((num, nm, -hw - G, hh - G - slot * G, 0))
            elif side == 'R':
                self.pins.append((num, nm, hw + G, hh - G - slot * G, 180))
            elif side == 'T':
                self.pins.append((num, nm, -hw + G + slot * G, hh + G, 270))
            elif side == 'B':
                self.pins.append((num, nm, -hw + G + slot * G, -hh - G, 90))

    def sexpr(self, lib):
        n = self.name
        out = [f'(symbol {q(lib + ":" + n)} (in_bom yes) (on_board yes)']
        if not self.show_pin_names:
            out[0] += ' (pin_names hide)'
        if self.two_pin:
            out[0] += ' (pin_numbers hide)'
        out.append(f'  (property "Reference" {q(self.ref_prefix)} (at 2.032 0.762 0) (effects (font (size 1.27 1.27)) (justify left)))')
        out.append(f'  (property "Value" {q(n)} (at 2.032 -1.016 0) (effects (font (size 1.27 1.27)) (justify left)))')
        out.append(f'  (property "Footprint" "" (at 0 0 0) {FONT_HIDE})')
        out.append(f'  (property "Datasheet" "" (at 0 0 0) {FONT_HIDE})')
        out.append(f'  (symbol {q(n + "_0_1")}')
        if self.two_pin:
            if self.body == 'cap':
                out.append('    (polyline (pts (xy -1.524 0.508) (xy 1.524 0.508)) (stroke (width 0.3) (type default)) (fill (type none)))')
                out.append('    (polyline (pts (xy -1.524 -0.508) (xy 1.524 -0.508)) (stroke (width 0.3) (type default)) (fill (type none)))')
                out.append('    (polyline (pts (xy 0 1.27) (xy 0 0.508)) (stroke (width 0) (type default)) (fill (type none)))')
                out.append('    (polyline (pts (xy 0 -1.27) (xy 0 -0.508)) (stroke (width 0) (type default)) (fill (type none)))')
            elif self.body in ('led', 'diode'):
                # anode (pin 2, bottom) -> cathode (pin 1, top): triangle pointing up
                out.append('    (polyline (pts (xy -1.27 -0.762) (xy 1.27 -0.762) (xy 0 0.762) (xy -1.27 -0.762)) (stroke (width 0.254) (type default)) (fill (type none)))')
                out.append('    (polyline (pts (xy -1.27 0.762) (xy 1.27 0.762)) (stroke (width 0.254) (type default)) (fill (type none)))')
                out.append('    (polyline (pts (xy 0 1.27) (xy 0 0.762)) (stroke (width 0) (type default)) (fill (type none)))')
                out.append('    (polyline (pts (xy 0 -1.27) (xy 0 -0.762)) (stroke (width 0) (type default)) (fill (type none)))')
                if self.body == 'led':
                    out.append('    (polyline (pts (xy 1.524 0) (xy 2.54 1.016)) (stroke (width 0) (type default)) (fill (type none)))')
                    out.append('    (polyline (pts (xy 1.524 -0.762) (xy 2.54 0.254)) (stroke (width 0) (type default)) (fill (type none)))')
            else:
                out.append('    (rectangle (start -0.762 1.27) (end 0.762 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))')
        else:
            out.append(f'    (rectangle (start {-self.w/2} {self.h/2}) (end {self.w/2} {-self.h/2}) (stroke (width 0.254) (type default)) (fill (type background)))')
        out.append('  )')
        out.append(f'  (symbol {q(n + "_1_1")}')
        for num, nm, x, y, a in self.pins:
            ln = 2.54
            out.append(f'    (pin passive line (at {x:.3f} {y:.3f} {a}) (length {ln}) (name {q(nm)} {FONT}) (number {q(num)} {FONT}))')
        out.append('  )')
        out.append(')')
        return '\n'.join(out)


class Schematic:
    def __init__(self, title, lib='jar-radio', project='jar-radio'):
        self.title = title
        self.lib = lib
        self.project = project
        self.root = uid()
        self.defs = {}
        self.items = []
        self.parts = []   # dicts for downstream (pcb/bom)
        self.nets = {}    # net -> list of (ref, pin)

    def add_def(self, d):
        self.defs[d.name] = d

    def part(self, ref, sym, value, x, y, nets, footprint='', lcsc='', mpn='',
             fields=None, dnp=False, nc=()):
        d = self.defs[sym]
        u = uid()
        props = [
            ('Reference', ref, (x + (2.032 if d.two_pin else -d.w/2), y - (0.762 if d.two_pin else d.h/2 + 1.27)), False),
            ('Value', value, (x + (2.032 if d.two_pin else -d.w/2), y + (1.016 if d.two_pin else d.h/2 + 1.27)), False),
            ('Footprint', footprint, (x, y), True),
            ('Datasheet', '', (x, y), True),
            ('LCSC', lcsc, (x, y), True),
            ('MPN', mpn, (x, y), True),
        ]
        for k, v in (fields or {}).items():
            props.append((k, v, (x, y), True))
        s = [f'(symbol (lib_id {q(self.lib + ":" + sym)}) (at {x:.3f} {y:.3f} 0) (unit 1)',
             f'  (in_bom yes) (on_board yes) (dnp {"yes" if dnp else "no"}) (uuid {u})']
        for i, (k, v, (px, py), hide) in enumerate(props):
            just = ' (justify left)'
            eff = f'(effects (font (size 1.27 1.27)){just}{" hide" if hide else ""})'
            s.append(f'  (property {q(k)} {q(v)} (at {px:.3f} {py:.3f} 0) {eff})')
        for num, *_ in d.pins:
            s.append(f'  (pin {q(num)} (uuid {uid()}))')
        s.append(f'  (instances (project {q(self.project)} (path {q("/" + self.root)} (reference {q(ref)}) (unit 1))))')
        s.append(')')
        self.items.append('\n'.join(s))
        self.parts.append(dict(ref=ref, sym=sym, value=value, footprint=footprint,
                               lcsc=lcsc, mpn=mpn, uuid=u, nets=dict(nets), dnp=dnp,
                               fields=fields or {}))
        # pins
        pinnums = {p[0] for p in d.pins}
        for pn in list(nets) + list(nc):
            if pn not in pinnums:
                raise ValueError(f'{ref}: no pin {pn}')
        for num, nm, px, py, a in d.pins:
            ax, ay = x + px, y - py
            if num in nets:
                net = nets[num]
                self.nets.setdefault(net, []).append((ref, num))
                # stub direction: away from body
                dx, dy = {0: (-1, 0), 180: (1, 0), 270: (0, -1), 90: (0, 1)}[a]
                L = 2.54
                ex, ey = ax + dx * L, ay + dy * L
                self.items.append(f'(wire (pts (xy {ax:.3f} {ay:.3f}) (xy {ex:.3f} {ey:.3f})) (stroke (width 0) (type default)) (uuid {uid()}))')
                ang, just = {(-1, 0): (0, 'right'), (1, 0): (0, 'left'), (0, -1): (90, 'left'), (0, 1): (90, 'right')}[(dx, dy)]
                self.items.append(f'(label {q(net)} (at {ex:.3f} {ey:.3f} {ang}) (fields_autoplaced) (effects (font (size 1.016 1.016)) (justify {just} bottom)) (uuid {uid()}))')
            else:
                self.items.append(f'(no_connect (at {ax:.3f} {ay:.3f}) (uuid {uid()}))')

    def text(self, s, x, y, size=1.27, bold=False):
        b = ' bold' if bold else ''
        self.items.append(f'(text {q(s)} (at {x:.3f} {y:.3f} 0) (effects (font (size {size} {size}){b}) (justify left bottom)) (uuid {uid()}))')

    def box(self, x1, y1, x2, y2):
        self.items.append(f'(rectangle (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.2) (type dash)) (fill (type none)) (uuid {uid()}))')

    def write(self, path, paper='A3', rev='', date='', comments=()):
        out = [f'(kicad_sch (version 20230121) (generator eeschema)', f'  (uuid {self.root})',
               f'  (paper {q(paper)})',
               f'  (title_block (title {q(self.title)}) (date {q(date)}) (rev {q(rev)})']
        for i, c in enumerate(comments, 1):
            out.append(f'    (comment {i} {q(c)})')
        out.append('  )')
        out.append('  (lib_symbols')
        for d in self.defs.values():
            out.append('    ' + d.sexpr(self.lib).replace('\n', '\n    '))
        out.append('  )')
        for it in self.items:
            out.append('  ' + it.replace('\n', '\n  '))
        out.append('  (sheet_instances (path "/" (page "1")))')
        out.append(')')
        with open(path, 'w') as f:
            f.write('\n'.join(out) + '\n')

    def write_lib(self, path):
        out = ['(kicad_symbol_lib (version 20220914) (generator jar_radio_gen)']
        for d in self.defs.values():
            out.append('  ' + d.sexpr(self.lib).replace(f'"{self.lib}:', '"').replace('\n', '\n  '))
        out.append(')')
        with open(path, 'w') as f:
            f.write('\n'.join(out) + '\n')
