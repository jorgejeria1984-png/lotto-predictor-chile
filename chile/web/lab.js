"use strict";
(()=>{
const $=x=>document.getElementById(x);
const token=document.querySelector('meta[name="local-token"]').content;
const labels={historica:'Histórica',reciente_25:'Reciente 25',exponencial:'Exponencial',momentum:'Momentum',rezago:'Rezago',hedge_online:'Híbrido adaptativo'};
let data=null;
const f=x=>Number(x).toFixed(3);
function chart(id,series,axis,zero=false){
 const c=$(id),ctx=c.getContext('2d'),w=c.width,h=c.height,p=45;
 ctx.clearRect(0,0,w,h);
 const values=series.flatMap(s=>s.values);
 let lo=Math.min(...values,0),hi=Math.max(...values,0);
 if(hi===lo)hi=lo+1;
 const y=v=>h-p-(v-lo)/(hi-lo)*(h-2*p),x=i=>p+i*(w-2*p)/Math.max(1,axis.length-1);
 ctx.font='12px system-ui';ctx.fillStyle='#526879';ctx.strokeStyle='#d9e2e9';
 for(let j=0;j<=4;j++){const v=lo+(hi-lo)*j/4;ctx.beginPath();ctx.moveTo(p,y(v));ctx.lineTo(w-p,y(v));ctx.stroke();ctx.fillText(f(v),3,y(v)+4);}
 if(zero){ctx.strokeStyle='#8495a2';ctx.beginPath();ctx.moveTo(p,y(0));ctx.lineTo(w-p,y(0));ctx.stroke();}
 for(const s of series){ctx.strokeStyle=s.color;ctx.lineWidth=2;ctx.beginPath();s.values.forEach((v,i)=>i?ctx.lineTo(x(i),y(v)):ctx.moveTo(x(i),y(v)));ctx.stroke();s.values.forEach((v,i)=>{ctx.beginPath();ctx.arc(x(i),y(v),2.5,0,2*Math.PI);ctx.fillStyle=s.color;ctx.fill();});}
 ctx.fillStyle='#526879';const step=Math.max(1,Math.ceil(axis.length/8));for(let i=0;i<axis.length;i+=step)ctx.fillText(String(axis[i]),x(i)-10,h-15);
 let offset=p;for(const s of series){ctx.fillStyle=s.color;ctx.fillText(s.name,offset,16);offset+=ctx.measureText(s.name).width+22;}
}
function matrix(l){
 const c=$('correlation'),ctx=c.getContext('2d'),n=l.correlation.length,p=29,cell=(c.width-2*p)/n;
 ctx.clearRect(0,0,c.width,c.height);ctx.font='10px system-ui';ctx.textAlign='center';
 for(let i=0;i<n;i++){ctx.fillStyle='#526879';ctx.fillText(i+1,p+(i+.5)*cell,p-7);ctx.fillText(i+1,p-13,p+(i+.6)*cell);for(let j=0;j<n;j++){const v=l.correlation[i][j];const delta=v===null?0:v-l.fair_correlation;const a=Math.min(1,Math.abs(delta));ctx.fillStyle=v===null?'#e3e7ea':delta>=0?'rgba(25,79,119,'+(.08+.9*a)+')':'rgba(174,81,38,'+(.08+.9*a)+')';ctx.fillRect(p+j*cell,p+i*cell,cell-.5,cell-.5);}}
}
function model(){
 if(!data)return;const l=data.laboratorio,d=l.distributions[$('lab-model').value];if(!d)return;
 chart('performance',[{name:'Exceso de aciertos',values:d.running,color:'#194f77'}],l.draws,true);
 const n=l.draws.length;chart('distribution',[{name:'Observado',values:d.counts.map(x=>x/n),color:'#194f77'},{name:'Azar teórico',values:l.theory,color:'#b38231'}],l.theory.map((_,i)=>i));
}
const keys=['historica','reciente_25','exponencial','momentum','rezago'];
for(const k of keys){const label=document.createElement('label');label.textContent=labels[k];const input=document.createElement('input');input.type='number';input.min='-5';input.max='5';input.step='.1';input.value='1';input.id='weight-'+k;label.append(input);$('weights').append(label);}
document.addEventListener('chile-reset',()=>{data=null;$('lab').hidden=true;$('sim-result').textContent='';});
document.addEventListener('chile-analysis',e=>{
 data=e.detail;const l=data.laboratorio;$('lab').hidden=false;
 $('lab-model').replaceChildren(...Object.keys(l.distributions).map(k=>{const o=document.createElement('option');o.value=k;o.textContent=labels[k]||k;return o;}));$('lab-model').value=data.estrategia;model();matrix(l);
 $('corr-note').textContent='Correlación esperada entre bolillas distintas bajo un sorteo justo: '+f(l.fair_correlation)+'. Azul: por encima; naranja: por debajo. La diagonal no se interpreta.';
 const g=l.geometry;$('geometry').textContent='Cuadrícula de '+g.grid_columns+' columnas. Adyacencias ortogonales promedio: '+f(g.mean.adjacent)+'; último sorteo: '+g.last.adjacent+'. Suma media: '+f(g.mean.sum)+'; impares medios: '+f(g.mean.odd)+'.';
 chart('autocorrelation',[{name:'Autocorrelación media',values:l.cycles.autocorrelation.map(x=>x.mean),color:'#194f77'}],l.cycles.autocorrelation.map(x=>x.lag),true);
 chart('spectrum',[{name:'Potencia media',values:l.cycles.spectrum.map(x=>x.power),color:'#194f77'}],l.cycles.spectrum.map((_,i)=>i+1));
 $('hedge').replaceChildren(...Object.entries(l.hedge_weights).map(([k,v])=>{const s=document.createElement('span');s.textContent=(labels[k]||k)+': '+(100*v).toFixed(1)+'%';return s;}));
});
$('lab-model').onchange=model;
$('simulate').onclick=async()=>{
 const game=$('game').value;const button=$('simulate');button.disabled=true;
 try{const weights=Object.fromEntries(keys.map(k=>[k,Number($('weight-'+k).value)]));const r=await fetch('/chile-api/simulate',{method:'POST',headers:{'Content-Type':'application/json','X-Chile-Token':token},body:JSON.stringify({game,weights})});const d=await r.json();if(!r.ok)throw Error(d.error);if(game===$('game').value)$('sim-result').textContent='Media '+f(d.mean)+' frente a '+f(d.expected)+' aleatoria, '+d.n+' sorteos. '+d.warning;}catch(e){$('sim-result').textContent=e.message;}finally{button.disabled=false;}
};
})();