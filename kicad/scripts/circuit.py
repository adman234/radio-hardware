"""The jar radio circuit: one place that defines every part and net.

gen_schematic.py turns this into the .kicad_sch, gen_pcb.py into the board,
and the BOM/CPL come from the same table, so they cannot drift apart.

Station: KOPN 89.5 MHz. To retune for another station change R_TUNE_H and
R_TUNE_L (see station.py) and the silkscreen text.
"""
from schlib import SymDef

LIB = 'jar-radio'

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
L0603 = 'Inductor_SMD:L_0603_1608Metric'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
JR = 'jar-radio:'

# ---- symbol definitions -------------------------------------------------
SYMS = [
    SymDef('R', 'R', [('1', '~', 'T', 0), ('2', '~', 'B', 0)], two_pin=True),
    SymDef('C', 'C', [('1', '~', 'T', 0), ('2', '~', 'B', 0)], two_pin=True, body='cap'),
    SymDef('L', 'L', [('1', '~', 'T', 0), ('2', '~', 'B', 0)], two_pin=True),
    # diodes/LEDs: pin 1 = cathode (top), pin 2 = anode (bottom)
    SymDef('D', 'D', [('1', 'K', 'T', 0), ('2', 'A', 'B', 0)], two_pin=True, body='diode'),
    SymDef('LED', 'D', [('1', 'K', 'T', 0), ('2', 'A', 'B', 0)], two_pin=True, body='led'),
    SymDef('Si4825-A10', 'U', [
        ('1', 'LNA_EN', 'L', 0), ('2', 'TUNE1', 'L', 1), ('3', 'TUNE2', 'L', 2), ('4', 'BAND', 'L', 3),
        ('5', 'NC', 'L', 4), ('6', 'FMI', 'L', 5), ('7', 'RFGND', 'L', 6), ('8', 'AMI', 'L', 7),
        ('9', 'RST', 'R', 7), ('10', 'VOL+', 'R', 6), ('11', 'VOL-', 'R', 5), ('12', 'XTALO', 'R', 4),
        ('13', 'XTALI', 'R', 3), ('14', 'VDD', 'R', 2), ('15', 'GND', 'R', 1), ('16', 'AOUT', 'R', 0)], width=17.78),
    SymDef('NS8002', 'U', [
        ('1', 'SD', 'L', 0), ('2', 'BYPASS', 'L', 1), ('3', 'IN+', 'L', 2), ('4', 'IN-', 'L', 3),
        ('8', 'VO2', 'R', 0), ('7', 'GND', 'R', 1), ('6', 'VDD', 'R', 2), ('5', 'VO1', 'R', 3),
        ('9', 'EP', 'B', 1)], width=12.7),
    SymDef('TP4056', 'U', [
        ('1', 'TEMP', 'L', 0), ('2', 'PROG', 'L', 1), ('3', 'GND', 'L', 2), ('4', 'VCC', 'L', 3),
        ('8', 'CE', 'R', 0), ('7', 'CHRG', 'R', 1), ('6', 'STDBY', 'R', 2), ('5', 'BAT', 'R', 3),
        ('9', 'EP', 'B', 1)], width=12.7),
    SymDef('XC6206', 'U', [('3', 'VIN', 'L', 0), ('1', 'VSS', 'B', 1), ('2', 'VOUT', 'R', 0)]),
    SymDef('XC61CN', 'U', [('3', 'VIN', 'L', 0), ('2', 'VSS', 'B', 1), ('1', 'VOUT', 'R', 0)]),   # SOT-23 per Torex datasheet
    SymDef('AO3401A', 'Q', [('1', 'G', 'L', 1), ('3', 'D', 'L', 0), ('2', 'S', 'R', 0)]),
    SymDef('Pot_Switch', 'RV', [('3', 'CW', 'L', 0), ('2', 'WIPER', 'L', 1), ('1', 'CCW', 'L', 2),
                                ('S1', 'SW_A', 'R', 0), ('S2', 'SW_B', 'R', 1), ('MP', 'MOUNT', 'R', 2)], width=12.7),
    SymDef('USB_C_Power', 'J', [('2', 'VBUS', 'R', 0), ('5', 'VBUS', 'R', 1), ('3', 'CC1', 'R', 2), ('4', 'CC2', 'R', 3),
                                ('1', 'GND', 'R', 4), ('6', 'GND', 'R', 5), ('S', 'SHIELD', 'R', 6)], width=12.7),
    SymDef('Conn_2_MP', 'J', [('1', '1', 'R', 0), ('2', '2', 'R', 1), ('MP', 'MP', 'R', 2)]),
    SymDef('Conn_2', 'J', [('1', '1', 'R', 0), ('2', '2', 'R', 1)]),
    SymDef('Conn_1', 'J', [('1', '1', 'R', 0)]),
    SymDef('Trim_3', 'RV', [('1', 'TOP', 'R', 0), ('2', 'WIPER', 'R', 1), ('3', 'BOT', 'R', 2)]),
    SymDef('Crystal', 'Y', [('1', '1', 'T', 0), ('2', '2', 'B', 0)], two_pin=True),
]

