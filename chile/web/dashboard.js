"use strict";
const $=id=>document.getElementById(id);
const token=document.querySelector('meta[name="local-token"]').content;
const fmt=n=>Number(n).toFixed(3);
const names={historica:'Frecuencia histórica',reciente_10:'Frecuencia 10',reciente_25:'Frecuencia 25',reciente_50:'Frecuencia 50',reciente_100:'Frecuencia 100',exponencial:'Exponencial',rezago:'Rezago',momentum:'Momentum',bayes:'Bayes',hibrida:'Híbrida',pares:'Coocurrencias',logit_online:'Regresión logística',evolutivo_online:'Evolutivo',hedge_online:'Híbrido adaptativo',lstm_online:'LSTM',azar:'Azar simulado'};
const label=s=>names[s]||s;
const pad=n=>String(n).padStart(2,'0');
const nums=arr=>arr.map(pad).join(' · ');
let result=null, offset=0, staged=null, busy=false;

function node(tag,text,cls){
  const el=document.createElement(tag);
  if(text!==undefined)el.textContent=text;
  if(cls)el.className=cls;
  return el;
}
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
function controls(value){
  busy=value;
  for(const id of ['game','lstm','reload','download','freeze','settle','prev','next','approve'])$(id).disabled=value;
  $('approve').disabled=value||!staged||!staged.new_count||!$('review').checked;
  if(!value){$('prev').disabled=offset===0;$('next').disabled=!$('next').dataset.more;}
}
async function api(path,payload){
  const opts=payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Chile-Token':token},body:JSON.stringify(payload)};
  const response=await fetch('/chile-api/'+path,opts);
  const data=await response.json();
  if(!response.ok)throw Error(data.error||'Error HTTP '+response.status);
  return data;
}
function tableRow(values){
  const tr=node('tr');
  values.forEach(v=>{const td=node('td');if(v instanceof Node)td.append(v);else td.textContent=v;tr.append(td);});
  return tr;
}
function sourceLink(url){
  try{const u=new URL(url);if(!['http:','https:'].includes(u.protocol))return node('span','—');
    const a=node('a',u.hostname);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';return a;
  }catch{return node('span','—');}
}
function recordsRows(tbody,rows){
  tbody.replaceChildren(...rows.map(r=>tableRow([r.draw,r.date,nums(r.numbers),sourceLink(r.source)])));
}
function metric(title,value){const m=node('div',undefined,'metric');m.append(node('span',title),node('strong',value));return m;}
function showLine(){
  if(!result)return;
  const selected=$('strategy').value;
  $('balls').replaceChildren(...result.lineas[selected].map(n=>node('span',pad(n),'ball')));
  $('strategy-note').textContent=label(selected)+(selected===result.estrategia?' · estrategia seleccionada por backtesting previo.':' · modelo alternativo para comparación descriptiva.')+' Todas las combinaciones tienen la misma probabilidad bajo un sorteo justo.';
}
function frequencies(){
  if(!result)return;
  const key=$('window').value;
  const max=Math.max(1,...result.frecuencias.map(x=>x[key]));
  const tiles=[],bars=[];
  for(const x of result.frecuencias){
    const t=node('div',undefined,'tile');
    t.dataset.level=String(Math.min(4,Math.floor(4*x[key]/max)));
    t.append(node('strong',pad(x.numero)),node('small',x[key]+' veces'));tiles.push(t);
    const row=node('div',undefined,'freq-row'),progress=node('progress');
    progress.max=max;progress.value=x[key];progress.setAttribute('aria-label','Número '+x.numero+', '+x[key]+' apariciones');
    row.append(node('span',pad(x.numero)),progress,node('span',x[key]));bars.push(row);
  }
  $('heat').replaceChildren(...tiles);$('freq').replaceChildren(...bars);
}
function render(d){
  result=d;
  const s=d.validacion_exploratoria[d.estrategia], c=d.contraste_media;
  $('metrics').replaceChildren(metric('Sorteos analizados',d.registros),metric('Último sorteo','#'+d.ultimo_sorteo),metric('Fecha del último',d.fecha_ultimo),metric('Media en prueba',fmt(s.media)),metric('Media aleatoria',fmt(d.azar_media)));
  const keys=Object.keys(d.lineas);
  $('strategy').replaceChildren(...keys.map(k=>{const o=node('option',label(k));o.value=k;return o;}));
  $('strategy').value=d.estrategia;showLine();
  $('target-head').textContent='≥'+d.objetivo+' aciertos';
  const ranked=Object.keys(d.seleccion).sort((a,b)=>d.seleccion[b].media-d.seleccion[a].media||a.localeCompare(b));
  $('ranking').replaceChildren(...ranked.map(k=>{const v=d.validacion_exploratoria[k];const tr=tableRow([label(k),fmt(d.seleccion[k].media),fmt(v.media),v.objetivo+'/'+v.n]);if(k===d.estrategia)tr.className='selected';return tr;}));
  const compare=node('div',undefined,'compare');
  [['p exacto de la media',c.exact_p],['p Monte Carlo',c.monte_carlo_p],['p del objetivo',d.p_objetivo],['Simulaciones',c.simulations]].forEach(([title,v],i)=>{const box=node('div');box.append(node('p',i===3?String(v):Number(v).toFixed(4),'reading'),node('small',title));compare.append(box);});
  $('comparison').replaceChildren(compare,node('p','Intervalo 95% Monte Carlo: '+c.mc_ci95.map(n=>Number(n).toFixed(4)).join(' – ')),node('p',d.advertencia,'muted'));
  const flagged=d.diagnostico_sesgo.filter(x=>x.alerta);
  $('bias').textContent=flagged.length?'Frecuencias que requieren investigación (Bonferroni): '+flagged.map(x=>pad(x.numero)+' (p='+x.p_bonferroni.toFixed(4)+')').join(', ')+'. No prueba sesgo físico.':'No se detectaron desviaciones marginales significativas con la corrección Bonferroni. Esto no demuestra ausencia de sesgo físico.';
  frequencies();
  document.dispatchEvent(new CustomEvent('chile-analysis',{detail:d}));
}
async function history(){
  const data=await api('history?game='+$('game').value+'&offset='+offset+'&limit=25');
  recordsRows($('history'),data.rows);
  const a=data.audit;
  $('audit').textContent=a.registros+' registros · '+a.bloque_reciente_contiguo+' consecutivos recientes · '+a.intervalos_faltantes.length+' intervalos faltantes. La cobertura total no ha sido verificada.';
  $('page').textContent=(data.total?offset+1:0)+'–'+Math.min(data.total,offset+25)+' de '+data.total;
  $('next').dataset.more=offset+25<data.total?'1':'';
}
async function ledger(){
  const d=await api('ledger?game='+$('game').value);
  $('ledger-summary').textContent=d.scored+' evaluados · '+d.pending+' pendientes'+(d.scored?' · media de aciertos: '+fmt(d.champion_mean):'');
  $('ledger').replaceChildren(...d.rows.map(r=>tableRow([r.target,r.created,label(r.strategy),nums(r.numbers),r.actual?nums(r.actual):'Pendiente',r.matches===null?'—':r.matches])));
}
function resetStage(){staged=null;$('stage').hidden=true;$('review').checked=false;}
async function run(work){
  if(busy)return;
  controls(true);status('Procesando…');
  try{const message=await work();status(message||'Análisis actualizado.');}catch(e){status(e.message,true);}finally{controls(false);}
}
async function load(refresh=false){
  await run(async()=>{
    const d=await api('analysis?game='+$('game').value+'&lstm='+($('lstm').checked?'1':'0')+'&refresh='+(refresh?'1':'0'));
    render(d);await history();await ledger();
    return 'Historial local cargado. Próximo sorteo sujeto a calendario oficial.';
  });
}
$('game').onchange=()=>{offset=0;resetStage();$('verified').checked=false;$('deadline').value='';result=null;document.dispatchEvent(new Event('chile-reset'));for(const id of ['metrics','balls','ranking','comparison','heat','freq','history','ledger','strategy'])$(id).replaceChildren();for(const id of ['strategy-note','bias','audit','page','ledger-summary'])$(id).textContent='';load();};
$('reload').onclick=()=>load(true);
$('lstm').onchange=()=>load();
$('strategy').onchange=showLine;
$('window').onchange=frequencies;
$('prev').onclick=()=>run(async()=>{offset=Math.max(0,offset-25);await history();return 'Historial actualizado.';});
$('next').onclick=()=>run(async()=>{offset+=25;await history();return 'Historial actualizado.';});
$('download').onclick=()=>run(async()=>{
  resetStage();
  const d=await api('stage',{game:$('game').value});
  staged=d;
  if(!d.new_count)return 'No hay registros nuevos en la fuente consultada.';
  const table=node('table'),body=node('tbody');
  recordsRows(body,d.rows);table.append(body);$('candidates').replaceChildren(table);$('stage').hidden=false;
  return d.new_count+' candidatos disponibles para revisión; el histórico aún no cambió.';
});
$('review').onchange=()=>{$('approve').disabled=busy||!staged||!$('review').checked;};
$('approve').onclick=()=>run(async()=>{
  await api('approve',{game:$('game').value,stage_hash:staged.stage_hash,reviewed:$('review').checked});
  resetStage();offset=0;await history();render(await api('analysis?game='+$('game').value+'&lstm='+($('lstm').checked?'1':'0')));await ledger();
  return 'Candidatos incorporados al archivo local.';
});
$('freeze').onclick=()=>run(async()=>{
  const d=await api('freeze',{game:$('game').value,deadline:$('deadline').value.trim(),reviewed:$('verified').checked,lstm:$('lstm').checked});
  await ledger();$('verified').checked=false;
  return 'Pronóstico local congelado para sorteo '+d.target+'.';
});
$('settle').onclick=()=>run(async()=>{
  const d=await api('settle',{game:$('game').value,reviewed:$('verified').checked});
  await ledger();$('verified').checked=false;
  return d.scored.length+' pronósticos evaluados.';
});
load();
