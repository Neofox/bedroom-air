'use strict';
const $ = id => document.getElementById(id);
const metrics = {
  co2: {label:'Carbon dioxide',unit:'ppm',color:'#7952c0',fill:'#ede5fc',floor:40,digits:0},
  temperature: {label:'Temperature',unit:'°C',color:'#b65c3c',fill:'#fae5d8',floor:1,digits:1},
  humidity: {label:'Humidity',unit:'%',color:'#21866d',fill:'#d5eee5',floor:3,digits:1},
  lux: {label:'Room light',unit:'lx',color:'#997119',fill:'#f7edc4',floor:5,digits:1}
};
const clock = t => new Date(t*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
const day = d => d.toLocaleDateString([], {month:'short',day:'numeric'});
const fmt = (v,d=0) => Number.isFinite(v)?v.toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const localDate = d => [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
let metric='co2', samples=[], live=null, recent=[], from=0, to=0, seq=0, picked=null, liveTimer, historyTimer;
let dropWindow = null;
const initially = new Date(), evening = new Date(initially);
if (evening.getHours()<20) evening.setDate(evening.getDate()-1);
$('night').max=localDate(initially); $('night').value=localDate(evening);
$('today').textContent=initially.toLocaleDateString(undefined,{weekday:'short',month:'long',day:'numeric'});

function prepareCanvas(c) {
  const w=c.clientWidth,h=c.clientHeight, d=window.devicePixelRatio||1;
  c.width=Math.round(w*d); c.height=Math.round(h*d);
  const ctx=c.getContext('2d'); ctx.scale(d,d);
  return {ctx,w,h};
}
function drawIcon(c) {
  const {ctx:g,w,h}=prepareCanvas(c);
  g.scale(w/24,h/24);g.lineWidth=1.7;g.lineCap='round';g.lineJoin='round';g.strokeStyle='#34323a';
  g.beginPath();
  if(c.dataset.icon==='temp'){
    g.moveTo(9,14);g.lineTo(9,5);g.arc(12,5,3,Math.PI,0);g.lineTo(15,14);
    g.arc(12,17,4.3,-.8,Math.PI+.8);g.closePath();g.stroke();
    g.beginPath();g.moveTo(12,9);g.lineTo(12,17);g.stroke();
  } else if(c.dataset.icon==='rh'){
    g.moveTo(12,3);g.bezierCurveTo(10,7,5,11,5,15);g.arc(12,15,7,Math.PI,0,true);
    g.bezierCurveTo(19,11,14,6,12,3);g.closePath();g.stroke();
  } else {
    g.arc(12,12,4,0,Math.PI*2);g.stroke();
    for(let i=0;i<8;i++){const a=i*Math.PI/4;g.beginPath();g.moveTo(12+7*Math.cos(a),12+7*Math.sin(a));g.lineTo(12+10*Math.cos(a),12+10*Math.sin(a));g.stroke();}
  }
}
function drawDial() {
  if(!$('dial').clientWidth)return;
  const {ctx:g,w,h}=prepareCanvas($('dial')); const scale=Math.min(w/256,h/145);
  g.translate((w-256*scale)/2,(h-145*scale)/2);g.scale(scale,scale);
  const cx=128,cy=113, r=88, angle=n=>Math.PI*(1+Math.min(1,Math.max(0,(n-400)/2100)));
  for(const [a,b,c] of [[400,800,'#67bda2'],[800,1500,'#eec15f'],[1500,2500,'#ed927c']]){
    g.beginPath();g.strokeStyle=c;g.lineWidth=24;g.arc(cx,cy,r,angle(a)+.011,angle(b)-.011);g.stroke();
  }
  for(let i=0;i<=28;i++){
    const a=Math.PI*(1+i/28),rad=i%4===0?105:102;
    g.beginPath();g.lineWidth=i%4===0?1.8:1;g.strokeStyle='#625576';
    g.moveTo(cx+rad*Math.cos(a),cy+rad*Math.sin(a));g.lineTo(cx+109*Math.cos(a),cy+109*Math.sin(a));g.stroke();
  }
  if(Number.isFinite(live?.co2)){
    const a=angle(live.co2);g.save();g.translate(cx,cy);g.rotate(a);g.fillStyle='#322b40';
    g.beginPath();g.moveTo(-5,-5);g.lineTo(94,0);g.lineTo(-5,5);g.closePath();g.fill();g.restore();
  }
  g.fillStyle='#322b40';g.beginPath();g.arc(cx,cy,7,0,2*Math.PI);g.fill();
  g.fillStyle='#5c506e';g.textAlign='center';g.font='600 12px system-ui';g.fillText('400',37,135);g.fillText('2,500+',218,135);
}
function bounds(period) {
  if(period==='drop' && dropWindow)return dropWindow;
  if(period==='night'){
    const a=new Date(($('night').value||localDate(evening))+'T20:00:00'),b=new Date(a);
    b.setDate(b.getDate()+1);b.setHours(8,0,0,0);return [a.getTime()/1000,b.getTime()/1000];
  }
  const b=Math.floor(Date.now()/1000)+1;
  return [b-Number(period)*3600,b];
}
function renderLive() {
  $('co2').textContent=fmt(live?.co2);
  $('temp').textContent=fmt(live?.temperature,1);$('rh').textContent=fmt(live?.humidity,1);
  $('lux').textContent=fmt(live?.lux,Number.isFinite(live?.lux)&&live.lux<10?1:0);
  $('light-status').textContent=live&&live.lux==null?'Sensor not connected':'';
  const conn=$('connection');conn.classList.toggle('online',!!live);
  conn.lastElementChild.textContent=live?'Sensor online':'Sensor offline';
  const points=recent.filter(p=>Number.isFinite(p.co2)&&live&&live.t-p.t>=0&&live.t-p.t<=920);
  const first=points[0], minutes=first&&live?Math.round((live.t-first.t)/60):0;
  if(!live)$('trend').textContent='Waiting for the ESP32';
  else if(!Number.isFinite(live.co2))$('trend').textContent=live.status||'Awaiting a reading';
  else if(minutes>=2){
    const delta=live.co2-first.co2;
    $('trend').textContent=delta===0?'Steady over '+minutes+' min':(delta>0?'↗ Up ':'↘ Down ')+fmt(Math.abs(delta))+' ppm in '+minutes+' min';
  }else $('trend').textContent='Measured at '+clock(live.t);
  drawDial();
}
async function getJSON(path) {
  const ctrl=new AbortController(), alarm=setTimeout(()=>ctrl.abort(),10000);
  try {const r=await fetch(path,{cache:'no-store',signal:ctrl.signal});if(!r.ok)throw Error(r.status);return await r.json();}
  finally{clearTimeout(alarm);}
}
async function getLive(){
  try{live=await getJSON('/api/live');}catch{live=null;}
  renderLive();liveTimer=setTimeout(getLive,4000);
}
async function getHistory(){
  clearTimeout(historyTimer);const id=++seq,period=$('period').value;
  $('night').hidden=period!=='night';const [a,b]=bounds(period);
  try {
    const data=await getJSON('/api/history?from='+a+'&to='+b);
    if(id!==seq)return; samples=data;
    if(period!=='night' && period!=='drop')recent=data;
    else {
      const now=Math.floor(Date.now()/1000)+1;
      getJSON('/api/history?from='+(now-920)+'&to='+now).then(v=>{if(id===seq){recent=v;renderLive();}}).catch(()=>{});
    }
    $('record-status').textContent=data.length+' saved minute'+(data.length===1?'':'s')+' · Raspberry Pi';
  }catch{
    if(id!==seq)return;samples=[];$('record-status').textContent='History unavailable · retrying';
  }
  from=a;to=b;
  $('period-caption').textContent=day(new Date(a*1000))+' · '+clock(a)+' – '+clock(b);
  if(picked!==null&&!samples.some(s=>s.t===picked))picked=null;
  renderHistory();if(live)renderLive();historyTimer=setTimeout(getHistory,30000);
}
function renderHistory(){
  const m=metrics[metric], data=samples.filter(s=>Number.isFinite(s[metric]));
  const values=data.map(s=>s[metric]),summary=values.length?[Math.min(...values),values.reduce((a,b)=>a+b,0)/values.length,Math.max(...values)]:[];
  ['low','avg','high'].forEach((id,i)=>$(id).textContent=summary.length?fmt(summary[i],m.digits)+' '+m.unit:'—');
  if(!$('plot').clientWidth)return;
  const {ctx:g,w,h}=prepareCanvas($('plot'));const l=45,r=w-10,top=15,bot=h-27;
  $('empty').hidden=values.length>0;
  $('empty').textContent=metric==='lux'?'No light readings for this period':'No readings for this period';
  const tip=$('tip');tip.hidden=true;
  if(!values.length)return;
  const divisor=10**m.digits;
  const min=summary[0], max=summary[2], raw=Math.max(m.floor,max-min);
  const yMin=Math.max(metric==='temperature'?-Infinity:0, Math.floor((min-raw*.14)*divisor)/divisor);
  const yMax=Math.max(yMin+m.floor,Math.ceil((max+raw*.14)*divisor)/divisor);
  const x=t=>l+(t-from)/(to-from)*(r-l), y=v=>bot-(v-yMin)/(yMax-yMin)*(bot-top);
  g.font='11px system-ui';g.textBaseline='middle';
  for(let i=0;i<4;i++){const v=yMin+(yMax-yMin)*i/3,yy=y(v);g.strokeStyle='#e7e4df';g.setLineDash([2,4]);g.beginPath();g.moveTo(l,yy);g.lineTo(r,yy);g.stroke();g.fillStyle='#686370';g.textAlign='right';g.fillText(fmt(v,m.digits),l-6,yy);}
  g.setLineDash([]);
  const timeLabels=w<430?3:5;
  for(let i=0;i<timeLabels;i++){
    const t=from+(to-from)*i/(timeLabels-1);g.textAlign=i===0?'left':i===timeLabels-1?'right':'center';g.fillText(clock(t),x(t),h-9);
  }
  const gradient=g.createLinearGradient(0,top,0,bot);gradient.addColorStop(0,m.fill);gradient.addColorStop(1,'#fffefa');
  function segment(group){
    if(!group.length)return;
    const first=group[0],last=group[group.length-1];g.beginPath();g.moveTo(x(first.t),bot);
    group.forEach(s=>g.lineTo(x(s.t),y(s[metric])));g.lineTo(x(last.t),bot);g.closePath();g.fillStyle=gradient;g.fill();
    g.beginPath();group.forEach((s,i)=>{if(i)g.lineTo(x(s.t),y(s[metric]));else g.moveTo(x(s.t),y(s[metric]));});g.lineWidth=2.5;g.lineJoin='round';g.strokeStyle=m.color;g.stroke();
    if(group.length===1){g.fillStyle=m.color;g.beginPath();g.arc(x(first.t),y(first[metric]),2.7,0,Math.PI*2);g.fill();}
  }
  let group=[];
  for(const s of samples){if(!Number.isFinite(s[metric])||(group.length&&s.t-group[group.length-1].t>100)){segment(group);group=[];}if(Number.isFinite(s[metric]))group.push(s);}
  segment(group);
  const point=data.find(s=>s.t===picked)||data[data.length-1],px=x(point.t),py=y(point[metric]);
  if(picked!==null){g.strokeStyle=m.color;g.lineWidth=1;g.setLineDash([3,3]);g.beginPath();g.moveTo(px,top);g.lineTo(px,bot);g.stroke();g.setLineDash([]);
    tip.textContent=clock(point.t)+' · '+fmt(point[metric],m.digits)+' '+m.unit;tip.hidden=false;
    tip.style.left=Math.max(1,Math.min(w-tip.offsetWidth-1,px-tip.offsetWidth/2))+'px';tip.style.top=Math.max(0,py-34)+'px';}
  g.fillStyle=m.color;g.strokeStyle='#fff';g.lineWidth=2;g.beginPath();g.arc(px,py,4.5,0,2*Math.PI);g.fill();g.stroke();
}
function selectMetric(key){metric=key;picked=null;document.querySelectorAll('[data-metric]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.metric===key)));renderHistory();}
function inspectPointer(e){
  const valid=samples.filter(s=>Number.isFinite(s[metric]));if(!valid.length)return;
  const rect=$('plot').getBoundingClientRect(),t=from+(e.clientX-rect.left-45)/(rect.width-55)*(to-from);
  picked=valid.reduce((a,b)=>Math.abs(b.t-t)<Math.abs(a.t-t)?b:a).t;renderHistory();
}
$('plot').onpointerdown=inspectPointer;$('plot').onpointermove=e=>{if(e.pointerType==='mouse'||e.buttons)inspectPointer(e);};
$('plot').onpointerleave=e=>{if(e.pointerType==='mouse'){picked=null;renderHistory();}};
$('plot').onkeydown=e=>{
  if(!['ArrowLeft','ArrowRight','Escape'].includes(e.key))return;e.preventDefault();
  const valid=samples.filter(s=>Number.isFinite(s[metric]));if(!valid.length)return;
  if(e.key==='Escape')picked=null;
  else{let i=picked===null?valid.length-1:valid.findIndex(s=>s.t===picked);picked=valid[Math.min(valid.length-1,Math.max(0,i+(e.key==='ArrowLeft'?-1:1)))].t;}renderHistory();
};
document.querySelectorAll('[data-metric]').forEach(b=>b.onclick=()=>selectMetric(b.dataset.metric));
$('period').onchange=$('night').onchange=()=>{picked=null;getHistory();};
function inspectDrop(start,end) {
  dropWindow=[start,end];
  const period=$('period');
  if(!period.querySelector('[value="drop"]'))period.add(new Option('Selected CO₂ drop','drop'));
  period.value='drop';picked=null;selectMetric('co2');
  location.hash='live';
  getHistory();
  requestAnimationFrame(()=>document.querySelector('.history').scrollIntoView({block:'start'}));
}
function redraw(){document.querySelectorAll('[data-icon]').forEach(drawIcon);drawDial();renderHistory();}
window.addEventListener('resize',redraw);redraw();getLive();getHistory();
