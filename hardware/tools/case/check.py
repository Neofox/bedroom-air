import sys
import numpy as np
from pathlib import Path
case_dir = Path(__file__).resolve().parents[2] / 'Case'
sys.path.insert(0, str(case_dir))
import enclosure as e
base, lid, keeper = e.base(), e.lid(), e.co2_keeper()
assembly = e.union([base,lid,keeper])

def disjoint(name,a,b):
    v=(a^b).volume()
    print(name,f'{v:.7f} mm3')
    assert abs(v)<.0003
def b(*coords): return e.box(*coords)
disjoint('base / lid',base,lid)
disjoint('keeper / base',keeper,base)
disjoint('keeper / lid',keeper,lid)
disjoint('carrier',assembly,b(0,0,e.PCB_SEAT,92,70,e.PCB_SEAT+1.6))
disjoint('ESP edge within notch',assembly,b(-1.5,9.5,16,51,40,19))
disjoint('USB plug body insertion',assembly,b(-16,13.5,10.0,5.0,35.5,24.0))
z=e.LIGHT_SEAT
disjoint('GY-302 substrate',assembly,b(63.6,7.38,z,81.65,20.93,z+1.6))
disjoint('GY-302 standard J6 socket and male spacer',assembly,b(63.60,7.5,9,66.4,20.5,z))
disjoint('GY-302 component envelope including short solder tails',assembly,b(63.6,7.38,z+1.6,81.65,20.93,z+2.6))
disjoint('ESP32 shield clearance with standard 8.5+2.54 header stack',assembly,b(13.0,13.0,20.04,38.0,36.0,25.2))
disjoint('ESP32 aerial end standard header stack',assembly,b(38.0,10.,20.04,51.,40.,22.5))
disjoint('USB-C jack clearance',assembly,b(-3.55,18.9,20.04,5.1,30.0,25.4))
for name,x0,x1 in [('CO2 terminal',6,27),('DHT terminal',59,75),('power terminal',34,45)]:
    disjoint(name,assembly,b(x0,50,9.0,x1,61,22))
disjoint('C1 6.3 mm x 12.5 mm',assembly,e.tube(52.25,54,9,21.5,6.3))
disjoint('approx DHT module PCB',assembly,b(66,83.0,8.45,88,124.8,10))
disjoint('DHT white housing',assembly,b(69.2,100.5,10,84.8,125.7,18.1))
disjoint('M12 locknut envelope, diameter 20 mm x 4.5 mm',assembly,e.M.cylinder(4.5,10,circular_segments=48).rotate((90,0,0)).translate((52,127.8,e.GLAND_Z)))
# Supplier drawing: case is 26 x 19.7; add nominal envelope tolerance on each axis.
disjoint('gold case and diffusion film',assembly,e.co2(b(2.85,-10.10,5.7,29.55,10.10,15.8)))
disjoint('tip naked FR4, 13.6 W x 1.65 thick',assembly,e.co2(b(0,-6.8,6.4,2.8,6.8,8.05)))
disjoint('neck FR4 up to shoulder',assembly,e.co2(b(29.55,-6.8,6.4,32.2,6.8,8.05)))
disjoint('plug end PCB, 10.2 W',assembly,e.co2(b(32.5,-5.1,6.4,39.1,5.1,8.05)))
disjoint('plug and pigtail housing',assembly,e.co2(b(34,-5.3,7.9,42.6,5.3,12.0)))
# Relative motion bounded by the stop tabs, after which the keeper still catches the PCB.
for dx,dy in ((-.4,-.20),(.7,.20)):
    trial=e.co2(b(2.85+dx,-10.1+dy,5.7,29.55+dx,10.1+dy,15.8))
    disjoint('gold chamber at tolerance offset',assembly,trial)
for x,y in e.PCB_HOLES:
    disjoint('M3x6 carrier shank',base,e.tube(x,y,3.01,9.0,2.55))
for x,y in e.LID_HOLES:
    disjoint('M3 lid pilot',assembly,e.tube(x,y,e.RIM+e.rise_at(x)-6.5,41,2.55))
print('All interference checks passed.')

# Verify the lid sightline from the active face, for several common stack tolerances.
import math
cx,cy=e.LIGHT_CHIP_XY
chip_z=e.LIGHT_SEAT+1.6+.8
print('Nominal chip Z and vertical recess:',chip_z, e.RIM+e.CAP+e.rise_at(cx)-chip_z)
screws=e.union([e.tube(x,y,e.RIM+e.CAP+e.rise_at(x)-.45,e.RIM+e.CAP+e.rise_at(x)+1.75,6.3) for x,y in e.LID_HOLES])
optics=e.union([lid,base,screws])
def ray_blocked(x,y,z,theta):
    for az in np.deg2rad(np.arange(0,360,1)):
        origin=np.array([x,y,z])
        t=math.radians(theta)
        direction=np.array([math.sin(t)*math.cos(az),math.sin(t)*math.sin(az),math.cos(t)])
        if optics.ray_cast(origin,origin+direction*150):return True
    return False
angles = [a for a in range(90) if ray_blocked(cx,cy,chip_z,a)]
print('Nominal first blocked whole-degree ray:',min(angles))
for dx in [-.5,.5]:
    for dy in [-.5,.5]:
        for dz in [-1.0,.5]:
            assert not ray_blocked(cx+dx,cy+dy,chip_z+dz,60)
print('Fixed lamp at 60 deg clears the enclosure for all 360 sampled azimuths at the specified worst-case offsets.')
import trimesh
m=trimesh.load_mesh(case_dir / '02-lid.stl')
bed=np.all(np.abs(m.vertices[m.faces][:,:,2])<.001,axis=1)
contact=m.area_faces[bed].sum()
print('Lid planar print contact:',round(contact),'mm2')
assert contact>10000
