"""Builds docs/jar-radio-plan.html (the published plan artifact) from the
JLC BOM check (docs/bom-check.csv), the DRC summary and the board renders."""
import base64, csv, html, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, 'img')


def uri(name):
    p = os.path.join(IMG, name)
    if not os.path.exists(p):
        return ''
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()


def esc(s):
    return html.escape(str(s))


def bom_table():
    """JLC-placed parts from docs/bom-check.csv (written by kicad/scripts/jlcdb.py check)."""
    import sys
    sys.path.insert(0, os.path.join(HERE, '..', 'kicad', 'scripts'))
    import circuit
    val = {p['ref']: p['value'] for p in circuit.P}
    rows = list(csv.DictReader(open(os.path.join(HERE, 'bom-check.csv'))))
    qcols = [k for k in rows[0] if k.startswith('cost_per_board_at_')]
    head = ''.join(f'<th class="num">$/board @{k.rsplit("_", 1)[1]}</th>' for k in qcols)
    out = ['<div class="tbl"><table><thead><tr><th>Refs</th><th>Value</th><th>MPN</th><th>LCSC</th><th>Type</th>'
           f'<th class="num">Stock</th>{head}</tr></thead><tbody>']
    for r in rows:
        t = r['type'].rstrip('*')
        tag = 'b' if t == 'Basic' else 'h' if t == 'Preferred' else 'e'
        refs = r['refs']; v = val.get(refs.split(',')[0], '')
        stock = r['stock'] if r['stock'] != '0' else '(not in mirror)'
        cells = ''.join(f'<td class="num">{float(r[k]):.3f}</td>' for k in qcols)
        out.append(f'<tr><td class="mono">{esc(refs)}</td><td>{esc(v)}</td><td class="mono">{esc(r["mpn"])}</td><td class="mono">{esc(r["lcsc"])}</td>'
                   f'<td><span class="tag {tag}">{esc(t)}</span></td><td class="num">{esc(stock)}</td>{cells}</tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)


def cost_table():
    rows = json.load(open(os.path.join(HERE, 'cost_model.json')))
    out = ['<div class="tbl"><table><thead><tr><th>Radios</th><th>JLC parts</th><th>JLC setup + fees + joints</th><th>PCB</th>'
           '<th>Shipping</th><th>Import duty (25% placeholder)</th><th>Hand parts + jar + battery</th><th>Per radio</th><th>Without battery</th><th>Order total</th></tr></thead><tbody>']
    for r in rows:
        out.append(f'<tr><td class="num"><b>{r["qty"]}</b></td><td class="num">${r["parts"]:.2f}</td><td class="num">${r["assembly"]:.2f}</td>'
                   f'<td class="num">${r["pcb"]:.2f}</td><td class="num">${r["shipping"]:.2f}</td><td class="num">${r["duty"]:.2f}</td>'
                   f'<td class="num">${r["hand"]:.2f}</td><td class="num"><b>${r["total"]:.2f}</b></td><td class="num">${r["total_no_batt"]:.2f}</td>'
                   f'<td class="num">${r["total"] * r["qty"]:,.0f}</td></tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)


def drc():
    p = os.path.join(HERE, '..', 'kicad', 'build', 'drc-summary.json')
    return json.load(open(p)) if os.path.exists(p) else {}


def main():
    t = open(os.path.join(HERE, 'plan_template.html')).read()
    d = drc()
    top = os.path.join(HERE, 'lipo-top-plan.html')
    t = t.replace('{{TOPSIDE}}', open(top).read() if os.path.exists(top) else '')
    rep = {
        '{{BOM}}': bom_table(),
        '{{IMG_TOP}}': uri('board-top.png'), '{{IMG_BOT}}': uri('board-bottom.png'), '{{IMG_SCH}}': uri('schematic.png'),
        '{{IMG_CU}}': uri('board-copper.png'),
        '{{DRC}}': esc(d.get('text', 'not run')),
    }
    for k, v in rep.items():
        t = t.replace(k, v)
    open(os.path.join(HERE, 'jar-radio-plan.html'), 'w').write(t)
    print('plan written', len(t) // 1024, 'KB')


if __name__ == '__main__':
    main()
