"""Local JLCPCB parts database: fetch it, check the BOM against it, search it.

    python3 jlcdb.py fetch                  # download the jlcparts database (~1.5 GB)
    python3 jlcdb.py check --qty 5 100      # stock / price / fee report for circuit.py
    python3 jlcdb.py search "50k switch" --sub Potentiometer

The data is yaqwsx/jlcparts (the same database behind yaqwsx.github.io/jlcparts),
refreshed daily by its maintainer. It is fetched from the repo's gh-pages
branch with git, so only github.com needs to be reachable.
"""
import argparse, csv, json, os, re, sqlite3, struct, subprocess, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('JLCDB', os.path.expanduser('~/.cache/jlcdb/cache.sqlite3'))
REPO = 'https://github.com/yaqwsx/jlcparts'
EXT_FEE = 3.00        # JLC Economic PCBA loading fee per unique Extended part
COLS = ('lcsc, mfr, manufacturer, category, subcategory, package, library_type, preferred, '
        'stock, price, attributes, description, assembly_process, joints')


# ---- fetch -------------------------------------------------------------------
def fetch():
    work = os.path.dirname(DB)
    pages = os.path.join(work, 'jlcparts-pages')
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1')
    if not os.path.isdir(os.path.join(pages, '.git')):
        subprocess.check_call(['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse',
                               '-b', 'gh-pages', REPO, pages], env=env)
    else:
        subprocess.check_call(['git', '-C', pages, 'pull', '-q', '--depth', '1'], env=env)
    subprocess.check_call(['git', '-C', pages, 'sparse-checkout', 'set', '--no-cone', 'data/cache.*'], env=env)
    data = os.path.join(pages, 'data')
    parts = sorted(f for f in os.listdir(data) if re.fullmatch(r'cache\.z\d\d', f)) + ['cache.zip']
    # The archive is a split zip holding one deflated file; stream the raw deflate
    # data across the pieces instead of rejoining them (zip -s 0 mangles it).
    def chunks():
        for f in parts:
            with open(os.path.join(data, f), 'rb') as fh:
                while True:
                    b = fh.read(1 << 20)
                    if not b:
                        break
                    yield b
    g = chunks()
    buf = next(g)
    off = 4 if buf[:4] == b'PK\x07\x08' else 0
    sig, _, _, meth, _, _, _, _, _, nl, el = struct.unpack('<IHHHHHIIIHH', buf[off:off + 30])
    assert sig == 0x04034b50 and meth == 8, 'unexpected archive layout'
    buf = buf[off + 30 + nl + el:]
    dec = zlib.decompressobj(-15)
    tmp = DB + '.part'
    with open(tmp, 'wb') as out:
        while True:
            out.write(dec.decompress(buf))
            if dec.eof:
                break
            buf = next(g)
    os.replace(tmp, DB)
    print('database:', DB, f'{os.path.getsize(DB) / 1e9:.2f} GB')


# ---- helpers -----------------------------------------------------------------
def db():
    if not os.path.exists(DB):
        sys.exit(f'no database at {DB}: run "python3 jlcdb.py fetch" first')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def lib(r):
    if r is None:
        return 'not at JLC'
    if r['library_type'] == 'base':
        return 'Basic'
    return 'Preferred' if r['preferred'] else 'Extended'


def fee(r):
    return EXT_FEE if lib(r) == 'Extended' else 0.0


def unit_price(r, n):
    """Price per piece when buying n pieces (JLC price tiers 'a-b:p,...')."""
    best = None
    for tier in r['price'].split(','):
        rng, p = tier.split(':')
        lo = int(rng.split('-')[0])
        if n >= lo or best is None:
            best = float(p)
    return best


def attrs(r):
    try:
        return json.loads(r['attributes'])
    except Exception:
        return {}


def num(s):
    """'2.4kΩ' -> 2400.0, '100nF' -> 1e-7, '25V' -> 25, '±1%' -> 1."""
    m = re.match(r'[±]?\s*([\d.]+)\s*([pnuµmkKMG]?)', s or '')
    if not m:
        return None
    mult = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9, '': 1}
    return float(m.group(1)) * mult[m.group(2)]