# ---- parts ----------------------------------------------------------------
# (ref, symbol, value, footprint, LCSC, MPN, {pin: net}, extra)
# extra: dnp=True, hand=True (not assembled by JLC), block='...'
P = []


def part(ref, sym, value, fp, lcsc, mpn, nets, **kw):
    P.append(dict(ref=ref, sym=sym, value=value, footprint=fp, lcsc=lcsc, mpn=mpn, nets=nets, **kw))


# Tuner -------------------------------------------------------------------
B = 'tuner'
part('U1', 'Si4825-A10', 'Si4825-A10', 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm', 'C2654605', 'SI4825-A10-CSR',
     {'2': 'TUNE1', '3': 'TUNE2', '4': 'BAND', '6': 'FMI', '7': 'GND', '8': 'AMI', '9': 'RST',
      '10': 'GND', '11': 'GND', '12': 'XTALO', '13': 'XTALI', '14': '+3V3', '15': 'GND', '16': 'AOUT'},
     block=B, nc=('1', '5'))
part('Y1', 'Crystal', '32.768kHz', 'Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm', 'C32346', 'Q13FC13500004', {'1': 'XTALI', '2': 'XTALO'}, block=B)
part('C1', 'C', '22pF', C0603, 'C1653', 'CL10C220JB8NNNC', {'1': 'XTALI', '2': 'GND'}, block=B)
part('C2', 'C', '22pF', C0603, 'C1653', 'CL10C220JB8NNNC', {'1': 'XTALO', '2': 'GND'}, block=B)
part('C3', 'C', '4.7uF', C0603, 'C19666', 'CL10A475KO8NNNC', {'1': '+3V3', '2': 'GND'}, block=B)
part('C4', 'C', '100nF', C0603, 'C14663', 'CC0603KRX7R9BB104', {'1': '+3V3', '2': 'GND'}, block=B)
part('R1', 'R', '100k', R0603, 'C25803', '0603WAF1003T5E', {'1': '+3V3', '2': 'RST'}, block=B)
part('C5', 'C', '100nF', C0603, 'C14663', 'CC0603KRX7R9BB104', {'1': 'RST', '2': 'GND'}, block=B)
part('U5', 'XC61CN', 'XC61CN2702MR', SOT23, 'C112139', 'XC61CN2702MR-G', {'3': '+3V3', '2': 'GND', '1': 'RST'}, block=B)
# station divider: TUNE1 -> R2 -> TUNE2 -> R3 -> TUNE_LO -> R4 -> GND
part('R2', 'R', '86.6k 0.1%', R0603, 'C861580', 'RT0603BRD0786K6L', {'1': 'TUNE1', '2': 'TUNE2'}, block=B, station=True)
part('R3', 'R', '11.7k 0.1%', R0603, 'C4553285', 'TNPW060311K7BEEA', {'1': 'TUNE2', '2': 'TUNE_LO'}, block=B, station=True)
part('R4', 'R', '100R', R0603, 'C22775', '0603WAF1000T5E', {'1': 'TUNE_LO', '2': 'GND'}, block=B)
part('C6', 'C', '100nF', C0603, 'C14663', 'CC0603KRX7R9BB104', {'1': 'TUNE1', '2': 'GND'}, block=B)
part('C7', 'C', '22uF', C0805, 'C45783', 'CL21A226MAQNNNE', {'1': 'TUNE1', '2': 'GND'}, block=B)
part('C21', 'C', '22uF', C0805, 'C45783', 'CL21A226MAQNNNE', {'1': 'TUNE1', '2': 'GND'}, block=B)   # 2x22u = AN738's 47u
part('RV2', 'Trim_3', '100k CAL (DNP)', 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', '', '3296W-1-104',
     {'1': 'TUNE1', '2': 'TUNE2', '3': 'TUNE_LO'}, block=B, dnp=True, hand=True)
