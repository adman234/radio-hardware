"""Rough landed cost per radio at several order quantities.

Inputs are the user's LCSC/eBay quotes where we have them and estimates
elsewhere (marked). JLC fees follow their published Economic PCBA model as of
2025-26: $8 setup + $1.50 stencil per order, $3 per unique Extended part,
~$0.0017 per solder joint. Shipping and US import duties are rough guesses.
Run: python3 cost_model.py  -> prints a table and writes cost_model.json
"""
import json

QTY = [5, 10, 50, 100, 500, 1000]

# JLC-placed parts, $ per radio at (10, 100, 1000) units; qty per radio folded in
JLC_PARTS = {
    'Si4825-A10 (C2654605)': (1.4369, 1.1052, 0.9919),
    'Station resistors 0.1% x2': (0.040 + 0.093, 0.034 + 0.074, 0.029 + 0.055),
    '47 uF 0805 x2 (C16780)': (2 * 0.1025, 2 * 0.0803, 2 * 0.0596),
    'Reverse-mount LEDs x2': (0.047 + 0.067, 0.038 + 0.067, 0.026 + 0.045),
    'NS8002 amp': (0.045, 0.030, 0.023),
    'TP4056 charger': (0.17, 0.087, 0.07),
    'XC61CN reset detector (est.)': (0.10, 0.06, 0.04),
    'Crystal 32.768 kHz': (0.10, 0.10, 0.08),
    'XH antenna socket (C23067528, est.)': (0.10, 0.08, 0.06),
    'USB-C vertical (C5156600), top side': (0.05, 0.047, 0.04),
    'PH speaker socket, vertical (est.)': (0.15, 0.11, 0.08),
    'PH battery socket, vertical (est.)': (0.15, 0.11, 0.08),
    'LDO, P-FET, Schottky, ESD, 56 nH (est.)': (0.25, 0.17, 0.12),
    '~35 resistors and capacitors': (0.10, 0.06, 0.04),
}
EXTENDED_UNIQUE = 14          # unique Extended parts per order ($3 each), from make_bom.py
JOINTS = 200                  # SMD solder joints per board (approx.)

# PCB: 2 layers, 1.6 mm, Ø85.5 mm, black mask, HASL. Order total by qty (est.)
PCB_ORDER = {5: 4, 10: 6, 50: 22, 100: 38, 500: 150, 1000: 270}

HAND = {   # $ per radio
    'Pot + knob (eBay 20 pc, $23 shipped)': 1.15,
    'Speaker GSPK4935 (LCSC C530575)': {5: 0.79, 10: 0.79, 50: 0.79, 100: 0.79, 500: 0.75, 1000: 0.75},
    'LiPo 500 mAh protected (eBay 100 pc, $283)': 2.83,
    'Antenna wire + XH plug (est.)': 0.25,
    'Zip ties, Kapton (est.)': 0.05,
    'Jar + band (local)': 0.90,
}
SHIP = {5: 25, 10: 30, 50: 45, 100: 60, 500: 160, 1000: 260}   # JLC DHL/economy, est.
DUTY = 0.25   # placeholder for US import duty on the JLC order; check current rates


def tier(prices, q):
    return prices[0] if q < 100 else prices[1] if q < 1000 else prices[2]


def model(q):
    parts = sum(tier(v, q) for v in JLC_PARTS.values())
    # two-sided (USB-C on top) needs Standard PCBA: ~$25 setup + 2 stencils (est.)
    assembly = (25 + 2 * 7 + 3 * EXTENDED_UNIQUE) / q + JOINTS * 0.0017
    pcb = PCB_ORDER[q] / q
    jlc = parts + assembly + pcb
    ship = SHIP[q] / q
    duty = DUTY * jlc
    hand = sum(v[q] if isinstance(v, dict) else v for v in HAND.values())
    return dict(qty=q, parts=parts, assembly=assembly, pcb=pcb, shipping=ship, duty=duty, hand=hand,
                total=jlc + ship + duty + hand, total_no_batt=jlc + ship + duty + hand - 2.83)


if __name__ == '__main__':
    rows = [model(q) for q in QTY]
    print(f"{'qty':>5} {'parts':>7} {'assy':>7} {'pcb':>6} {'ship':>6} {'duty':>6} {'hand':>6} {'TOTAL':>7} {'noBatt':>7}")
    for r in rows:
        print(f"{r['qty']:>5} {r['parts']:7.2f} {r['assembly']:7.2f} {r['pcb']:6.2f} {r['shipping']:6.2f} {r['duty']:6.2f} {r['hand']:6.2f} {r['total']:7.2f} {r['total_no_batt']:7.2f}")
    json.dump(rows, open(__file__.replace('.py', '.json'), 'w'), indent=1)
