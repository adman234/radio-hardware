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


def main(passes=40, finish=False):
    os.makedirs(WORK, exist_ok=True)
    dsn, ses = os.path.join(WORK, 'jar-radio.dsn'), os.path.join(WORK, 'jar-radio.ses')
    # export in a child process: pcbnew can't load the same board twice in one
    # process. GND pours are removed first so Freerouting routes every GND pad
    # with real copper instead of assuming the plane reaches it.
    if not finish:
        # pre-place locked GND vias on a grid in the free space, so every
        # patch of pour that the routing leaves behind already has a via
        subprocess.run(['python3', '-c', f"""
import sys; sys.path.insert(0, {HERE!r})
import pcbnew, stitch, fanout
b = pcbnew.LoadBoard({BOARD!r})
print('GND fan-out vias:', fanout.fanout(b))
print('pre-route stitching vias:', stitch.add_stitching(b, pitch=2.5, locked=True))
pcbnew.SaveBoard({BOARD!r}, b)
"""], check=True)
    subprocess.run(['python3', '-c', f"""
import pcbnew
b = pcbnew.LoadBoard({BOARD!r})
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        z.SetIsFilled(False)   # GND stays a plane: Freerouting leaves its pads to the pours
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
    print('imported tracks/vias:', ses_import.import_ses(board, ses, replace=finish))
    if not finish:
        import stitch
        print('stitching vias:', stitch.add_stitching(board))
    # drop vias stacked on the same spot (pre-route grid + stitching can coincide)
    seen = set()
    for t in list(board.GetTracks()):
        if t.GetClass() == 'PCB_VIA':
            k = (t.GetPosition().x, t.GetPosition().y)
            if k in seen:
                board.Remove(t)
            seen.add(k)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    rpt = os.path.join(WORK, 'drc.rpt')
    import zone_stitch
    print('pour-joining vias:', zone_stitch.stitch(board))
    import island_bridge
    print('GND bridges:', island_bridge.bridge(board))
    pcbnew.SaveBoard(BOARD, board)
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    # anything Freerouting left: two-pad connections get the small maze router
    import route_one, island_bridge
    txt = open(rpt).read()
    left = re.findall(r'Pad (\S+) \[[^\]]+\] of (\S+) on \S+\n\s+@\([^)]*\): Pad (\S+) \[[^\]]+\] of (\S+) on', txt)
    for pa, ra, pb, rb in left:
        print(f'maze-routing {ra}.{pa} -> {rb}.{pb}:', route_one.route_net(board, ra, pa, rb, pb))
    # a pad left short of its own net's track: route it onto that net's copper
    # anything else: join every stray piece of the affected nets to the rest of the net
    blocks = re.findall(r'\[unconnected_items\][^\n]*\n[^\n]*\n\s+@\([^)]*\): [^\[]*\[([^\]]+)\]', txt)
    for net in sorted(set(blocks) - {'GND'}):
        n = route_one.join_net(board, net)
        print(f'maze-joining net {net}:', n)
        left = left + [net] * bool(n)
    if left:
        print('GND bridges:', island_bridge.bridge(board))
        pcbnew.SaveBoard(BOARD, board)
        pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    n = prune_dangling(board, rpt)
    if n:
        print('dangling stubs removed:', n)
        pcbnew.SaveBoard(BOARD, board)
    print(summary(rpt))


def prune_dangling(board, rpt=None):
    """Deletes track stubs with a free end (touching no pad, via or other
    track of the same net on that layer), repeating until none are left.
    Pure geometry: re-running DRC between deletions upsets pcbnew's bindings."""
    from shapely.geometry import Point, LineString, box
    removed = 0
    for _ in range(10):
        tracks = [t for t in board.GetTracks() if t.GetClass() != 'PCB_VIA']
        geo = {}
        for t in board.GetTracks():
            k = t.GetNetCode()
            if t.GetClass() == 'PCB_VIA':
                p = t.GetPosition()
                g = Point(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)).buffer(pcbnew.ToMM(t.GetWidth()) / 2)
                geo.setdefault((k, 'F.Cu'), []).append((t, g)); geo.setdefault((k, 'B.Cu'), []).append((t, g))
            else:
                a, e = t.GetStart(), t.GetEnd()
                g = LineString([(pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)), (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))]).buffer(pcbnew.ToMM(t.GetWidth()) / 2)
                geo.setdefault((k, t.GetLayerName()), []).append((t, g))
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                g = box(pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
                for L in ('F.Cu', 'B.Cu'):
                    if pad.IsOnLayer(pcbnew.F_Cu if L == 'F.Cu' else pcbnew.B_Cu):
                        geo.setdefault((pad.GetNetCode(), L), []).append((pad, g))
        dead = []
        for t in tracks:
            a, e = t.GetStart(), t.GetEnd()
            others = [g for o, g in geo.get((t.GetNetCode(), t.GetLayerName()), []) if o is not t]
            for q in (a, e):
                pt = Point(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
                if not any(g.distance(pt) < 1e-3 for g in others):
                    dead.append(t)
                    break
        if not dead:
            break
        for t in dead:
            board.Remove(t); removed += 1
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    return removed


def summary(rpt):
    t = open(rpt).read()
    out = []
    for key in ('DRC violations', 'unconnected pads', 'Footprint errors'):
        m = re.search(r'\*\* Found (\d+) ' + key, t)
        if m:
            out.append(f'{key}: {m.group(1)}')
    return ', '.join(out)


if __name__ == '__main__':
    import sys
    main(passes=int(os.environ.get('ROUTE_PASSES', 40)), finish='--finish' in sys.argv)
