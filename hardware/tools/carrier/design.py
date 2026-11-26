from dataclasses import dataclass
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS
import json

root=Path(__file__).resolve().parents[2]
out=root/'PCB'
lib=out/'BedroomAir.pretty'
lib.mkdir(exist_ok=True,parents=True)
q=lambda s:json.dumps(str(s),ensure_ascii=False)
def uid(s):return str(uuid5(NAMESPACE_DNS,'bedroom-air-carrier-a/'+s))
def n(v):return f'{v:.4f}'.rstrip('0').rstrip('.') or '0'
def xy(x,y):return n(x)+' '+n(y)
def effects(h=1.27,thick=None,justify=''):
    return f'(effects (font (size {xy(h,h)})'+(f' (thickness {n(thick)})' if thick else '')+')'+(f' (justify {justify})' if justify else '')+')'
netnames=['VIN_ESP','5V_SYS','GND','3V3','CO2_TX','CO2_RX','DHT_DATA','I2C_SDA','I2C_SCL']
top='VIN GND D13 D12 D14 D27 D26 D25 D33 D32 D35 D34 VN VP EN'.split()
low='3V3 GND D15 D2 D4 D16 D17 D5 D18 D19 D21 RX0 TX0 D22 D23'.split()
class Part:
    def __init__(self,ref,kind,value,at,pads,schem):
        self.ref,self.kind,self.value,self.at,self.pads,self.schem=ref,kind,value,at,pads,schem
    @property
    def id(self):return uid('part.'+self.ref)
@dataclass
class Pad:
    num:int
    x:float
    y:float
    label:str
    net:str
    width:float
    drill:float
    square:bool=False
esp=[]
active={1:'VIN_ESP',2:'GND',16:'3V3',17:'GND',21:'CO2_TX',22:'CO2_RX',24:'DHT_DATA',26:'I2C_SDA',29:'I2C_SCL'}
for i,label in enumerate(top+low):
    j=i+1
    for y in ([0] if i<15 else [22.86,25.4]):
        esp.append(Pad(j,round(i%15*2.54,2),y,label,active.get(j,''),1.72,1.0,j in (1,16)))
parts=[Part('U1','ESP32_30_DualWidth','ESP32 WROOM-32 / 30-pin',(8,12),esp,(72.39,99.06))]
def header(ref,kind,v,at,names,nets,pitch,sch,vertical=False,dia=1.75,drill=1):
    pads=[Pad(i+1,0 if vertical else i*pitch,i*pitch if vertical else 0,names[i],net,dia,drill,i==0) for i,net in enumerate(nets)]
    parts.append(Part(ref,kind,v,at,pads,sch))
header('J4','Terminal_4P_5mm','MH-Z19C harness',(9,55),['VIN (4)','GND (3)','TXD (6)','RXD (5)'],['5V_SYS','GND','CO2_TX','CO2_RX'],5,(196.85,57.15),dia=2.9,drill=1.4)
header('J5','Terminal_3P_5mm','DHT22 breakout',(62,55),['GND (-)','OUT','VCC (+)'],['GND','DHT_DATA','3V3'],5,(196.85,88.9),dia=2.9,drill=1.4)
header('J6','GY302_5P','GY-302 BH1750 / optional',(65,9),['ADDR','SDA','SCL','GND','VCC'],['GND','I2C_SDA','I2C_SCL','GND','3V3'],2.54,(196.85,123.19),vertical=True)
header('J7','Terminal_2P_5mm','Regulated DC input',(37,55),['+5 V','GND'],['5V_SYS','GND'],5,(71.12,151.13),dia=2.9,drill=1.4)
header('JP1','Shunt_1x02','RUN shunt',(39,46),['SYS','ESP'],['5V_SYS','VIN_ESP'],2.54,(198.12,151.13))
header('C1','Cap_radial_D6.3_P2.5','100 uF / 10 V or higher',(51,54),['+','-'],['5V_SYS','GND'],2.5,(125.73,151.13),dia=1.8,drill=.85)
header('C2','Cap_disc_P2.5','100 nF',(9,47.5),['1','2'],['5V_SYS','GND'],2.5,(125.73,171.45),dia=1.75,drill=.85)
header('R1','Resistor_axial_P7.62','10k / optional DHT pull-up',(64,44),['1','2'],['3V3','DHT_DATA'],7.62,(252.73,88.9),dia=1.8,drill=.9)
holes=[(4,4),(88,4),(4,66),(88,66)]
def fp_line(x0,y0,x1,y1,layer='F.SilkS',w=.18):
    return f'(fp_line (start {xy(x0,y0)}) (end {xy(x1,y1)}) (stroke (width {n(w)}) (type default)) (layer {q(layer)}))'
def rect(x0,y0,x1,y1,layer='F.SilkS',w=.18):
    return f'(fp_rect (start {xy(x0,y0)}) (end {xy(x1,y1)}) (stroke (width {n(w)}) (type default)) (fill none) (layer {q(layer)}))'
