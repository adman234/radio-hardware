"""Builds docs/bom-plan.csv (the master parts spreadsheet) from the circuit
definition plus the price/sourcing table below. Prices: the user's LCSC quotes
where given, otherwise estimates (flagged 'est')."""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kicad', 'scripts'))
import circuit

# MPN: (LCSC override or '', JLC class guess, $@10, $@100, price source, status)
PRICE = {
    'SI4825-A10-CSR': ('', 'Extended', 1.4369, 1.1052, 'LCSC quote', 'ok'),
    'Q13FC13500004': ('', 'Basic', 0.10, 0.10, 'est', 'ok'),
    'RT0603BRD0786K6L': ('', 'Extended', 0.0396, 0.0337, 'LCSC quote (min 20)', 'value final after calibration'),
    'TNPW060311K7BEEA': ('', 'Extended', 0.0927, 0.0744, 'LCSC quote', 'value final after calibration'),
    '0603WAF1000T5E': ('', 'Basic', 0.001, 0.001, 'est', 'need C-number'),
    'CL21A476MQYNNNE': ('', 'Extended?', 0.1025, 0.0803, 'LCSC quote', 'ok'),
    '0603WAF4303T5E': ('', 'Basic?', 0.001, 0.001, 'est', 'ok'),
    '0603WAF6802T5E': ('', 'Basic?', 0.001, 0.001, 'est', 'ok'),
    'CL10C102JB8NNNC': ('', 'Basic?', 0.002, 0.001, 'est', 'ok'),
    'CL10A105KB8NNNC': ('', 'Basic', 0.003, 0.002, 'est', 'ok'),
    'CL10A475KO8NNNC': ('', 'Basic?', 0.004, 0.003, 'est', 'need C-number'),
    '0603WAF1003T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    'CC0603KRX7R9BB104': ('', 'Basic', 0.002, 0.001, 'est', 'ok'),
    'XC61CN2702MR': ('', 'Extended', 0.10, 0.06, 'est', 'need C-number; confirm SOT-23 pinout'),
    'CL10A224KB8NNNC': ('', 'Basic?', 0.002, 0.001, 'est', 'ok'),
    '0603WAF2202T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    '0603WAF2203T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    'NS8002': ('', 'Extended', 0.045, 0.03, 'est', 'ok; SD jumper both ways'),
    '0603WAF0000T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    'CL10A106KP8NNNC': ('', 'Basic', 0.005, 0.004, 'est', 'ok'),
    '0603WAF5101T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    'TP4056-42-ESOP8': ('', 'Extended', 0.17, 0.087, 'est', 'ok'),
    '0603WAF3001T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    '24-21SURC/S530-A3/TR8': ('', 'Extended', 0.0471, 0.0377, 'LCSC quote', 'ok'),
    '25-21/GHC-YSU/2A': ('', 'Extended', 0.0673, 0.0673, 'LCSC quote', 'ok'),
    '0603WAF6800T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    '0603WAF2201T5E': ('', 'Basic', 0.001, 0.001, 'est', 'ok'),
    'B2B-PH-SM4-TB(LF)(SN)': ('', 'Extended', 0.15, 0.11, 'est', 'need C-number (vertical SMD PH)'),
    'AO3401A': ('', 'Basic', 0.04, 0.03, 'est', 'ok'),
    'B5819W SL': ('', 'Basic', 0.02, 0.015, 'est', 'ok'),
    'XC6206P332MR': ('', 'Basic', 0.075, 0.059, 'est', 'ok'),
    'GT-A2501WRS-102SBT01': ('', 'Extended', 0.10, 0.08, 'est', 'ok'),
    'PESD5V0F1BL (TBD)': ('', 'Extended', 0.05, 0.03, 'est', 'need part: ESD <=1 pF, SOD-882'),
    'LQW18AN56NJ00D': ('', 'Extended', 0.10, 0.06, 'est', 'need C-number'),
    'CL10C220JB8NNNC': ('', 'Basic', 0.002, 0.001, 'est', 'ok'),
    '3296W-1-104': ('', 'Not placed', 0, 0, '', 'calibration only'),
    'RV097NS B50K': ('', 'Hand', 1.15, 1.15, 'eBay 20 pc kit $23 shipped', 'footprint PROVISIONAL: measure'),
    'GSPK4935PN-8R2W-L270': ('C530575', 'Hand', 0.7877, 0.7877, 'LCSC quote', 'ok; cut plug, solder leads'),
    'TYPE-C 6PLTH6.8-DJ': ('', 'Hand (top)', 0.05, 0.047, 'est', 'ok'),
}
EXTRA = [  # hand / kit / assembly items not on the board
    ('BT1', 'LiPo 1S protected, 500 mAh, PH2.0 lead', 'eBay 100 pc lot', '', 'Plug-in', 1, 2.83, 2.83, 'eBay quote $283/100', 'need dims + polarity'),
    ('ANT', '75 cm 26 AWG wire on XH 2.54 2-pin plug (1 wire used)', 'custom lead', '', 'Kit', 1, 0.30, 0.20, 'est', ''),
    ('WHIP', 'Telescopic whip, M3 male, 7-section ~75 cm (optional)', 'generic', '', 'Kit (optional)', 0, 2.00, 1.20, 'est', 'optional'),
    ('TIES', 'Zip ties 2.5 x 200 mm', 'generic', '', 'Assembly', 2, 0.02, 0.01, 'est', ''),
    ('PAD', 'Kapton / 1 mm foam between speaker back and battery', 'generic', '', 'Assembly', 1, 0.03, 0.02, 'est', ''),
    ('JAR', 'Wide-mouth 8 oz jar + band', 'Ball/Kerr', '', 'Buy locally', 1, 0.90, 0.90, 'local quote', 'measure'),
]


