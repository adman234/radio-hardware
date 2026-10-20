"""Autoroutes jar-radio.kicad_pcb with Freerouting, then refills zones and
writes a DRC report.

Needs Java and freerouting.jar (v1.9). Set FREEROUTING_JAR to its path.
Power nets are given 0.5 mm tracks in the DSN before routing.
"""
import os, re, subprocess
import pcbnew
import gen_pcb

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
BOARD = os.path.join(PROJ, 'jar-radio.kicad_pcb')
JAR = os.environ.get('FREEROUTING_JAR', 'freerouting.jar')
WORK = os.environ.get('ROUTE_WORK', os.path.join(PROJ, 'build'))


def main(passes=40):
    os.makedirs(WORK, exist_ok=True)
    dsn, ses = os.path.join(WORK, 'jar-radio.dsn'), os.path.join(WORK, 'jar-radio.ses')
    # export in a child process: pcbnew can't load the same board twice in one
    # process. GND pours are removed first so Freerouting routes every GND pad
    # with real copper instead of assuming the plane reaches it.
    subprocess.run(['python3', '-c', f"""
import pcbnew
b = pcbnew.LoadBoard({BOARD!r})
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z)
assert pcbnew.ExportSpecctraDSN(b, {dsn!r})
"""], check=True)
    text = open(dsn).read()
    nets = ' '.join(f'"{n}"' if re.search(r'[^A-Za-z0-9_]', n) else n for n in sorted(gen_pcb.POWER_NETS - {'GND'}))
    power = f'    (class Power {nets}\n      (circuit (use_via "Via[0-1]_800:400_um"))\n      (rule (width 500) (clearance 200))\n    )\n'
    # remove power nets from the default class, add a Power class
    for n in gen_pcb.POWER_NETS - {'GND'}:
        q = f'"{n}"' if re.search(r'[^A-Za-z0-9_]', n) else n
        text = re.sub(r'(\(class kicad_default[^()]*?)\s' + re.escape(q) + r'(?=[\s)])', r'\1', text, flags=re.S)
    text = text.replace('    (class kicad_default', power + '    (class kicad_default', 1)
    if 'Via[0-1]_800:400_um' not in text.split('(network')[0]:
        text = text.replace('(via "Via[0-1]_600:300_um")', '(via "Via[0-1]_600:300_um" "Via[0-1]_800:400_um")')
        text = text.replace('    (padstack "Via[0-1]_600:300_um"',
                            '    (padstack "Via[0-1]_800:400_um"\n      (shape (circle F.Cu 800))\n      (shape (circle B.Cu 800))\n      (attach off)\n    )\n    (padstack "Via[0-1]_600:300_um"', 1)
    text = re.sub(r'\(clearance 200(\.1)?\)', '(clearance 220)', text)
    open(dsn, 'w').write(text)
    cmd = ['xvfb-run', '-a', 'java', '-jar', JAR, '-de', dsn, '-do', ses, '-mp', str(passes), '-mt', '1']
    print(' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3000)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if 'INFO' in l and ('unrouted' in l.lower() or 'completed' in l.lower() or 'incomplete' in l.lower())][-8:]
    print('\n'.join(tail))
    if not os.path.exists(ses):
        raise SystemExit('freerouting produced no session file')
    board = pcbnew.LoadBoard(BOARD)
    import ses_import
    print('imported tracks/vias:', ses_import.import_ses(board, ses))
    import stitch
    print('stitching vias:', stitch.add_stitching(board))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(BOARD, board)
    rpt = os.path.join(WORK, 'drc.rpt')
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print(summary(rpt))


def summary(rpt):
    t = open(rpt).read()
    out = []
    for key in ('DRC violations', 'unconnected pads', 'Footprint errors'):
        m = re.search(r'\*\* Found (\d+) ' + key, t)
        if m:
            out.append(f'{key}: {m.group(1)}')
    return ', '.join(out)


if __name__ == '__main__':
    main()