def fp_art(p):
    pads=p.pads; x=pads[-1].x
    if p.ref=='U1':
        return [rect(-8.7,-1.6,42.4,27.2,'F.Fab'),rect(-11.6,8.6,-6.8,15.8,'F.Fab'),
                rect(-.98,-1.12,36.54,1.12),fp_line(-1.05,-1.12,-1.05,1.12),
                rect(-.98,21.74,36.54,23.98),rect(-.98,24.28,36.54,26.52)]
    if 'Terminal' in p.kind:
        return [rect(-2.55,-3.8,x+2.55,4.7),fp_line(-2.55,3.4,x+2.55,3.4)]
    if p.ref=='J6':return [rect(-1.15,-1.16,1.15,11.32),rect(-1.3,-1.8,16.7,12.0,'F.Fab')]
    if p.ref=='JP1':return [rect(-1.25,-1.3,x+1.25,1.3)]
    if p.ref=='C1':return ['(fp_circle (center 1.25 0) (end 4.4 0) (stroke (width 0.16) (type default)) (fill none) (layer "F.SilkS"))',fp_line(-3.4,-.5,-3.4,.5),fp_line(-3.9,0,-2.9,0)]
    if p.ref=='C2':return [rect(-1.25,-1.45,3.75,1.45)]
    return [rect(1.5,-1.1,6.12,1.1)]
def fp(p,board,numbers):
    name=('BedroomAir:' if board else '')+p.kind
    doc=f'(footprint {q(name)} '
    if not board: doc+='(version 20240108) (generator "pcbnew") '
    doc+='(layer "F.Cu") '
    if board:doc+=f'(uuid {uid("fp."+p.ref)}) (at {xy(*p.at)}) (path "/{p.id}") '
    doc+=f'(property "Reference" {q(p.ref if board else "REF**")} (at 0 0) (layer "F.Fab") (hide yes) {effects(1,.15)}) '
    doc+=f'(property "Value" {q(p.value if board else p.kind)} (at 0 0) (layer "F.Fab") (hide yes) {effects(1,.15)}) (attr through_hole) '
    doc+=' '.join(fp_art(p))
    # These are rows of module sockets. A shared courtyard spans both row options.
    courtyards={'U1':(-11.9,-2.2,42.8,27.6),'J6':(-1.55,-2.3,17.3,12.35),'C1':(-2.25,-3.5,4.75,3.5),'C2':(-1.6,-1.8,4.1,1.8),'JP1':(-1.55,-1.55,4.1,1.55),'R1':(-1.15,-1.4,8.78,1.4)}
    extent=courtyards.get(p.ref,(-2.85,-4.1,p.pads[-1].x+2.85,5.0))
    doc+=rect(*extent,'F.CrtYd',.05)
    for k,d in enumerate(p.pads):
        shape='roundrect' if d.square else 'circle'
        doc+=f'(pad "{d.num}" thru_hole {shape} (at {xy(d.x,d.y)}) (size {xy(d.width,d.width)}) (drill {n(d.drill)}) (layers "*.Cu" "*.Mask") '
        if d.square:doc+='(roundrect_rratio 0.18) '
        if board:
            net=numbers.get((p.ref,d.num),d.net)
            if net:doc+=f'(net {netid[net]} {q(net)}) '
            doc+=f'(pinfunction {q(d.label)}) (pintype {q(pintype(p,d))}) (uuid {uid(p.ref+".pad."+str(k))}))'
        else:doc+=')'
    return doc+')'
def pintype(p,d):
    if p.ref=='U1':
        if d.num==16:return 'power_out'
        if d.num==21:return 'input'
        if d.num==22:return 'output'
        if d.num in (24,26,29):return 'bidirectional'
    return 'passive'
