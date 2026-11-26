from pathlib import Path
import sys
import numpy as np
import trimesh
import mitsuba as mi
mi.set_variant("scalar_rgb")
case_dir = Path(__file__).resolve().parents[2] / 'Case'
sys.path.insert(0, str(case_dir))
import enclosure as e

here = Path(__file__).resolve().parent / 'rendered'
here.mkdir(exist_ok=True)
T=mi.ScalarTransform4f
colors={
 'porcelain':(.70,.72,.67),'green':(.04,.25,.17),'black':(.025,.033,.036),
 'metal':(.44,.47,.47),'dark':(.10,.15,.15),'terminal':(.095,.43,.145),
 'gold':(.71,.36,.075),'film':(.33,.31,.28),'blue':(.055,.24,.46),
 'white':(.77,.79,.78),'red':(.53,.065,.065),'yellow':(.76,.44,.055),
 'teal':(.08,.39,.39),'keeper':(.13,.23,.23),'tan':(.58,.40,.16),
 'lightgreen':(.22,.41,.28),'slate':(.28,.34,.35)
}
mats={}
def add(mat,solid): mats.setdefault(mat,[]).append(solid)
b=e.box
def rod(p0,p1,d):
    a=np.array(p0,dtype=float); v=np.array(p1,dtype=float)-a; u=v/np.linalg.norm(v)
    any_dir=np.array([1,0,0]) if abs(u[0])<.9 else np.array([0,1,0])
    h=np.cross(u,any_dir); h/=np.linalg.norm(h); j=np.cross(u,h)
    mat=np.column_stack((h,j,u,a))
    return e.M.cylinder(np.linalg.norm(v),d/2,circular_segments=20).transform(mat)
def wire(col,points,d=1.25):
    for p0,p1 in zip(points,points[1:]): add(col,rod(p0,p1,d))
    for p in points[1:-1]: add(col,e.M.sphere(d/2,circular_segments=12).translate(p))
def screw(x,y,z,d=4.8):
    h=e.tube(x,y,z,z+1.05,d)
    recess=e.union([b(x-.35,y-1.5,z+.54,x+.35,y+1.5,z+1.2),b(x-1.5,y-.35,z+.54,x+1.5,y+.35,z+1.2)])
    add('metal',h-recess)
def gland():
    cx=e.GLAND_X; cz=e.GLAND_Z
    def body(y0,y1,d,n):
        return e.M.cylinder(y1-y0,d/2,circular_segments=n).rotate((-90,0,0)).translate((cx,y0,cz))
    for y0,y1,d,n in ((123.8,127.8,19.4,6),(127.8,131.0,11.8,40),(130.0,133,17.9,6),(133.,138.,15.4,48),(138.,143.,15.9,24),(143,144.6,13.7,40)):
        add('dark',body(y0,y1,d,n))
    wire('black',[(cx,143.,cz),(cx,149.,cz),(cx+1.2,154.,cz-.8),(cx+4.1,159.,cz-2.1)],4.4)

