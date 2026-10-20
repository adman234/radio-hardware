"""Regenerates the whole design: schematic -> board (placed) -> optional route.

    python3 build.py            # schematic + placed, unrouted board
    python3 build.py --route    # also autoroute with Freerouting, refill, DRC
"""
import os, sys, subprocess
import gen_schematic, gen_pcb

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))


def project_files():
    open(os.path.join(PROJ, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n  (lib (name "jar-radio")(type "KiCad")(uri "${KIPRJMOD}/lib/jar-radio.pretty")(options "")(descr "Jar radio project footprints"))\n)\n')
    open(os.path.join(PROJ, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n  (lib (name "jar-radio")(type "KiCad")(uri "${KIPRJMOD}/lib/jar-radio.kicad_sym")(options "")(descr "Jar radio project symbols"))\n)\n')
    open(os.path.join(PROJ, 'jar-radio.kicad_dru'), 'w').write(
        '(version 1)\n(rule "single spoke ok" (constraint min_resolved_spokes 1))\n')
    pro = os.path.join(PROJ, 'jar-radio.kicad_pro')
    if True:
        open(pro, 'w').write('{\n  "meta": {"filename": "jar-radio.kicad_pro", "version": 1},\n  "board": {"design_settings": {"rule_severities": {"lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore", "silk_over_copper": "warning", "silk_overlap": "warning", "text_height": "ignore"}}},\n  "schematic": {},\n  "net_settings": {"classes": [\n'
                             '    {"name": "Default", "track_width": 0.25, "clearance": 0.2, "via_diameter": 0.6, "via_drill": 0.3},\n'
                             '    {"name": "Power", "track_width": 0.5, "clearance": 0.2, "via_diameter": 0.8, "via_drill": 0.4}],\n'
                             '    "netclass_patterns": [' + ', '.join('{"netclass": "Power", "pattern": "%s"}' % n for n in sorted(gen_pcb.POWER_NETS)) + ']},\n'
                             '  "pcbnew": {}, "libraries": {}\n}\n')


if __name__ == '__main__':
    project_files()
    s = gen_schematic.main()
    gen_pcb.build(s.parts, os.path.join(PROJ, 'jar-radio.kicad_pcb'))
    print('board written')
    if '--route' in sys.argv:
        import route
        route.main()