def lcsc_int(code):
    return int(code[1:]) if code and code.startswith('C') else None


def get(c, code):
    n = lcsc_int(code)
    return c.execute(f'select {COLS} from jlc_components where lcsc=?', (n,)).fetchone() if n else None


# ---- alternatives ------------------------------------------------------------
VALUE_KEY = {'Resistors': 'Resistance', 'Capacitors': 'Capacitance', 'Inductors, Coils, Chokes': 'Inductance'}


def alternatives(c, r, need, limit=3):
    """Cheaper-to-load parts that should drop in: same subcategory and package,
    Basic or Preferred, enough stock, and for R/C/L the same value with equal or
    better voltage and tolerance. Anything else is listed for a human to judge."""
    if r is None or lib(r) != 'Extended':
        return []
    a = attrs(r)
    rows = c.execute(f'select {COLS} from jlc_components where present=1 and subcategory=? and package=? '
                     f"and (library_type='base' or preferred=1) and stock>=? and lcsc!=? order by library_type, stock desc",
                     (r['subcategory'], r['package'], need, r['lcsc'])).fetchall()
    key = VALUE_KEY.get(r['category'])
    out = []
    for q in rows:
        b = attrs(q)
        if key:
            if num(b.get(key)) != num(a.get(key)):
                continue
            if num(b.get('Voltage Rating') or '0') < (num(a.get('Voltage Rating') or '0') or 0):
                continue
            if a.get('Tolerance') and b.get('Tolerance') and num(b['Tolerance']) > num(a['Tolerance']):
                continue
            if a.get('Temperature Coefficient', '').startswith('C0G') and not b.get('Temperature Coefficient', '').startswith(('C0G', 'NP0')):
                continue
        out.append((q, 'drop-in' if key else 'review'))
        if len(out) >= limit:
            break
    return out


# ---- fallback: JLC's own BOM-tool export ---------------------------------------
def jlc_export(paths):
    """{LCSC: (lib type, unit price)} from JLC BOM-tool 'BOM Matching' .xlsx exports.
    The jlcparts mirror misses some parts JLC does stock (e.g. the Si4825), so
    those fall back to what JLC itself quoted."""
    import glob, warnings
    out = {}
    try:
        import openpyxl
    except ImportError:
        return out
    for path in sorted(p for pat in paths for p in glob.glob(pat)):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            ws = openpyxl.load_workbook(path).active
        for row in ws.iter_rows(values_only=True):
            if len(row) > 16 and isinstance(row[11], str) and row[11].startswith('C') and row[14]:
                out[row[11]] = (row[13], float(row[16]) / float(row[14]))
    return out


# ---- check -------------------------------------------------------------------
def bom_lines():
    sys.path.insert(0, HERE)
    import circuit
    lines = {}
    for p in circuit.P:
        if p.get('dnp') or p.get('nobom') or not p['lcsc']:
            if not (p.get('nobom') or p.get('dnp')):
                lines.setdefault(('', p['mpn'] or p['value']), []).append(p['ref'])
            continue
        lines.setdefault((p['lcsc'], p['mpn']), []).append(p['ref'])
    return lines