def main():
    rows = []
    groups = {}
    for p in circuit.P:
        if p.get('nobom') and p['ref'] != 'ANT1':
            continue
        key = (p['value'], p['footprint'], p['mpn'])
        groups.setdefault(key, []).append(p)
    for (value, fp, mpn), ps in groups.items():
        pr = PRICE.get(mpn, ('', '?', 0, 0, '', 'unknown'))
        lcsc = ps[0]['lcsc'] or pr[0]
        who = 'Not placed' if ps[0].get('dnp') else ('Hand' if ps[0].get('hand') else 'JLC')
        if ps[0]['ref'] == 'ANT1':
            continue
        refs = ','.join(p['ref'] for p in ps)
        status = pr[5] if lcsc or 'need' in pr[5] else ('need C-number' if who == 'JLC' else pr[5])
        rows.append([refs, value, mpn, lcsc, pr[1] if who != 'Not placed' else 'Not placed', len(ps) if who != 'Not placed' else 0,
                     pr[2], pr[3], who, fp.split(':')[1], pr[4], status])
    rows.sort(key=lambda r: ({'JLC': 0, 'Hand': 1, 'Not placed': 2}.get(r[8], 3), r[0]))
    for e in EXTRA:
        rows.append([e[0], e[1], e[2], e[3], '—', e[5], e[6], e[7], e[4], '', e[8], e[9]])
    path = os.path.join(HERE, 'bom-plan.csv')
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Refs', 'Value / description', 'MPN', 'LCSC', 'JLC class (guess)', 'Qty per radio',
                    'Unit $ @10', 'Unit $ @100', 'Who', 'Footprint', 'Price source', 'Status'])
        w.writerows(rows)
    jlc10 = sum(r[5] * r[6] for r in rows if r[8] == 'JLC')
    jlc100 = sum(r[5] * r[7] for r in rows if r[8] == 'JLC')
    ext = sorted({r[2] for r in rows if r[8] == 'JLC' and 'Extended' in r[4]})
    print(f'{len(rows)} lines; JLC parts/radio ${jlc10:.2f} @10, ${jlc100:.2f} @100; {len(ext)} unique Extended')
    return rows


if __name__ == '__main__':
    main()