def electronics():
    core=b(0,0,7.4,92,70,9)
    for x,y in e.PCB_HOLES:
        core-=e.tube(x,y,7,10,3.2)
        screw(x,y,9)
    add('green',core)
    for y in (12.0,34.86):
        add('black',b(6.7,y-1.3,9.0,44.86,y+1.3,17.2))
        for i in range(15):
            add('metal',e.tube(8+2.54*i,y,16.6,19.95,.85))
    esp=e.obround(-1.2,9.8,50.6,37.0,1.9,17.2,18.8)
    add('black',esp)
    add('metal',e.obround(16.0,14.2,36.1,32.3,.85,18.8,21.9))
    add('black',b(36.1,14.2,18.8,49.0,32.3,19.3))
    for x in (38.0,40.4,42.8,45.2,47.6):
        add('tan',b(x,15.5,19.3,x+.42,21.8,19.5))
        add('tan',b(x,21.4,19.3,x+2.1,21.85,19.5))
    add('dark',b(6.2,18.1,18.8,12.7,25.8,20.5))
    shell=e.obround(-4.0,19.5,3.8,27.7,.7,18.8,21.8)
    add('metal',shell-b(-4.2,20.05,19.2,2.0,27.15,21.3))
    for y in (13.7,32.8): add('slate',b(.8,y,18.8,4.5,y+2.,20.0))
    for x0,count in ((9,4),(37,2),(62,3)):
        t=b(x0-2.5,50.5,9,x0+5.0*(count-1)+2.5,58.9,19)
        holes=[]
        for i in range(count):
            x=x0+i*5
            holes.extend([e.tube(x,54.2,17.3,21,3.55),b(x-1.5,57.6,11.4,x+1.5,59.1,15.9)])
            screw(x,54.2,17.3,3.15)
        add('terminal',e.cut(t,holes))
    add('black',e.tube(52.3,54,9,20.6,6.3))
    add('metal',e.tube(52.3,54,20.6,20.8,6.05))
    add('black',b(38.8,44.8,9.,43.8,47.2,14.4))
    # BH1750 on the ordinary straight header, below the sloped roof.
    seat=e.LIGHT_SEAT
    add('black',b(63.7,7.7,9,66.3,20.4,17.5))
    add('black',b(63.75,7.75,seat-2.5,66.25,20.4,seat))
    panel=e.obround(63.6,7.38,81.65,20.93,.45,seat,seat+1.6)
    for x,y in ((79.4,9.75),(79.4,18.5)):
        panel-=e.tube(x,y,seat-.2,seat+1.7,3.1)
    add('blue',panel)
    for i in range(5):
        x,y=65,9+2.54*i
        add('metal',b(x-.32,y-.32,17.4,x+.32,y+.32,seat+2.15))
    cx,cy=e.LIGHT_CHIP_XY
    add('dark',b(cx-.85,cy-1.35,seat+1.6,cx+.85,cy+1.35,seat+2.4))
    for x in (67.5,68.8):
        for y in (9.4,11.4,16.2,18.5):
            add('slate',b(x,y,seat+1.6,x+.65,y+.85,seat+2.1))
    # CO2 electronics, diffusion film and right-angle factory connector.
    g=e.co2
    add('green',g(b(0,-6.65,6.4,32.2,6.65,7.65)))
    add('green',g(b(32.2,-5.0,6.4,38.8,5.0,7.65)))
    add('gold',g(e.obround(3.15,-9.85,29.15,9.85,.7,6.4,15.0)))
    add('film',g(b(21,-9.75,15,28.85,-.65,15.05)))
    add('white',g(b(34,-5.05,7.65,41.25,5.05,10.82)))
    for u,v in e.KEEPER_SCREWS:
        screw(e.CO2_X+v,e.CO2_Y-u,10.8,4.35)
    add('keeper',e.co2_keeper())
    # AM2302 breakout with clear airflow paths over the perforated housing.
    add('black',b(69.5,84.3,8.45,84.5,119.3,10.05))
    add('black',b(73.1,80.3,10.05,80.9,86.3,12.55))
    dht=e.obround(69.45,100.6,84.55,121.7,.9,10.05,17.9)
    dht_cut=[]
    for x in (71.0,74.1,77.2,80.3):
        for y in (102.1,106.7,111.3,115.9):
            dht_cut.append(b(x,y,15.4,x+1.65,y+3.1,18))
    add('white',e.cut(dht,dht_cut))
    tab=e.obround(73.1,119.2,80.9,126.6,2.5,9.9,11.5)
    add('white',tab-e.tube(77,123.3,9,12,3.0))
    screw(77,123.3,11.5,4.2)
    for i,col in enumerate(('black','red','yellow','teal')):
        a=9+5*i; u=21.0+1.3*i
        wire(col,[(a,58.85,13.2),(a,62,13.0),(a+1,66+i*.6,12.1),(u,73.0,9.2),(u,79.65,8.0),(u,83.1,9.1)],1.15)
    for i,col in enumerate(('yellow','red','black')):
        a=62+5*i; x=74.5+2.5*i
        wire(col,[(a,58.8,13.1),(a,64.5,12.8),(a+3.4,68.4,12.),(75+i*2.5,74,11.4),(x,79.9,11.1)],1.25)
    wire('black',[(52,125.0,e.GLAND_Z),(52,103,11),(52,88,8.5),(52,78.5,9.8)],4.3)
    for i,col in enumerate(('black','red')):
        wire(col,[(50.8+i*2.4,79,9.8),(48+i*2,71,11),(37+i*5,64,12.4),(37+i*5,58.9,13.0)],1.4)

def build(covered):
    mats.clear(); add('porcelain',e.base())
    electronics(); gland()
    if covered:
        add('porcelain',e.lid())
        for x,y in e.LID_HOLES: screw(x,y,e.RIM+e.CAP+e.rise_at(x)-.45,5.4)
    scene={'type':'scene','integrator':{'type':'path','max_depth':5},
           'env':{'type':'constant','radiance':{'type':'rgb','value':[.67,.71,.72]}}}
    # Smooth diffuse studio illumination and grounding shadow.
    scene['softbox']={'type':'rectangle','to_world':T().look_at(origin=[-90,-110,220],target=[50,66,0],up=[0,1,0])@T().scale([76,76,1]),
      'emitter':{'type':'area','radiance':{'type':'rgb','value':[6.8,6.45,5.95]}}}
    scene['floor']={'type':'rectangle','to_world':T().translate([50,70,-.095])@T().scale([12000,12000,1]),
      'bsdf':{'type':'diffuse','reflectance':{'type':'rgb','value':[.72,.72,.68]}}}
    for mat,geos in mats.items():
        path=here/f'{"closed" if covered else "open"}-{mat}.ply'
        # Mesh concatenation keeps individual realistic material boundaries.
        parts=[e.mesh(e.physical(x)) for x in geos]
        trimesh.util.concatenate(parts).export(path)
        col=colors[mat]
        bsdf={'type':'diffuse','reflectance':{'type':'rgb','value':col}}
        if mat in ('metal','gold'): bsdf={'type':'roughconductor','material':'Al' if mat=='metal' else 'Au','alpha':.29}
        scene[mat]={'type':'ply','filename':str(path),'face_normals':True,'bsdf':bsdf}
    center=[50,65,9]
    eye=[174,-124,103] if covered else [-18,-82,250]
    scene['camera']={'type':'perspective','fov':42 if covered else 37,'to_world':T().look_at(origin=eye,target=center,up=[0,0,1]),
      'film':{'type':'hdrfilm','width':760,'height':720,'rfilter':{'type':'gaussian'}},
      'sampler':{'type':'independent','sample_count':96}}
    result=mi.render(mi.load_dict(scene))
    mi.util.write_bitmap(str(here/('closed.png' if covered else 'open.png')),result)

if __name__=='__main__': build(sys.argv[1]=='closed')
