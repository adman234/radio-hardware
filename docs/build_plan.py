"""Builds docs/jar-radio-plan.html (the published plan artifact) from the
BOM spreadsheet, the cost model, the DRC summary and the board renders."""
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
    rows = list(csv.DictReader(open(os.path.join(HERE, 'bom-plan.csv'))))
    groups = [('Placed by JLCPCB (inside face, single-sided assembly)', 'JLC'),
              ('You solder (top face / leads)', 'Hand'), ('Footprint only', 'Not placed'), ('Kit and assembly items', None)]
    out = ['<div class="tbl"><table><thead><tr><th>Refs</th><th>Part</th><th>MPN</th><th>LCSC</th><th>Class</th>'
           '<th>Qty</th><th>$ @10</th><th>$ @100</th><th>Status</th></tr></thead><tbody>']
    used = set()
    for title, who in groups:
        sel = [r for r in rows if (r['Who'] == who if who else r['Who'] not in ('JLC', 'Hand', 'Not placed'))]
        if not sel:
            continue
        out.append(f'<tr class="grp"><td colspan="9">{esc(title)}</td></tr>')
        for r in sel:
            need = 'need' in r['Status'] or 'PROVISIONAL' in r['Status']
            lc = esc(r['LCSC']) if r['LCSC'] else ('<span class="tag p">need C#</span>' if 'C-number' in r['Status'] else '—')
            cls = r['JLC class (guess)']
            tag = 'b' if cls.startswith('Basic') else 'e' if 'Extended' in cls else 'h'
            st = f'<span class="tag p">{esc(r["Status"])}</span>' if need else esc(r['Status'])
            src = ' <small>(quote)</small>' if 'quote' in r['Price source'] else ''
            out.append(f'<tr><td class="mono">{esc(r["Refs"])}</td><td>{esc(r["Value / description"])}</td><td class="mono">{esc(r["MPN"])}</td>'
                       f'<td class="mono">{lc}</td><td><span class="tag {tag}">{esc(cls)}</span></td><td class="num">{esc(r["Qty per radio"])}</td>'
                       f'<td class="num">{float(r["Unit $ @10"] or 0):.3f}{src}</td><td class="num">{float(r["Unit $ @100"] or 0):.3f}</td><td>{st}</td></tr>')
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
    rep = {
        '{{BOM}}': bom_table(), '{{COST}}': cost_table(),
        '{{IMG_TOP}}': uri('board-top.png'), '{{IMG_BOT}}': uri('board-bottom.png'), '{{IMG_SCH}}': uri('schematic.png'),
        '{{IMG_CU}}': uri('board-copper.png'),
        '{{DRC}}': esc(d.get('text', 'not run')),
        '{{TOPSIDE}}': open(os.path.join(HERE, 'lipo-top-plan.html')).read() if os.path.exists(os.path.join(HERE, 'lipo-top-plan.html')) else '',
    }
    for k, v in rep.items():
        t = t.replace(k, v)
    open(os.path.join(HERE, 'jar-radio-plan.html'), 'w').write(t)
    print('plan written', len(t) // 1024, 'KB')


if __name__ == '__main__':
    main()