def check(qtys, out_csv=None, exports=()):
    c = db()
    fb = jlc_export(exports)
    rows = []
    for (code, mpn), refs in sorted(bom_lines().items(), key=lambda kv: kv[1][0]):
        r = get(c, code)
        rows.append(dict(code=code, mpn=mpn, refs=refs, r=r))
    print(f'database: {DB}')
    hdr = f'{"LCSC":<11}{"MPN":<30}{"refs":<20}{"type":<11}{"stock":>9}  ' + ''.join(f'{"@" + str(q):>9}' for q in qtys) + '  notes'
    print(hdr)
    print('-' * len(hdr))
    totals = {q: 0.0 for q in qtys}
    fees = 0.0
    report = []
    for x in rows:
        r, n = x['r'], len(x['refs'])
        notes = []
        prices = {}
        if r is None and x['code'] in fb:
            kind, each = fb[x['code']]
            notes.append(f'not in jlcparts mirror; JLC BOM tool: {kind}, ${each:.3f} each (stock unknown)')
            for q in qtys:
                prices[q] = each * n
                totals[q] += prices[q]
            if kind == 'Extended':
                fees += EXT_FEE
                x['ext'] = True
        elif r is None:
            notes.append('NOT IN JLC LIBRARY' if x['code'] else 'no LCSC number')
        else:
            for q in qtys:
                need = q * n
                prices[q] = unit_price(r, need) * n
                totals[q] += prices[q]
                if r['stock'] < need:
                    notes.append(f'short for {q} ({r["stock"]} < {need})')
            fees += fee(r)
            if r['assembly_process'] == 'THT':
                notes.append('THT assembly')
            for q, kind in alternatives(c, r, max(qtys) * n):
                notes.append(f'{kind}: C{q["lcsc"]} {q["mfr"]} [{lib(q)}, {q["stock"]}]')
        refs = ','.join(x['refs'])
        kind = lib(r) if r is not None or x['code'] not in fb else fb[x['code']][0] + '*'
        print(f'{x["code"]:<11}{(x["mpn"] or "")[:29]:<30}{refs[:19]:<20}{kind:<11}{(r["stock"] if r else 0):>9}  '
              + ''.join(f'{prices.get(q, 0):>9.3f}' for q in qtys) + '  ' + '; '.join(notes))
        report.append({'lcsc': x['code'], 'mpn': x['mpn'], 'refs': refs, 'qty_per_board': n, 'type': kind,
                       'stock': r['stock'] if r else 0,
                       **{f'cost_per_board_at_{q}': round(prices.get(q, 0), 4) for q in qtys},
                       'notes': '; '.join(notes)})
    print('-' * len(hdr))
    n_ext = sum(1 for x in rows if lib(x['r']) == 'Extended' or x.get('ext'))
    print(f'Extended parts: {n_ext} -> ${fees:.2f} loading fee per order')
    for q in qtys:
        print(f'{q:>5} boards: parts ${totals[q]:.2f}/board, +fees ${fees / q:.2f}/board = ${totals[q] + fees / q:.2f}/board')
    if out_csv:
        with open(out_csv, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(report[0]))
            w.writeheader()
            w.writerows(report)
        print('wrote', out_csv)
    return report


# ---- search ------------------------------------------------------------------
def search(words, sub=None, pkg=None, basic=False, limit=25):
    c = db()
    q = f'select {COLS} from jlc_components where present=1 and stock>0'
    args = []
    for w in words.split():
        q += ' and (description like ? or mfr like ? or attributes like ?)'
        args += [f'%{w}%'] * 3
    if sub:
        q += ' and subcategory like ?'
        args.append(f'%{sub}%')
    if pkg:
        q += ' and package like ?'
        args.append(f'%{pkg}%')
    if basic:
        q += " and (library_type='base' or preferred=1)"
    q += ' order by library_type, preferred desc, stock desc limit ?'
    args.append(limit)
    for r in c.execute(q, args):
        print(f'C{r["lcsc"]:<10}{r["mfr"][:28]:<29}{r["package"][:14]:<15}{lib(r):<10}{r["stock"]:>9}  '
              f'${unit_price(r, 1):<8.4f}{r["description"][:70]}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('fetch')
    a = sp.add_parser('check')
    a.add_argument('--qty', type=int, nargs='+', default=[5, 100])
    a.add_argument('--csv')
    a.add_argument('--jlc-export', nargs='*', default=[os.path.join(HERE, '..', '..', 'docs', 'jlc-bom-match-*.xlsx')],
                   help='JLC BOM-tool exports used for parts missing from the mirror')
    a = sp.add_parser('search')
    a.add_argument('words')
    a.add_argument('--sub')
    a.add_argument('--pkg')
    a.add_argument('--basic', action='store_true')
    a.add_argument('--limit', type=int, default=25)
    o = ap.parse_args()
    if o.cmd == 'fetch':
        fetch()
    elif o.cmd == 'check':
        check(o.qty, o.csv, o.jlc_export)
    else:
        search(o.words, o.sub, o.pkg, o.basic, o.limit)
