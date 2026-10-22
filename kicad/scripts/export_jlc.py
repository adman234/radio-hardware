"""Writes the JLCPCB order files into kicad/jlcpcb/:
gerbers + drill zip, BOM.csv and CPL.csv (all on the top face), plus PNG
renders of both faces into docs/img/."""
import csv, os, subprocess, zipfile, shutil, glob
import circuit

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
BOARD = os.path.join(PROJ, 'jar-radio.kicad_pcb')
OUT = os.path.join(PROJ, 'jlcpcb')
LAYERS = 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)


def gerbers():
    g = os.path.join(OUT, 'gerber')
    shutil.rmtree(g, ignore_errors=True); os.makedirs(g)
    run('kicad-cli', 'pcb', 'export', 'gerbers', BOARD, '-o', g + '/', '--layers', LAYERS, '--subtract-soldermask', '--no-x2')
    run('kicad-cli', 'pcb', 'export', 'drill', BOARD, '-o', g + '/', '--format', 'excellon', '--excellon-units', 'mm',
        '--excellon-separate-th', '--generate-map', '--map-format', 'gerberx2')
    z = os.path.join(OUT, 'jar-radio-gerbers.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as f:
        for p in sorted(glob.glob(g + '/*')):
            f.write(p, os.path.basename(p))
    return z


def bom():
    rows = {}
    for p in circuit.P:
        if p.get('dnp') or p.get('hand') or p.get('nobom'):
            continue
        fp = p['footprint'].split(':')[1]
        key = (p['value'], fp, p['lcsc'], p['mpn'])
        rows.setdefault(key, []).append(p['ref'])
    path = os.path.join(OUT, 'BOM.csv')
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'MPN', 'Qty'])
        for (v, fp, lc, mpn), refs in sorted(rows.items(), key=lambda kv: kv[1][0]):
            w.writerow([v, ','.join(sorted(refs, key=lambda r: (r.rstrip('0123456789'), int(r[len(r.rstrip('0123456789')):] or 0)))),
                        fp, lc, mpn, len(refs)])
    return path


# JLC's library parts don't share KiCad's zero orientation or origin. These
# were checked against JLC's assembly preview (pink dot = JLC pin 1):
#   SOIC/ESOP: JLC zero has the pins along top/bottom with pin 1 bottom-left,
#              KiCad has them along left/right with pin 1 top-left -> -90
#   SOT-23:    pin 1 on the opposite corner -> +180
ROT_CORR = [(r'^SOIC-', -90), (r'^SOT-23$', 180)]
# footprint-local offset (mm, KiCad axes) from our origin to the centre JLC uses
POS_CORR = {'USB_C_Receptacle_ShouHan_TYPE-C-6P-LTH6.8-108_Vertical': (0.0, -0.93)}   # origin is the pad row; JLC centres the body


def cpl():
    import math, re
    import pcbnew
    b = pcbnew.LoadBoard(BOARD)
    path = os.path.join(OUT, 'CPL.csv')
    placed = {p['ref'] for p in circuit.P if not (p.get('dnp') or p.get('hand') or p.get('nobom'))}
    rows = []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref not in placed:
            continue
        name = str(fp.GetFPID().GetLibItemName())
        rot = fp.GetOrientationDegrees()
        rot = (rot + sum(d for pat, d in ROT_CORR if re.search(pat, name))) % 360
        c = fp.GetPosition(); x, y = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
        ox, oy = POS_CORR.get(name, (0.0, 0.0))
        a = math.radians(fp.GetOrientationDegrees())      # KiCad: CCW on screen, y down
        x += ox * math.cos(a) + oy * math.sin(a)
        y += -ox * math.sin(a) + oy * math.cos(a)
        rows.append((ref, f'{x:.4f}mm', f'{-y:.4f}mm', 'Bottom' if fp.IsFlipped() else 'Top', f'{rot:.0f}'))
    rows.sort(key=lambda r: (r[0].rstrip('0123456789'), int(r[0][len(r[0].rstrip('0123456789')):] or 0)))
    with open(path, 'w', newline='') as o:
        w = csv.writer(o)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        w.writerows(rows)
    return path


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print(gerbers()); print(bom()); print(cpl())
