import json
import xml.etree.ElementTree as ET
from pathlib import Path
import design as d
from design import n,xy,uid,q,effects
out=d.out
here=Path(__file__).parent
tree=ET.parse(here/'net.xml')
numbers={(node.get('ref'),int(node.get('pin'))):net.get('name') for net in tree.findall('.//nets/net') for node in net.findall('node')}
for name in numbers.values():
    if name not in d.netid:d.netid[name]=max(d.netid.values())+1
board=['(kicad_pcb (version 20240108) (generator "pcbnew") (general (thickness 1.6)) (paper "A4")']
board.append('(title_block (title "Bedroom Air | Sensor carrier") (date "2026-11-26") (rev "A"))')
board.append('(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user) (48 "B.Fab" user) (49 "F.Fab" user)) (setup (pad_to_mask_clearance 0)) (net 0 "")')
for name,i in d.netid.items():board.append(f'(net {i} {q(name)})')
for p in d.parts:board.append(d.fp(p,True,numbers))
def mounting(ref,at,board):
    suffix='BedroomAir:' if board else ''
    a=f'(footprint "{suffix}Mounting_M3" '
    if not board:a+='(version 20240108) (generator "pcbnew") '
    a+='(layer "F.Cu") '
    if board:a+=f'(at {xy(*at)}) (uuid {uid(ref)}) '
    a+=f'(property "Reference" "{ref if board else "REF**"}" (at 0 0) (layer "F.Fab") (hide yes) {effects(1,.15)}) '
    a+=f'(property "Value" "Mounting_M3" (at 0 0) (layer "F.Fab") (hide yes) {effects(1,.15)}) '
    a+='(attr board_only exclude_from_pos_files exclude_from_bom) (fp_circle (center 0 0) (end 3.25 0) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd")) (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask")))'
    return a
(d.lib/'Mounting_M3.kicad_mod').write_text(mounting('',(0,0),False)+'\n')
for j,at in enumerate(d.holes,1):board.append(mounting('H'+str(j),at,True))
board.append(f'(gr_rect (start 0 0) (end 92 70) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts") (uuid {uid("edge")}))')
def silk(s,x,y,h=1.05,th=.17,layer='F.SilkS'):
    board.append(f'(gr_text {q(s)} (at {xy(x,y)}) (layer {q(layer)}) (uuid {uid("silk."+s+str(x)+str(y))}) {effects(h,th)})')
silk('BEDROOM  AIR',24,5.1,2.6,.42);silk('REV A',42.8,5.2,1.15,.2)
silk('ESP32   /   30 PIN',25,21.2,1.65,.25);silk('USB  <',8.6,24.6,1.15,.19)
silk('Fit one lower socket',26,26,1.12);silk('VIN',8,9.4,1.0);silk('G',10.54,9.4,1.0);silk('22.86',49.2,34.86,1);silk('25.40',49.2,37.4,1)
silk('GY-302',74,6.1,1.22,.19);silk('LIGHT',74,24.2,1.05)
for name,y in [('ADDR',9),('SDA',11.54),('SCL',14.08),('GND',16.62),('3V3',19.16)]:silk(name,70,y,.95)
silk('CO2',17,62.4,1.65,.28);silk('5 V  IN',39.5,62.4,1.55,.25);silk('DHT22',67,62.4,1.65,.28)
for x,label in [(9,'5V'),(14,'G'),(19,'TX'),(24,'RX'),(37,'+5V'),(42,'G'),(62,'G'),(67,'OUT'),(72,'3V3')]:silk(label,x,49.8,.98)
silk('C2',6.1,44.2,.96);silk('C1',52.3,48.8,1.0)
silk('JP1 RUN',40,42.9,1.05);silk('R1  10k OPT',69,40.8,1.0)
silk('5V REGULATED   /   REMOVE JP1 FOR USB + EXT POWER',45,66.7,1.22,.2)
for i,r in enumerate(json.loads((here/'routes.json').read_text())):
    for j,(a,b) in enumerate(zip(r['pts'],r['pts'][1:])):
        if a==b:continue
        board.append(f'(segment (start {xy(*a)}) (end {xy(*b)}) (width {n(r["width"])}) (layer "{["F.Cu","B.Cu"][r["layer"]]}") (net {d.netid[r["net"]]}) (uuid {uid("trace."+str(i)+"."+str(j))}))')
board.append(f'(zone (net 0) (net_name "") (layers "F&B.Cu") (uuid {uid("rfkeep")}) (name "ESP antenna clearance") (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed)) (fill (thermal_gap 0.3) (thermal_bridge_width 0.3)) (polygon (pts (xy 45 5) (xy 61 5) (xy 61 43) (xy 45 43))))')
(out/'Bedroom-Air.kicad_pcb').write_text('\n'.join(board)+')\n')
