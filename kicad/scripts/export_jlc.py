"""Writes the JLCPCB order files into kicad/jlcpcb/:
gerbers + drill zip, BOM.csv and CPL.csv (inside face only), plus PNG
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


def cpl():
    tmp = os.path.join(OUT, 'pos-raw.csv')
    run('kicad-cli', 'pcb', 'export', 'pos', BOARD, '-o', tmp, '--side', 'both', '--format', 'csv', '--units', 'mm',
        )
    path = os.path.join(OUT, 'CPL.csv')
    placed = {p['ref'] for p in circuit.P if not (p.get('dnp') or p.get('hand') or p.get('nobom'))}
    with open(tmp) as f, open(path, 'w', newline='') as o:
        w = csv.writer(o)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in csv.DictReader(f):
            if r['Ref'] not in placed:
                continue
            w.writerow([r['Ref'], r['PosX'] + 'mm', r['PosY'] + 'mm', 'Bottom' if r['Side'] == 'bottom' else 'Top',
                        f"{float(r['Rot']):.0f}"])
    os.remove(tmp)
    return path


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print(gerbers()); print(bom()); print(cpl())