# band ladder 330k + 100k + 68k = 498k (AN738: 500k +/-1%), all Basic parts
part('R5', 'R', '330k', R0603, 'C23137', '0603WAF3303T5E', {'1': 'TUNE1', '2': 'BAND_M'}, block=B)
part('R17', 'R', '100k', R0603, 'C25803', '0603WAF1003T5E', {'1': 'BAND_M', '2': 'BAND'}, block=B)
part('R6', 'R', '68k', R0603, 'C23231', '0603WAF6802T5E', {'1': 'BAND', '2': 'GND'}, block=B)
part('C8', 'C', '1uF', C0603, 'C15849', 'CL10A105KB8NNNC', {'1': 'AMI', '2': 'GND'}, block=B)
# antenna front end (AN738 5.2)
part('J3', 'Conn_1', 'ANT wire', JR + 'Antenna_Wire_Solder_D1.0', '', '', {'1': 'ANT'}, block='ant', nobom=True)   # wire soldered in by hand
part('ANT1', 'Conn_1', 'WHIP M3', JR + 'Antenna_Telescopic_M3', '', '', {'1': 'ANT'}, block='ant', hand=True, nobom=True)
part('D4', 'D', 'ESD <=1pF', 'Diode_SMD:D_SOD-882', 'C5139344', 'PESD5V0F1BL', {'1': 'ANT', '2': 'GND'}, block='ant')
part('C9', 'C', '1nF', C0603, 'C1588', 'CL10B102KB8NNNC', {'1': 'ANT', '2': 'FMI'}, block='ant')   # Basic X7R; C0G C163508 is Extended
part('L1', 'L', '56nH', L0603, 'C98080', 'LQW18AN56NJ00D', {'1': 'FMI', '2': 'GND'}, block='ant')

# Audio -------------------------------------------------------------------
B = 'audio'
part('C10', 'C', '1uF', C0603, 'C15849', 'CL10A105KB8NNNC', {'1': 'AOUT', '2': 'VOL_TOP'}, block=B)
part('RV1', 'Pot_Switch', '20k + SW', JR + 'Potentiometer_RV097NS_Switch_Vertical_PROVISIONAL', 'C470569', 'RK0971111Z0P',
     {'3': 'VOL_TOP', '2': 'VOL_WIPER', '1': 'GND', 'S1': 'VSYS', 'S2': 'VSW', 'MP': 'GND'}, block=B)   # footprint: need Alps drawing
part('C11', 'C', '100nF', C0603, 'C14663', 'CC0603KRX7R9BB104', {'1': 'VOL_WIPER', '2': 'AMP_C'}, block=B)   # 100n x 47k = 34 Hz
part('R7', 'R', '47k', R0603, 'C25819', '0603WAF4702T5E', {'1': 'AMP_C', '2': 'AMP_INN'}, block=B)   # 20k pot || 47k = 14k >= Si4825 10k min load
part('R8', 'R', '470k', R0603, 'C23178', '0603WAF4703T5E', {'1': 'AMP_INN', '2': 'SPK+'}, block=B)   # Av = 2*470/47 = 20, Basic
part('U2', 'NS8002', 'NS8002', 'Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm', 'C189960', 'NS8002',
     {'1': 'AMP_SD', '2': 'AMP_BYP', '3': 'AMP_BYP', '4': 'AMP_INN', '5': 'SPK+', '6': 'VSW', '7': 'GND', '8': 'SPK-', '9': 'GND'}, block=B)
part('C12', 'C', '1uF', C0603, 'C15849', 'CL10A105KB8NNNC', {'1': 'AMP_BYP', '2': 'GND'}, block=B)
part('C13', 'C', '10uF', C0603, 'C19702', 'CL10A106KP8NNNC', {'1': 'VSW', '2': 'GND'}, block=B)
part('C14', 'C', '100nF', C0603, 'C14663', 'CC0603KRX7R9BB104', {'1': 'VSW', '2': 'GND'}, block=B)
part('R9', 'R', '0R', R0603, 'C21189', '0603WAF0000T5E', {'1': 'AMP_SD', '2': 'GND'}, block=B)
part('R10', 'R', '0R (DNP)', R0603, 'C21189', '0603WAF0000T5E', {'1': 'AMP_SD', '2': 'VSW'}, block=B, dnp=True)
part('J4', 'Conn_2', 'SPK wires', JR + 'Speaker_Wire_Pads_P5', '', 'HDK-4008BB-2 (hand-wired)', {'1': 'SPK+', '2': 'SPK-'}, block=B, hand=True, nobom=True)

