from collections import defaultdict
from pathlib import Path
import heapq,math,json
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union
import shapely
import design as d

here=Path(__file__).parent
numbers={(v.get('ref'),int(v.get('pin'))):net.get('name') for net in ET.parse(here/'net.xml').findall('.//nets/net') for v in net.findall('node')}
pads=defaultdict(list)
items=[]
for p in d.parts:
    for pd in p.pads:
        x,y=round(p.at[0]+pd.x,3),round(p.at[1]+pd.y,3)
        net=numbers[p.ref,pd.num]
        shape=box(x-pd.width/2,y-pd.width/2,x+pd.width/2,y+pd.width/2) if pd.square else Point(x,y).buffer(pd.width/2,quad_segs=16)
        items.append((net,-1,shape))
        if not (p.ref=='U1' and pd.y==22.86):pads[net].append((x,y))
tracks=[]
widths={'5V_SYS':.8,'GND':.8,'VIN_ESP':.8,'3V3':.55}
def commit(net,layer,pts):
    w=widths.get(net,.35)
    pts=[(round(x,4),round(y,4)) for x,y in pts]
    tracks.append({'net':net,'layer':layer,'width':w,'pts':pts})
    items.append((net,layer,LineString(pts).buffer(w/2,quad_segs=8)))
for p in d.parts[0].pads:
    if p.y==22.86:
        x=8+p.x
        commit(numbers['U1',p.num],0,[(x,34.86),(x,37.4)])
mounts=[Point(x,y).buffer(3.3) for x,y in d.holes]
antenna=box(45,5,61,43)
static=[antenna,*mounts]
grid=.25
def obstacles(net,layer):
    margin=widths.get(net,.35)/2+.31
    return unary_union([g for no,la,g in items if no!=net and la in(-1,layer)]+static).buffer(margin,quad_segs=6)
def direct(a,b):
    x,y=a;u,v=b
    dx,dy=u-x,v-y;sl=min(abs(dx),abs(dy))
    sx=math.copysign(sl,dx);sy=math.copysign(sl,dy)
    yield [a,b] if dx==0 or dy==0 or abs(abs(dx)-abs(dy))<.001 else None
    for p in [(u-sx,v-sy),(x+sx,y+sy),(x,v),(u,y)]:
        if p not in [a,b]:yield [a,p,b]
def raster(obst):
    gx,gy=np.meshgrid(np.arange(369)*grid,np.arange(281)*grid)
    mask=shapely.contains_xy(obst.buffer(.16),gx,gy)
    mask[:5,:]=True;mask[-5:,:]=True;mask[:,:5]=True;mask[:,-5:]=True
    return mask
def seek(mask,a,b):
    src=tuple(round(i/grid) for i in a);dst=tuple(round(i/grid) for i in b)
    def h(p):
        x,y=abs(p[0]-dst[0]),abs(p[1]-dst[1])
        return 10*max(x,y)+4*min(x,y)
    costs={src:0};prev={};q=[(h(src),h(src),0,src)]
    while q:
        _,_,g,pos=heapq.heappop(q)
        if costs[pos]!=g:continue
        if pos==dst:
            chain=[pos]
            while chain[-1]!=src:chain.append(prev[chain[-1]])
            chain.reverse()
            pts=[]
            for j,p in enumerate(chain):
                if 0<j<len(chain)-1:
                    before,after=chain[j-1],chain[j+1]
                    if (p[0]-before[0],p[1]-before[1])==(after[0]-p[0],after[1]-p[1]):continue
                pts.append(tuple(t*grid for t in p))
            if pts[0]!=a:pts.insert(0,a)
            if pts[-1]!=b:pts.append(b)
            return pts
        for dx,dy in [(1,1),(1,-1),(-1,1),(-1,-1),(1,0),(-1,0),(0,1),(0,-1)]:
            n=(pos[0]+dx,pos[1]+dy)
            if mask[n[1],n[0]]:continue
            k=g+(14 if dx and dy else 10)
            if k<costs.get(n,10**9):
                costs[n]=k;prev[n]=pos;hh=h(n);heapq.heappush(q,(k+hh,hh,k,n))
    return None
def pathcost(pts):return LineString(pts).length+.30*len(pts)
def route_net(net):
    endpoints=pads[net]
    covered=endpoints[:1];waiting=set(endpoints[1:])
    obs=[obstacles(net,i) for i in range(2)]
    masks=[None,None]
    while waiting:
        pairs=sorted((math.dist(a,b),a,b) for a in covered for b in waiting)
        for _,a,b in pairs:
            cand=[(pathcost(pts),l,pts) for l in range(2) for pts in direct(a,b) if pts and LineString(pts).disjoint(obs[l])]
            if not cand:
                for l in range(2):
                    if masks[l] is None:masks[l]=raster(obs[l])
                    pts=seek(masks[l],a,b)
                    if pts and LineString(pts).disjoint(obs[l]):cand.append((pathcost(pts),l,pts))
            if cand:
                _,layer,pts=min(cand)
                commit(net,layer,pts)
                covered.append(b);waiting.remove(b);break
        else:raise RuntimeError(('no route',net,waiting))
if __name__=='__main__':
    for net in ['CO2_TX','CO2_RX','I2C_SCL','I2C_SDA','DHT_DATA','VIN_ESP','5V_SYS','3V3','GND']:
        route_net(net)
        print(net,len(tracks),flush=True)
    (here/'routes.json').write_text(json.dumps(tracks,indent=1))
