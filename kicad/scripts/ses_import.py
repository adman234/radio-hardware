"""Imports a Freerouting .ses into a board without the KiCad GUI
(pcbnew.ImportSpecctraSES only works inside the editor in KiCad 7)."""
import re
import pcbnew


def tokenize(t):
    return re.findall(r'\(|\)|"[^"]*"|[^\s()]+', t)


def parse(tokens):
    stack = [[]]
    for tk in tokens:
        if tk == '(':
            stack.append([])
        elif tk == ')':
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(tk.strip('"'))
    return stack[0][0]


def find(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            yield c


def import_ses(board, path, replace=False):
    """replace=True: delete every track/via first and take all of them from
    the session (used when re-routing a board that already had copper)."""
    if replace:
        for t in list(board.GetTracks()):
            board.Remove(t)
    tree = parse(tokenize(open(path).read()))
    routes = next(find(tree, 'routes'))
    res = next(find(routes, 'resolution'))
    scale = {'um': 1e-3, 'mm': 1.0, 'mil': 0.0254}[res[1]] / float(res[2])   # -> mm
    layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
    vias = {}
    lib = next(find(routes, 'library_out'), None)
    if lib:
        for ps in find(lib, 'padstack'):
            m = re.search(r'_(\d+):(\d+)_um', ps[1])
            if m:
                vias[ps[1]] = (int(m.group(1)) / 1000, int(m.group(2)) / 1000)
    n_tr = n_via = 0

    def pt(x, y):
        return pcbnew.VECTOR2I(pcbnew.FromMM(float(x) * scale), pcbnew.FromMM(-float(y) * scale))

    for net in find(next(find(routes, 'network_out')), 'net'):
        ni = board.FindNet(net[1])
        for w in find(net, 'wire'):
            if not replace and any(isinstance(c, list) and c[0] == 'type' and c[1] == 'protect' for c in w):
                continue
            path = next(find(w, 'path'))
            layer, width = path[1], float(path[2]) * scale
            xy = path[3:]
            pts = [pt(xy[i], xy[i + 1]) for i in range(0, len(xy) - 1, 2)]
            for a, b in zip(pts, pts[1:]):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(a); tr.SetEnd(b)
                tr.SetWidth(pcbnew.FromMM(width)); tr.SetLayer(layers[layer]); tr.SetNet(ni)
                board.Add(tr); n_tr += 1
        for v in find(net, 'via'):
            if not replace and any(isinstance(c, list) and c[0] == 'type' and c[1] == 'protect' for c in v):
                continue
            dia, drill = vias.get(v[1], (0.6, 0.3))
            if v[1] not in vias:
                m = re.search(r'_(\d+):(\d+)_um', v[1])
                if m:
                    dia, drill = int(m.group(1)) / 1000, int(m.group(2)) / 1000
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pt(v[2], v[3]))
            via.SetWidth(pcbnew.FromMM(dia)); via.SetDrill(pcbnew.FromMM(drill)); via.SetNet(ni)
            board.Add(via); n_via += 1
    return n_tr, n_via