# Power -------------------------------------------------------------------
B = 'power'
part('J1', 'USB_C_Power', 'USB-C 5V', JR + 'USB_C_Receptacle_ShouHan_TYPE-C-6PLTH6.8-DJ_Vertical', 'C5156600', 'TYPE-C 6PLTH6.8-DJ',
     {'2': 'VBUS', '5': 'VBUS', '3': 'CC1', '4': 'CC2', '1': 'GND', '6': 'GND', 'S': 'GND'}, block=B, top=True)
part('R11', 'R', '5.1k', R0603, 'C23186', '0603WAF5101T5E', {'1': 'CC1', '2': 'GND'}, block=B)
part('R12', 'R', '5.1k', R0603, 'C23186', '0603WAF5101T5E', {'1': 'CC2', '2': 'GND'}, block=B)
part('C15', 'C', '10uF', C0603, 'C19702', 'CL10A106KP8NNNC', {'1': 'VBUS', '2': 'GND'}, block=B)
part('U3', 'TP4056', 'TP4056', 'Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm', 'C16581', 'TP4056-42-ESOP8',
     {'1': 'GND', '2': 'PROG', '3': 'GND', '4': 'VBUS', '5': 'VBAT', '6': 'STDBY', '7': 'CHRG', '8': 'VBUS', '9': 'GND'}, block=B)
part('R13', 'R', '3.0k', R0603, 'C4211', '0603WAF3001T5E', {'1': 'PROG', '2': 'GND'}, block=B)
part('D2', 'LED', 'RED charging', 'LED_SMD:LED_0603_1608Metric', 'C2286', 'KT-0603R',
     {'1': 'CHRG', '2': 'LEDR_A'}, block=B)
part('R14', 'R', '680R', R0603, 'C23228', '0603WAF6800T5E', {'1': 'VBUS', '2': 'LEDR_A'}, block=B)
part('D3', 'LED', 'GREEN full', 'LED_SMD:LED_0603_1608Metric', 'C72043', '19-217/GHC-YR1S2/3T',
     {'1': 'STDBY', '2': 'LEDG_A'}, block=B)
part('R15', 'R', '2.2k', R0603, 'C4190', '0603WAF2201T5E', {'1': 'VBUS', '2': 'LEDG_A'}, block=B)
part('C16', 'C', '10uF', C0603, 'C19702', 'CL10A106KP8NNNC', {'1': 'VBAT', '2': 'GND'}, block=B)
part('J2', 'Conn_2', '18650 holder', JR + 'Battery_Holder_Tab_Slot_Plus_Wire', '', 'BH-18650-B1BA002 (C2988620, hand)', {'1': 'VBAT', '2': 'GND'}, block=B, hand=True, nobom=True)   # tab end = +, wire = - (confirm holder polarity)
part('Q1', 'AO3401A', 'AO3401A', SOT23, 'C15127', 'AO3401A', {'1': 'VBUS', '2': 'VSYS', '3': 'VBAT'}, block=B)
part('R16', 'R', '100k', R0603, 'C25803', '0603WAF1003T5E', {'1': 'VBUS', '2': 'GND'}, block=B)
part('D1', 'D', 'B5819W', 'Diode_SMD:D_SOD-123', 'C8598', 'B5819W SL', {'1': 'VSYS', '2': 'VBUS'}, block=B)
part('C17', 'C', '10uF', C0603, 'C19702', 'CL10A106KP8NNNC', {'1': 'VSYS', '2': 'GND'}, block=B)
part('C18', 'C', '22uF', C0805, 'C45783', 'CL21A226MAQNNNE', {'1': 'VSW', '2': 'GND'}, block=B)
part('U4', 'XC6206', 'XC6206P332MR', SOT23, 'C5446', 'XC6206P332MR', {'3': 'VSW', '1': 'GND', '2': '+3V3'}, block=B)
part('C19', 'C', '1uF', C0603, 'C15849', 'CL10A105KB8NNNC', {'1': 'VSW', '2': 'GND'}, block=B)
part('C20', 'C', '1uF', C0603, 'C15849', 'CL10A105KB8NNNC', {'1': '+3V3', '2': 'GND'}, block=B)

SYM_BY_NAME = {s.name: s for s in SYMS}
