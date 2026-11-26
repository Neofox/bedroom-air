#pragma once
static const char dashboard[] PROGMEM = R"HTML(<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f5f5ed"><title>Bedroom air</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f5ed;color:#183e33;font-family:"DM Sans",system-ui,-apple-system,sans-serif;font-variant-numeric:tabular-nums}
main{max-width:630px;margin:auto;padding:clamp(24px,6vw,50px) 20px}header,.row,.scale{display:flex;align-items:center;justify-content:space-between;gap:12px}
h1{font-weight:650;font-size:clamp(27px,6vw,36px);letter-spacing:-.045em;margin:0}header{margin-bottom:22px}
#status{font-size:13px;font-weight:600;max-width:48%;text-align:right}#status:before{content:"";display:inline-block;background:#9f7937;border-radius:50%;width:7px;height:7px;margin-right:6px}
#status.live:before{background:#328354}.hero{background:#184a3c;color:#f3f6de;border-radius:22px;padding:clamp(23px,5vw,37px)}
h2{font-size:17px;font-weight:550;margin:0}.reading{display:flex;align-items:baseline;gap:10px;margin:6px 0 28px}.reading strong{line-height:1.12;font-size:clamp(62px,16vw,98px);font-weight:550;letter-spacing:-.065em}
.reading span{font-size:21px;color:#cfdbc5}.row{font-size:13px;color:#d5e2d5}canvas{display:block;width:100%;height:74px;margin:12px 0 6px}
.scale{border-top:1px solid #76a28b;padding-top:8px;color:#c1d1c1;font-size:11px}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}
.metric{border:1px solid #d4ddcf;background:#fbfbf5;border-radius:16px;padding:clamp(15px,4vw,24px)}.metric h2{font-size:14px;color:#496354;}
.metric p{margin:12px 0 0;font-size:clamp(26px,7vw,41px);line-height:1;font-weight:550;letter-spacing:-.05em}.metric small{font-size:.52em;letter-spacing:0}
body{background:#f6f4ef;color:#292638}.hero{background:#dcd1ff;color:#282136}.reading span,.row,.scale{color:#544468}.scale{border-color:#ac9bc9}
.metrics{grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.metric{padding:14px 10px;border:0;background:#ffdbc5}.metric:nth-child(2){background:#c6eadf}.metric:nth-child(3){background:#f6e9ae}.metric h2{color:#393640}.metric p{white-space:nowrap}.metric aside{font-size:11px;padding-top:4px}
footer{font-size:12px;color:#625e6c;margin:16px 2px;display:flex;gap:10px;flex-wrap:wrap;justify-content:space-between}footer a{color:#6644a3}
</style></head><body><main><header><h1>Bedroom air</h1><span id="status" role="status">Connecting…</span></header>
<section class="hero"><h2>Carbon dioxide</h2><div class="reading"><strong id="co2">—</strong><span>ppm</span></div>
<div class="row"><span>CO₂ trend</span><span id="range"></span></div><canvas id="plot" role="img" aria-label="CO₂ readings over the last five minutes"></canvas>
<div class="scale"><span>5 min ago</span><span>Now</span></div></section>
<div class="metrics"><section class="metric"><h2>Temperature</h2><p><span id="temp">—</span> <small>°C</small></p></section>
<section class="metric"><h2>Humidity</h2><p><span id="rh">—</span> <small>%</small></p></section>
<section class="metric"><h2>Room light</h2><p><span id="lux">—</span> <small>lx</small></p><aside id="lux-status"></aside></section></div>
<footer><span id="updated">Waiting for readings…</span><a href="http://air-history.local:8080/">Bedroom dashboard &amp; history ↗</a></footer></main>
<script>
const byId = id => document.getElementById(id);
let historyPoints = [];
function draw(){
  const c=byId('plot'), w=c.clientWidth, h=c.clientHeight, dpr=window.devicePixelRatio||1;
  c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);
  const ctx=c.getContext('2d');ctx.scale(dpr,dpr);
  const vals=historyPoints.map(p=>p[1]).filter(Number.isFinite);
  byId('range').textContent='';
  if(!vals.length)return;
  const lo=Math.min(...vals), hi=Math.max(...vals), span=Math.max(40,hi-lo), mid=(lo+hi)/2;
  byId('range').textContent=(lo===hi?lo:lo+'–'+hi)+' ppm';
  ctx.strokeStyle=ctx.fillStyle='#6c49a7';ctx.lineWidth=2.4;ctx.lineJoin='round';ctx.lineCap='round';ctx.beginPath();
  let last=null;
  for(const [age,v] of historyPoints){
    if(v===null){last=null;continue;}
    const x=3+(w-6)*(1-age/300), y=h/2-(v-mid)*(h-16)/span;
    if(!last||last.age-age>7){ctx.moveTo(x,y);ctx.fillRect(x-1,y-1,2,2);}else ctx.lineTo(x,y);
    last={age,x,y};
  }
  ctx.stroke();
  if(last){ctx.beginPath();ctx.arc(last.x,last.y,3,0,Math.PI*2);ctx.fill();}
}
let timer;
async function refresh(){
  const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),5000);
  try{
    const response=await fetch('/api/readings',{cache:'no-store',signal:controller.signal});
    if(!response.ok)throw Error();
    const r=await response.json();
    byId('co2').textContent=r.co2===null?'—':r.co2.toLocaleString();
    byId('temp').textContent=r.temperature===null?'—':r.temperature.toFixed(1);
    byId('rh').textContent=r.humidity===null?'—':r.humidity.toFixed(1);
    byId('lux').textContent=Number.isFinite(r.lux)?r.lux.toLocaleString():'—';
    byId('lux-status').textContent=Number.isFinite(r.lux)?'':'Sensor not connected';
    byId('status').textContent=r.status;byId('status').className=r.status==='Live'?'live':'';
    byId('updated').textContent='Updated '+new Date().toLocaleTimeString();
    historyPoints=r.history;draw();
  }catch{
    byId('status').className='';byId('status').textContent='Offline';
    byId('co2').textContent=byId('temp').textContent=byId('rh').textContent=byId('lux').textContent='—';byId('lux-status').textContent='';
    byId('updated').textContent='Reconnecting to the monitor…';historyPoints=[];draw();
  }finally{clearTimeout(timeout);timer=setTimeout(refresh,3000);}
}
window.addEventListener('resize',draw);
refresh();
</script></body></html>)HTML";
