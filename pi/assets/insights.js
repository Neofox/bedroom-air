'use strict';
(() => {
  const night = $('night-view'), airing = $('airing-view');
  const options = {};
  const dateLabel = t => new Date(t*1000).toLocaleDateString([], {...options,month:'short',day:'numeric'});
  const timeLabel = t => new Date(t*1000).toLocaleTimeString([], {...options,hour:'2-digit',minute:'2-digit'});
  const degrees = v => fmt(v,1)+' °C';
  let view, report, request = 0, timer;
  const threshold = $('night-threshold'), picker = $('night-pick'), dateInput = $('report-date');
  try {
    const saved = localStorage.getItem('bedroom-night-threshold');
    if ([...threshold.options].some(o=>o.value===saved)) threshold.value=saved;
  } catch {}

  function duration(seconds) {
    if(seconds<=0)return '0 min';
    if(seconds<60)return '<1 min';
    const mins=Math.floor(seconds/60), hours=Math.floor(mins/60), rest=mins%60;
    return hours ? hours+' h'+(rest?' '+rest+' min':'') : mins+' min';
  }

  function plotNight() {
    const c=$('night-line');
    if(!report || !c.clientWidth || !c.clientHeight)return;
    const {ctx:g,w,h}=prepareCanvas(c), {samples,stats,start,end,threshold:limit}=report;
    const values=samples.filter(s=>Number.isFinite(s.co2)).map(s=>s.co2);
    if(!values.length)return;
    const lo=Math.max(0,Math.floor((Math.min(...values,limit)-65)/50)*50);
    const hi=Math.ceil((Math.max(...values,limit)+80)/50)*50;
    const left=3,right=w-4,top=14,bottom=h-25;
    const x=t=>left+(right-left)*(t-start)/(end-start),y=v=>bottom-(bottom-top)*(v-lo)/(hi-lo);
    g.font='11px system-ui';g.fillStyle='#e4d9ef';g.strokeStyle='#ab9ab9';
    g.setLineDash([3,4]);g.beginPath();g.moveTo(left,y(limit));g.lineTo(right,y(limit));g.stroke();g.setLineDash([]);
    g.textAlign='right';g.fillText(fmt(limit)+' ppm',right,y(limit)-4);
    g.lineJoin='round';g.lineCap='round';g.strokeStyle='#c6b0ff';g.lineWidth=2.3;g.beginPath();
    let previous=null;
    for(const s of samples){
      if(!Number.isFinite(s.co2)){previous=null;continue;}
      if(!previous || s.t-previous.t>100)g.moveTo(x(s.t),y(s.co2));
      else g.lineTo(x(s.t),y(s.co2));
      previous=s;
    }
    g.stroke();g.beginPath();g.arc(x(stats.peakAt),y(stats.peak),3.4,0,2*Math.PI);g.fillStyle='#ffd3a8';g.fill();
    g.fillStyle='#ddcfe9';
    for(const [fraction,label] of [0, 1/3, 2/3, 1].map(f => [f, timeLabel(start + f * (end-start))])){
      g.textAlign=fraction===0?'left':fraction===1?'right':'center';g.fillText(label,left+fraction*(right-left),h-4);
    }
    c.setAttribute('aria-label','CO₂ from 20:00 to 08:00. Peak '+fmt(stats.peak)+' ppm at '+timeLabel(stats.peakAt)+'.');
  }

  function showNight(data) {
    report=data;
    const s=data.stats, partial=data.asOf<data.end;
    const elapsed=Math.min(data.asOf,data.end)-data.start;
    $('night-title').textContent=partial?'Tonight so far':data.date===data.last?'Last night':'Night report';
    $('night-dates').textContent=dateLabel(data.start)+' – '+dateLabel(data.end)+' · 20:00–08:00 at the monitor';
    picker.querySelector('[value="latest"]').textContent=data.latest===data.last?'Latest night':'Tonight so far';
    picker.querySelector('[value="latest"]').hidden=data.latest===data.last && picker.value!=='latest';
    dateInput.max=data.latest;
    dateInput.value=data.date;
    $('tonight-shortcut').hidden=data.date===data.latest || data.latest===data.last;
    $('night-data').hidden=!s.count;
    $('night-message').hidden=!!s.count;
    if(!s.count){
      $('night-message').textContent=partial?'Waiting for the first saved CO₂ reading tonight.':'No CO₂ readings were recorded for this night.';
      return;
    }
    $('night-peak').textContent=fmt(s.peak);
    $('night-peak-time').textContent='at '+timeLabel(s.peakAt);
    $('night-above').textContent=s.covered ? duration(s.above) : '—';
    $('night-coverage').textContent=duration(s.covered);
    $('night-elapsed').textContent='of '+duration(elapsed)+(partial?' elapsed':' overnight');
    const week=$('night-week');
    if(data.typicalPeak==null){
      week.textContent='Building your baseline · '+data.comparisonNights+' of 3 nights ready. Each needs at least 80% CO₂ coverage.';
    }else if(partial || s.covered<.8*(data.end-data.start)){
      week.textContent='Typical peak: '+fmt(data.typicalPeak)+' ppm across '+data.comparisonNights+' recent nights. A full comparison needs 80% coverage of a finished night.';
    }else{
      const delta=s.peak-data.typicalPeak;
      week.textContent=(delta===0?'The peak matched':fmt(Math.abs(delta))+' ppm '+(delta>0?'above':'below'))+
        ' the typical peak of '+fmt(data.typicalPeak)+' ppm (median of '+data.comparisonNights+' nights).';
    }
    plotNight();
  }

  function recovery(e) {
    switch(e.recovery){
      case 'returned':return e.recoveredAt===e.end?'Back by end of drop':duration(e.recoveredAt-e.end)+' after drop';
      case 'steady':return 'Less than 0.3 °C of cooling';
      case 'ongoing':return 'CO₂ drop in progress';
      case 'watching':return 'Watching for recovery';
      case 'unconfirmed':return 'Return unconfirmed in the observed readings';
      default:return 'Insufficient temperature readings';
    }
  }
  function eventCard(e, open, asOf) {
    const item=document.createElement('details');item.className='event-card';item.open=open;item.dataset.start=e.start;
    const title=document.createElement('summary');title.textContent=dateLabel(e.start)+' · '+timeLabel(e.start);
    const amount=document.createElement('span');amount.textContent='↓ '+fmt(e.drop)+' ppm';title.append(amount);item.append(title);
    const body=document.createElement('div');body.className='event-body';
    const row=(label,value)=>{
      const line=document.createElement('div'),a=document.createElement('span'),b=document.createElement('b');
      line.className='event-row';a.textContent=label;b.textContent=value;line.append(a,b);body.append(line);
    };
    row('CO₂ fell',fmt(e.startCO2)+' → '+fmt(e.endCO2)+' ppm');
    row('Time to low',duration(e.end-e.start)+' · '+timeLabel(e.end));
    if(e.minTemp!=null){
      row('Start → coolest',degrees(e.startTemp)+' → '+degrees(e.minTemp));
      row('Room cooled by',degrees(Math.max(0,e.startTemp-e.minTemp)));
    }else{row('Room cooling','Insufficient temperature readings');}
    row('Warm-up',recovery(e));
    const inspect=document.createElement('button');inspect.className='inspect-drop';inspect.textContent='Inspect on chart ↗';
    inspect.onclick=()=>inspectDrop(e.start-3*60,Math.min(asOf+1,(e.recoveredAt||e.end)+5*60));
    body.append(inspect);
    item.append(body);return item;
  }
  function showAiring(data) {
    $('airing-data').hidden=false;$('airing-message').hidden=true;
    $('airing-count').textContent=fmt(data.events.length);
    $('airing-covered').textContent=data.covered
      ?duration(data.covered)+' of observed CO₂ · '+(data.events.length?'Newest drop first':'No qualifying drop yet')
      :'Waiting for continuous CO₂ readings.';
    const list=$('airing-events');
    const states=new Map([...list.children].map(card=>[card.dataset.start,card.open]));
    list.replaceChildren(...data.events.map((e,i)=>eventCard(e,states.get(String(e.start))??(i===0),data.asOf)));
  }

  async function refresh() {
    clearTimeout(timer);
    const id=++request;
    if(view==='live')return;
    const isNight=view==='night', message=$(isNight?'night-message':'airing-message');
    const selected=picker.value==='date'?dateInput.value:picker.value;
    try{
      const url=isNight?'/api/night?night='+encodeURIComponent(selected)+'&threshold='+threshold.value:'/api/airing?hours='+$('airing-range').value;
      const data=await getJSON(url);
      if(id!==request)return;
      if(isNight)showNight(data);else showAiring(data);
    }catch{
      if(id!==request)return;
      $(isNight?'night-data':'airing-data').hidden=true;
      if(isNight)$('tonight-shortcut').hidden=true;
      message.hidden=false;message.textContent='The Pi could not load these readings. Retrying in a minute.';
    }
    if(id===request)timer=setTimeout(refresh,60000);
  }
  function route() {
    const hash=location.hash.slice(1);
    view=['last-night','tonight'].includes(hash)?'night':hash==='airing'?'airing':'live';
    $('live-view').hidden=view!=='live';night.hidden=view!=='night';airing.hidden=view!=='airing';
    for(const a of document.querySelectorAll('.view-nav a')){
      if(a.hash===(view==='night'?'#last-night':'#'+view))a.setAttribute('aria-current','page');
      else a.removeAttribute('aria-current');
    }
    if(view==='night'){picker.value=hash==='tonight'?'latest':'last';dateInput.hidden=true;}
    if(view==='live')redraw();
    refresh();
  }
  picker.onchange=()=>{
    dateInput.hidden=picker.value!=='date';
    if(picker.value==='date' && !dateInput.value)return;
    refresh();
  };
  dateInput.onchange=()=>{if(dateInput.value)refresh();};
  threshold.onchange=()=>{try{localStorage.setItem('bedroom-night-threshold',threshold.value);}catch{}refresh();};
  $('airing-range').onchange=refresh;
  window.addEventListener('hashchange',route);
  window.addEventListener('resize',plotNight);
  route();
})();