def schematic():
    symbols=[];placements=[]
    def prop(k,v,x,y,hidden=False):
        return f'(property {q(k)} {q(v)} (at {xy(x,y)} 0) (effects (font (size 1.27 1.27))'+(' (hide yes)' if hidden else '')+'))'
    for p in parts:
        pins=list({d.num:d for d in p.pads}.values())
        if p.ref=='U1':left=[d for d in pins if not d.net];right=[d for d in pins if d.net];hw=15.24
        else:left=pins;right=[];hw=11.43 if len(pins)>2 else 7.62
        count=max(len(left),len(right));half=((count-1)*2.54/2)+2.54
        anchor=p.schem
        def contact(d,i,side):
            y=((count-1)/2-i)*2.54
            return ((-1 if side==left else 1)*(hw+3.81),y,0 if side==left else 180)
        def make_symbol(libkey):
            ref='U' if p.ref=='U1' else ''.join(c for c in p.ref if c.isalpha())
            res=f'(symbol {q(libkey)} (pin_names (offset 0.75)) (exclude_from_sim no) (in_bom yes) (on_board yes) '
            res+=prop('Reference',ref,0,half+4.57)+prop('Value',p.kind,0,half+2.54)+prop('Footprint','BedroomAir:'+p.kind,0,0,True)+prop('Datasheet','',0,0,True)
            res+=f'(symbol "{p.kind}_0_1" (rectangle (start {xy(-hw,half)}) (end {xy(hw,-half)}) (stroke (width 0.25) (type default)) (fill (type background)))) (symbol "{p.kind}_1_1" '
            for side in [left,right]:
                for i,d in enumerate(side):
                    x,y,a=contact(d,i,side);res+=f'(pin {pintype(p,d)} line (at {xy(x,y)} {a}) (length 3.81) (name {q(d.label)} {effects(1)}) (number "{d.num}" {effects(.95)}))'
            return res+'))'
        symbols.append(make_symbol('BedroomAir:'+p.kind))
        (lib/(p.kind+'.kicad_mod')).write_text(fp(p,False,{})+'\n')
        x,y=anchor
        item=f'(symbol (lib_id "BedroomAir:{p.kind}") (at {xy(x,y)} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (uuid {p.id}) '
        item+=prop('Reference',p.ref,x,y-half-5.08)+prop('Value',p.value,x,y-half-2.54)+prop('Footprint','BedroomAir:'+p.kind,x,y,True)+prop('Datasheet','',x,y,True)
        for d in pins:item+=f'(pin "{d.num}" (uuid {uid("instance."+p.ref+str(d.num))})) '
        item+=f'(instances (project "Bedroom-Air" (path "/{uid("sheet")}" (reference "{p.ref}") (unit 1)))))'
        placements.append(item)
        for side in [left,right]:
            for i,d in enumerate(side):
                rx,ry,angle=contact(d,i,side);px=x+rx;py=y-ry;sign=-1 if angle==0 else 1
                if not d.net:
                    placements.append(f'(no_connect (at {xy(px,py)}) (uuid {uid("nc."+p.ref+str(d.num))}))');continue
                ex=px+sign*5.08
                placement=180 if sign==-1 else 0
                # A sheet-local label on a wire names a net on this sheet.
                # Global labels keep the net names stable across PCB exports.
                placements.append(f'(wire (pts (xy {xy(px,py)}) (xy {xy(ex,py)})) (stroke (width 0) (type default)) (uuid {uid("wire."+p.ref+str(d.num))}))')
                placements.append(f'(global_label {q(d.net)} (shape bidirectional) (at {xy(ex,py)} {placement}) {effects(1.0,justify=("right" if placement==180 else "left"))} (uuid {uid("label."+p.ref+str(d.num))}))')
    rootuuid=uid('sheet')
    title='(title_block (title "Bedroom Air | Sensor carrier") (date "2026-11-26") (rev "A") (comment 1 "USB at left on the assembled carrier. Sensor signal names follow the sensor.") (comment 2 "J7 regulated 5 V. Remove JP1 before attaching a computer USB cable with J7 powered."))'
    def note(s,x,y,h=1.5):
        return f'(text {q(s)} (exclude_from_sim no) (at {xy(x,y)} 0) {effects(h,justify="left bottom")} (uuid {uid("note."+s)}))'
    notes=[note('ROOM MONITOR   /   MODULE INTERCONNECT',28,26,2.3),
           note('ESP32 / 15 positions per socket row',28,64),note('Sensor-side names on the terminals',150,35),
           note('POWER   /   5 V REGULATED INPUT',28,134,1.7),note('Fit R1 only if the DHT breakout has no pull-up.',225,100,1.1)]
    schematic_file=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {rootuuid}) (paper "A4") {title} (lib_symbols '+''.join(symbols)+') '+''.join(placements+notes)+' (sheet_instances (path "/" (page "1"))) (embedded_fonts no))'
    (out/'Bedroom-Air.kicad_sch').write_text(schematic_file+'\n')
    (out/'BedroomAir.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+''.join(s.replace('"BedroomAir:','"',1) for s in symbols)+')\n')
    (out/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "BedroomAir")(type "KiCad")(uri "${KIPRJMOD}/BedroomAir.kicad_sym")(options "")(descr "Project symbols")))\n')
    (out/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "BedroomAir")(type "KiCad")(uri "${KIPRJMOD}/BedroomAir.pretty")(options "")(descr "Project footprints")))\n')
    (out/'Bedroom-Air.kicad_pro').write_text(json.dumps({'meta':{'filename':'Bedroom-Air.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.2,'min_track_width':.25,'min_copper_edge_clearance':.35}}},'net_settings':{'meta':{'version':3},'classes':[{'name':'Default','clearance':.22,'track_width':.35,'via_diameter':.8,'via_drill':.4}] }},indent=2)+'\n')
netid={name:i+1 for i,name in enumerate(netnames)}
if __name__=='__main__':schematic()
