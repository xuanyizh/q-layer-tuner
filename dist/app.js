import {PythonClient} from './python-client.js';
const client=new PythonClient();
let defaults={},ready=false,generation=0;
const $=id=>document.getElementById(id);
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=(v,d=2)=>Number.isFinite(v)?v.toFixed(d):'—';
const signed=(v,d=2)=>(Math.abs(v)<0.5*Math.pow(10,-d)?0:v)>=0?'+'+number(Math.abs(v)<0.5*Math.pow(10,-d)?0:v,d):number(v,d);
let lastResult=null,lastError=null,timer;
function setFields(s){
  for(const key of Object.keys(defaults)){if($(key))$(key).value=s[key]??'';}
}
function readFields(){
  const s={};
  for(const [key,value] of Object.entries(defaults)){
    const text=$(key).value.trim();
    s[key]=value===null?(text===''?null:Number(text)):typeof value==='number'?(text===''?NaN:Number(text)):text;
  }
  return s;
}
function formula(c){return `In<sub>${number(c.In,3)}</sub>Ga<sub>${number(c.Ga,3)}</sub>As<sub>${number(c.As,3)}</sub>P<sub>${number(c.P,3)}</sub>`;}
function sourceCard(name,item,s,error){
  const key=name==='In'?'inStep':name==='Ga'?'gaStep':'asStep';
  const unit=name==='As'?'LV':'°C';
  return `<article class="source-card ${name==='As'?'as':''}"><div class="source-header"><strong>${name==='As'?'As valve':name+' cell'}</strong><span>${name==='As'?'PROVISIONAL':'RATE-ANCHORED'}</span></div><div class="source-values">${item?`<div class="full-value">${number(item.full,2)}<small>${unit}</small></div><div class="delta">${signed(item.full-item.current,2)} from ${number(item.current,1)}</div>`:`<div class="blocked">${esc(error||'Conversion unavailable')}</div>`}</div><div class="applied-row"><span>Applied setting</span><strong>${item?number(item.applied,2):'—'}</strong></div><div class="step-control"><span>${s[key]}% of the full change</span></div></article>`;
}
function chart(r){
  if(!r.prediction||r.trajectory.length<2)return '<p class="micro">A valid As conversion is needed for the modeled correction path.</p>';
  const points=[r.current,r.target,r.prediction,...r.trajectory];
  let xmin=Math.min(...points.map(p=>p.mismatch)),xmax=Math.max(...points.map(p=>p.mismatch));
  let ymin=Math.min(...points.map(p=>p.pl)),ymax=Math.max(...points.map(p=>p.pl));
  const dx=Math.max(xmax-xmin,40),dy=Math.max(ymax-ymin,2);
  xmin-=dx*.17;xmax+=dx*.17;ymin-=dy*.23;ymax+=dy*.23;
  const W=670,H=250,L=62,R=18,T=22,B=49;
  const X=x=>L+(x-xmin)/(xmax-xmin)*(W-L-R),Y=y=>H-B-(y-ymin)/(ymax-ymin)*(H-B-T);
  let grid='';
  for(let i=0;i<=4;i++){
    const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;
    grid+=`<line x1="${X(x)}" x2="${X(x)}" y1="${T}" y2="${H-B}" stroke="#edf1f5"/><text x="${X(x)}" y="${H-B+21}" text-anchor="middle" fill="#73869b" font-size="12">${number(x,0)}</text><line x1="${L}" x2="${W-R}" y1="${Y(y)}" y2="${Y(y)}" stroke="#edf1f5"/><text x="${L-9}" y="${Y(y)+4}" text-anchor="end" fill="#73869b" font-size="12">${number(y,1)}</text>`;
  }
  const path=r.trajectory.map((p,i)=>`${i?'L':'M'}${X(p.mismatch)},${Y(p.pl)}`).join(' ');
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Predicted PL versus XRD correction path. Current ${number(r.current.pl,2)} nm at ${number(r.current.mismatch,1)} arcsec; applied ${number(r.prediction.pl,2)} nm at ${number(r.prediction.mismatch,1)} arcsec; target ${number(r.target.pl,2)} nm at ${number(r.target.mismatch,1)} arcsec."><text x="${L}" y="12" font-size="12" fill="#5c7289">PL (nm)</text>${grid}<line x1="${X(r.target.mismatch)}" x2="${X(r.target.mismatch)}" y1="${T}" y2="${H-B}" stroke="#75b5aa" stroke-dasharray="4 4"/><line x1="${L}" x2="${W-R}" y1="${Y(r.target.pl)}" y2="${Y(r.target.pl)}" stroke="#75b5aa" stroke-dasharray="4 4"/><path d="${path}" fill="none" stroke="#93a9c1" stroke-width="2.5"/><circle cx="${X(r.target.mismatch)}" cy="${Y(r.target.pl)}" r="6" fill="#188b7d" stroke="white" stroke-width="2"/><circle cx="${X(r.current.mismatch)}" cy="${Y(r.current.pl)}" r="6" fill="#587bb0" stroke="white" stroke-width="2"/><circle cx="${X(r.prediction.mismatch)}" cy="${Y(r.prediction.pl)}" r="6" fill="#d18b36" stroke="white" stroke-width="2"/><text x="${(L+W-R)/2}" y="${H-5}" font-size="12" text-anchor="middle" fill="#5c7289">Reported XRD separation (arcsec)</text></svg><div class="chart-caption"><span class="chart-legend"><span>Current</span><span class="target">Target</span><span class="applied">Applied</span></span><span>Line: all controls advanced together to 100%</span></div>`;
}
function render(r){
  const s=r.inputs;
  $('loading').hidden=true;$('error').hidden=true;$('results').hidden=false;
  $('ratio-display').textContent=`Normalized target: In ${number(r.target.In*100,2)}% · Ga ${number(r.target.Ga*100,2)}%`;
  $('target-formula').innerHTML=formula(r.target);
  $('summary-pl').innerHTML=`${number(s.targetPL,1)} <small>nm</small>`;
  $('summary-rate').innerHTML=`${number(s.targetRate,4)} <small>III units</small>`;
  $('summary-anchor').innerHTML=`${signed(r.offset*1000,2)} <small>meV</small>`;
  $('source-cards').innerHTML=['In','Ga','As'].map(n=>sourceCard(n,r.settings[n],s,r.asError)).join('');
  const p=r.prediction;
  const metric=(label,value,unit,target)=>`<div class="metric"><span class="metric-label">${label}</span><strong>${value}<small>${unit}</small></strong><span class="metric-target">target ${target}</span></div>`;
  $('prediction-metrics').innerHTML=metric('PL peak',p?number(p.pl,2):'—','nm',number(s.targetPL,1))+metric('XRD separation',p?signed(p.mismatch,1):'—','arcsec',number(r.target.mismatch,1))+metric('Total III rate',p?number(p.rate,4):'—','',number(s.targetRate,4));
  $('trajectory-chart').innerHTML=chart(r);
  const row=(label,current,target,sigma='')=>`<tr><td>${label}</td><td>${current}${sigma?` <span class="small">± ${sigma}</span>`:''}</td><td>${target}</td></tr>`;
  let rows=['In','Ga','As','P'].map(n=>row(`${n} fraction`,number(r.current[n],4),number(r.target[n],4),r.uncertainty?number(['In','Ga'].includes(n)?r.uncertainty.ga:r.uncertainty.as,4):'')).join('');
  rows+=row('In incorporated rate',number(r.rates.In.current,4),number(r.rates.In.target,4))+row('Ga incorporated rate',number(r.rates.Ga.current,4),number(r.rates.Ga.target,4))+row('Total III rate',number(r.total,4),number(s.targetRate,4));
  $('composition-table').innerHTML=`<table class="composition-table"><thead><tr><th>Quantity</th><th>Current / 1σ</th><th>Target</th></tr></thead><tbody>${rows}</tbody></table>`;
  $('inference-note').textContent=`Known ${s.knownElement} rate: ${number(s.knownRate,4)}. Current in-plane strain: ${signed(r.current.parallel*100,4)}%. Uncertainty propagates current PL/XRD errors only; the reference and calibrations are treated as exact.`;
  $('notices').innerHTML=[...r.notices,...(r.asError?[r.asError]:[])].map(n=>`<div class="notice">${esc(n)}</div>`).join('');
  $('nominal-rates').textContent=`Unanchored source-curve outputs: In ${number(r.nominalRates.In,4)}, Ga ${number(r.nominalRates.Ga,4)} (original units unverified). Corrections use the known/inferred rates.`;
  $('mode-display').textContent=`Bandgap strain: ${s.opticalStrain==='on'?'ON — hydrostatic + HH/LH corrections':'OFF — bulk estimate'} · Coherent XRD elasticity: ON`;
  const pressure=v=>Number.isFinite(v)?(v*1e6).toFixed(6):'—';
  const ab=r.bep.As,pb=r.bep.P;
  $('bep-table').innerHTML=`<table class="composition-table"><thead><tr><th>BEP (10⁻⁶ Torr)</th><th>Current</th><th>Full / fixed</th><th>Applied</th></tr></thead><tbody><tr><td>As</td><td>${pressure(ab.current)}</td><td>${pressure(ab.fullRequested)}</td><td>${pressure(ab.applied)}</td></tr><tr><td>P · held fixed</td><td>${pressure(pb.current)}</td><td>${pressure(pb.full)}</td><td>${pressure(pb.applied)}</td></tr></tbody></table><p class="micro">${pb.valve==null?'P valve is not recorded; stable P supply is assumed.':`P valve ${number(pb.valve,2)} is held fixed.`} ${pb.error?esc(pb.error):''} BEP values are not atomic incorporation fractions.</p>`;
  $('calibration-plots').innerHTML=['As','P'].map(n=>calibrationChart(n,r.calibrations[n])).join('');
  $('calc-status').textContent=client.mode==='local'?'Updated · Python on your computer':'Updated · Python in this browser';
}
function showError(error){
  lastResult=null;lastError=error.message;$('loading').hidden=true;$('results').hidden=true;$('error').hidden=false;
  $('error').innerHTML=`<strong>Check the inputs</strong>${esc(error.message)}`;
  $('calc-status').textContent='No recommendation shown for invalid inputs';
}
async function run(){
  clearTimeout(timer);if(!ready)return null;
  const id=++generation;
  $('calc-status').textContent='Calculating…';$('calculate').disabled=true;
  $('results').hidden=true;$('loading').hidden=false;$('loading').textContent='Calculating source adjustments…';
  try{
    const r=await client.request({action:'calculate',settings:readFields()});
    if(id!==generation)return null;
    lastResult=r;lastError=null;render(r);return r;
  }catch(e){if(id===generation)showError(e);return null;}
  finally{if(id===generation)$('calculate').disabled=false;}
}
function calibrationChart(name,c){
  if(c.error)return `<p class="notice">${esc(name+': '+c.error)}</p>`;
  const W=530,H=235,L=55,R=18,T=25,B=40;
  const [lo,hi]=c.range,max=Math.max(...c.curve.map(p=>p.bep),...c.measurements.map(p=>p.bep))*1.1;
  const X=v=>L+(v-lo)/(hi-lo)*(W-L-R),Y=v=>H-B-v/max*(H-B-T);
  let grid='';
  for(let i=0;i<5;i++){const val=max*i/4;grid+=`<line x1="${L}" x2="${W-R}" y1="${Y(val)}" y2="${Y(val)}" stroke="#e6edf2"/><text x="${L-7}" y="${Y(val)+4}" text-anchor="end" fill="#52657b" font-size="12">${number(val*1e6,1)}</text>`;}
  const path=c.curve.map((p,i)=>`${i?'L':'M'}${X(p.valve)},${Y(p.bep)}`).join(' ');
  return `<div><h3>${name} · valve ${lo}–${hi}</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${name} measured BEP and fitted fifth-degree curve"><text x="${L}" y="14" font-size="12" fill="#52657b">BEP (10⁻⁶ Torr)</text>${grid}<path d="${path}" fill="none" stroke="#127c75" stroke-width="2.5"/>${c.measurements.map(p=>`<circle cx="${X(p.valve)}" cy="${Y(p.bep)}" r="4" fill="white" stroke="#127c75" stroke-width="1.5"/>`).join('')}<text x="${L}" y="${H-15}" font-size="12">${lo}</text><text x="${W-R}" y="${H-15}" text-anchor="end" font-size="12">${hi}</text><text x="${W/2}" y="${H-8}" text-anchor="middle" font-size="12">Valve setting</text></svg><p class="micro">R² ${number(c.rSquared,7)} · maximum measured-point residual ${number(c.maxRelativePercent,2)}%. Residuals are not uncertainty bounds.</p></div>`;
}
async function convert(){
  if(!ready)return;
  const text=$('convert-value').value.trim();
  if(!text){$('convert-result').textContent='Enter a value to convert.';return;}
  const direction=$('convert-direction').value;
  const value=Number(text)*(direction==='bep_to_valve'?1e-6:1);
  $('convert-button').disabled=true;
  try{
    const r=await client.request({action:'convert_bep',source:$('convert-source').value,direction,value,settings:readFields()});
    $('convert-result').textContent=`${r.source}: valve ${number(r.valve,4)} ↔ ${(r.bepTorr*1e6).toFixed(6)} × 10⁻⁶ Torr`;
  }catch(e){$('convert-result').textContent=e.message;}
  finally{$('convert-button').disabled=false;}
}
function activateTab(name){
  for(const n of ['recipe','calibration']){
    $(`tab-${n}`).setAttribute('aria-selected',String(n===name));$(`tab-${n}`).tabIndex=n===name?0:-1;$(`${n}-fields`).hidden=n!==name;
  }
}
for(const n of ['recipe','calibration']){
  $(`tab-${n}`).addEventListener('click',()=>activateTab(n));
  $(`tab-${n}`).addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'recipe':e.key==='End'?'calibration':n==='recipe'?'calibration':'recipe';activateTab(next);$(`tab-${next}`).focus();}});
}
$('recipe-form').addEventListener('submit',e=>{e.preventDefault();return run();});
$('recipe-form').addEventListener('input',e=>{if(e.target.id.startsWith('convert-'))return;generation++;lastResult=null;clearTimeout(timer);$('results').hidden=true;$('loading').hidden=false;$('loading').textContent='Updating calculations…';$('calc-status').textContent='Updating…';timer=setTimeout(run,350);});
$('recipe-form').addEventListener('change',e=>{if(!e.target.id.startsWith('convert-'))return run();});
$('convert-button').addEventListener('click',convert);
$('convert-direction').addEventListener('change',()=>{$('convert-label').textContent=$('convert-direction').value==='bep_to_valve'?'BEP (10⁻⁶ Torr)':'Valve setting';$('convert-result').textContent='Enter a value in the selected units and convert.';});
$('convert-source').addEventListener('change',()=>{$('convert-result').textContent='Enter a value and convert.';});
$('reset').addEventListener('click',()=>{setFields(defaults);activateTab('recipe');return run();});
function concise(r){return {target:r.target,current:r.current,totalCurrentRate:r.total,sourceSettings:r.settings,appliedPrediction:r.prediction,asModel:'measured_fifth_degree_BEP_fit_and_provisional_incorporation_response',opticalStrain:r.inputs.opticalStrain,bep:r.bep,asError:r.asError,notices:r.notices};}
function registerTools(){
  const context=document.modelContext;if(!context?.registerTool)return;
  const properties=Object.fromEntries(Object.entries(defaults).map(([k,v])=>[k,{type:v===null?['number','null']:typeof v==='number'?'number':'string'}]));
  for(const [key,values] of Object.entries({axis:['theta','two_theta'],sign:['film_minus_substrate','substrate_minus_film'],knownElement:['In','Ga'],opticalStrain:['off','on']}))properties[key].enum=values;
  const controller=new AbortController();window.addEventListener('pagehide',()=>controller.abort(),{once:true});
  const tools=[{name:'calculate_q_layer_recipe',title:'Calculate Q-layer recipe',description:'Update visible recipe inputs and calculate corrections using Python. Does not control source hardware.',inputSchema:{type:'object',properties,additionalProperties:false},annotations:{readOnlyHint:false},async execute(input){
    if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!Object.hasOwn(defaults,k)))throw new Error('Supply supported recipe inputs.');
    const next={...readFields(),...input};const id=++generation;
    const r=await client.request({action:'calculate',settings:next});
    if(id!==generation)throw new Error('Inputs changed during calculation; please retry.');
    clearTimeout(timer);setFields(next);lastResult=r;lastError=null;render(r);$('calculate').disabled=false;return concise(r);
  }},{name:'get_q_layer_result',title:'Read Q-layer result',description:'Read the current visible result without changing inputs.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute(){return lastResult?concise(lastResult):{error:lastError||'Not ready'};}}];
  for(const tool of tools){try{Promise.resolve(context.registerTool(tool,{signal:controller.signal})).catch(()=>{});}catch{}}
}
try{
  const metadata=await client.initialize();defaults=metadata.defaults;
  for(const n of ['As','P']){
    const prefix=n.toLowerCase();
    $(prefix+'-coefficients').innerHTML=[5,4,3,2,1,0].map(j=>`<label>a${j}<input id="${prefix}C${j}" name="${prefix}C${j}" type="number" step="any"></label>`).join('');
  }
  setFields(defaults);ready=true;$('calculate').disabled=false;
  await run();registerTools();
}catch(e){showError(e);$('error').insertAdjacentHTML('beforeend','<p class="micro">Reload the page, or run the included local Python launcher.</p>');}
