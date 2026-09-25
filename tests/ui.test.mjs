// DOM wiring harness; Python requests execute the canonical native core.
// This is not a real-browser screenshot test.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const html=readFileSync(new URL('../dist/index.html',import.meta.url),'utf8');
const app=readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace(/^import .*?;\n/,'');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
class PythonClient {
  constructor(){this.mode='local';}
  async initialize(){return this.request({action:'metadata'});}
  async request(payload){
    const code="import sys,json\nfrom qlayer.engine import dispatch\ntry:\n print(json.dumps({'result':dispatch(json.load(sys.stdin))}))\nexcept Exception as e:\n print(json.dumps({'error':str(e)}))";
    const body=JSON.parse(execFileSync('python',['-c',code],{cwd:root,input:JSON.stringify(payload),encoding:'utf8'}));
    if(body.error)throw new Error(body.error);
    return body.result;
  }
}
async function harness(options={}){
 const nodes=new Map(),registry=new Map(),downloads=[];
 function add(markup){
  for(const match of markup.matchAll(/<[^>]+\bid="([^"]+)"[^>]*>/g)){
   assert.ok(!nodes.has(match[1]),'Duplicate element '+match[1]);
   const listeners=new Map();let fieldValue=match[0].match(/\bvalue="([^"]*)"/)?.[1]||'',inner='';
   nodes.set(match[1],{id:match[1],get value(){return fieldValue},set value(v){fieldValue=String(v)},hidden:/\bhidden\b/.test(match[0]),disabled:false,textContent:'',attrs:{},listeners,
    get innerHTML(){return inner},set innerHTML(v){inner=v;add(v)},
    addEventListener(n,f){listeners.set(n,f)},setAttribute(k,v){this.attrs[k]=v},focus(){},insertAdjacentHTML(_p,v){inner+=v;add(v)},
    dispatch(n,target=this){return listeners.get(n)?.({preventDefault(){},target})}
   });
  }
 }
 add(html);
 nodes.get('convert-source').value='As';nodes.get('convert-direction').value='valve_to_bep';
 const document={body:{appendChild(){}},createElement(){return {click(){downloads.push({url:this.href,name:this.download})},remove(){}}},getElementById:id=>{assert.ok(nodes.has(id),'Missing element '+id);return nodes.get(id)},modelContext:{registerTool(tool){registry.set(tool.name,tool)}}};
 class HarnessClient extends PythonClient {async request(payload){const result=await super.request(payload);if(payload.action==='fit_calibration'&&options.pauseFit)await options.pauseFit();if(payload.action==='convert_bep'&&options.pauseConversion)await options.pauseConversion();return result;}}
 await new AsyncFunction('document','window','PythonClient',app)(document,{addEventListener(){}},HarnessClient);
 return {nodes,registry,downloads};
}
test('GUI initializes Python, toggles strain, edits coefficients and recovers from errors',async()=>{
 const {nodes:n}=await harness();
 assert.equal(n.get('results').hidden,false);assert.match(n.get('target-formula').innerHTML,/0.800/);
 assert.match(n.get('source-cards').innerHTML,/1000.30/);assert.match(n.get('source-cards').innerHTML,/101.19/);
 n.get('opticalStrain').value='on';await n.get('recipe-form').dispatch('change',n.get('opticalStrain'));
 assert.match(n.get('source-cards').innerHTML,/1000.70/);assert.match(n.get('mode-display').textContent,/ON/);
 n.get('tab-calibration').dispatch('click');assert.equal(n.get('calibration-fields').hidden,false);
 n.get('asC1').value='0.02';await n.get('recipe-form').dispatch('submit');assert.equal(n.get('results').hidden,false);
 n.get('targetRate').value='0';await n.get('recipe-form').dispatch('submit');assert.equal(n.get('results').hidden,true);assert.equal(n.get('error').hidden,false);
 await n.get('reset').dispatch('click');assert.equal(n.get('results').hidden,false);assert.equal(n.get('error').hidden,true);
 assert.equal(n.get('opticalStrain').value,'off');assert.equal(n.get('pValve').value,'');
 const metadata=await new PythonClient().initialize();
 for(const id of Object.keys(metadata.defaults))assert.ok(n.has(id),'Editable input '+id);
});
test('As/P converter uses Python and reports a bounded inverse',async()=>{
 const {nodes:n}=await harness();
 n.get('convert-source').value='P';n.get('convert-value').value='40';
 await n.get('convert-button').dispatch('click');assert.match(n.get('convert-result').textContent,/P: valve 40.0000/);
 n.get('convert-direction').value='bep_to_valve';n.get('convert-direction').dispatch('change');
 n.get('convert-value').value='16.7';await n.get('convert-button').dispatch('click');assert.match(n.get('convert-result').textContent,/16.700000/);
 n.get('convert-value').value='100';await n.get('convert-button').dispatch('click');assert.match(n.get('convert-result').textContent,/extrapolation/);
});
test('WebMCP applies valid changes, rejects invalid edits atomically and reads selected mode',async()=>{
 const {nodes:n,registry}=await harness();assert.equal(registry.size,2);
 const edit=registry.get('calculate_q_layer_recipe'),read=registry.get('get_q_layer_result');
 const r=await edit.execute({targetPL:1210,measuredPL:1210,mismatch:0,opticalStrain:'on',pValve:40});
 assert.equal(n.get('targetPL').value,'1210');assert.ok(Math.abs(r.target.pl-1210)<1e-8);
 assert.equal(read.execute().opticalStrain,'on');assert.equal(read.execute().bep.P.valve,40);
 await assert.rejects(edit.execute({targetRate:-1}));assert.equal(n.get('targetRate').value,'1');
 assert.ok(Math.abs(read.execute().target.pl-1210)<1e-8);
 await assert.rejects(edit.execute({unexpected:1}));
});
test('static wiring contains Python assets and no parallel JS scientific engine',()=>{
 for(const path of ['style.css','app.js','python-client.js','engine-worker.mjs','python/qlayer/engine.py'])
  assert.ok(readFileSync(new URL('../dist/'+path,import.meta.url)).length>0);
 for(const m of html.matchAll(/for="([^"]+)"/g))assert.ok(html.includes(`id="${m[1]}"`));
 assert.ok(!app.includes("'./engine.js'"));
 assert.ok(!html.includes('http://terminal.local'));
});

const linearText=Array.from({length:10},(_,i)=>{const v=40+20*i;return `${v}, ${(.25+.012*v)*1e-6}`}).join('\n');
const uploadedFile=(name,text)=>({name,size:text.length,text:async()=>text});
test('measured fit applies a new range; rejected fits retain it and reset recipe preserves it',async()=>{
 const {nodes:n,registry}=await harness();
 const field=n.get('cal-as-data');field.value=linearText;field.dispatch('input');
 assert.match(n.get('cal-as-status').textContent,/Unfitted draft/);
 await n.get('cal-as-fit').dispatch('click');
 assert.match(n.get('cal-as-status').textContent,/Applied As fit/);
 assert.equal(n.get('as-range').textContent,'40–220');
 const r=registry.get('get_q_layer_result').execute();
 assert.deepEqual(r.calibrations.As.range,[40,220]);
 const expected=(r.sourceSettings.As.current===100);
 assert.equal(expected,true);
 const curve=n.get('asC0').value,applied=n.get('source-cards').innerHTML;
 field.value='1, 1e-6';field.dispatch('input');await n.get('cal-as-fit').dispatch('click');
 assert.match(n.get('cal-as-status').textContent,/Not applied/);assert.equal(n.get('asC0').value,curve);
 assert.equal(n.get('source-cards').innerHTML,applied);
 field.value=Array.from({length:7},(_,i)=>`${10+i*10}, ${(100-i*10)*1e-6}`).join('\n');
 field.dispatch('input');await n.get('cal-as-fit').dispatch('click');
 assert.match(n.get('cal-as-status').textContent,/must increase/);assert.equal(n.get('asC0').value,curve);
 await n.get('reset').dispatch('click');assert.equal(n.get('asC0').value,curve);assert.equal(n.get('as-range').textContent,'40–220');
 n.get('convert-value').value='30';await n.get('convert-button').dispatch('click');assert.match(n.get('convert-result').textContent,/40–220/);
});
test('calibration JSON download and load preserve both fitted data and manual coefficients',async()=>{
 const {nodes:n,downloads}=await harness();
 n.get('cal-as-data').value=linearText;await n.get('cal-as-fit').dispatch('click');
 n.get('asC0').value='.5';n.get('recipe-form').dispatch('input',n.get('asC0'));await n.get('recipe-form').dispatch('submit');
 await n.get('cal-save').dispatch('click');assert.equal(downloads.length,1);
 const text=await (await fetch(downloads[0].url)).text(),profile=JSON.parse(text);
 assert.equal(profile.sources.As.raw_coefficients_ascending_microtorr[0],.5);
 assert.equal(profile.sources.As.measurements.length,10);
 await n.get('cal-as-reset').dispatch('click');assert.equal(n.get('as-range').textContent,'30–270');
 n.get('cal-load').files=[uploadedFile('saved.json',text)];await n.get('cal-load').dispatch('change');
 assert.equal(n.get('asC0').value,'0.5');assert.equal(n.get('as-range').textContent,'40–220');
 assert.match(n.get('cal-profile-status').textContent,/Both calibrations loaded/);
 profile.sources.P.valid_valve_range=[1,1000];n.get('cal-load').files=[uploadedFile('bad.json',JSON.stringify(profile))];
 await n.get('cal-load').dispatch('change');assert.match(n.get('cal-profile-status').textContent,/Not loaded/);
 assert.equal(n.get('asC0').value,'0.5');assert.equal(n.get('p-range').textContent,'optional · 5–80');
});
test('measurement text file and selected microtorr units feed Python independently of recipe validity',async()=>{
 const {nodes:n}=await harness();
 const text='Valve,BEP\n'+Array.from({length:8},(_,i)=>`${10+i*10}, ${1+i*.4}`).join('\n');
 n.get('cal-p-file').files=[uploadedFile('new-p.csv',text)];await n.get('cal-p-file').dispatch('change');
 assert.equal(n.get('cal-p-data').value,text);
 n.get('cal-p-unit').value='microtorr';n.get('cal-p-unit').dispatch('change');
 n.get('targetRate').value='0';await n.get('cal-p-fit').dispatch('click');
 assert.match(n.get('cal-p-status').textContent,/Applied P fit/);assert.equal(n.get('error').hidden,false);
 n.get('convert-source').value='P';n.get('convert-value').value='10';await n.get('convert-button').dispatch('click');
 assert.match(n.get('convert-result').textContent,/1.000000/);
});
test('editing draft while a fit is pending discards the stale fit',async()=>{
 let release,started;const gate=new Promise(resolve=>release=resolve),signal=new Promise(resolve=>started=resolve);
 const {nodes:n}=await harness({pauseFit:()=>{started();return gate}});
 const before=n.get('asC0').value;
 n.get('cal-as-data').value=linearText;const pending=n.get('cal-as-fit').dispatch('click');
 await signal;n.get('cal-as-data').value='40, 2e-6';n.get('cal-as-data').dispatch('input');
 release();await pending;
 assert.equal(n.get('asC0').value,before);assert.equal(n.get('as-range').textContent,'30–270');
 assert.match(n.get('cal-as-status').textContent,/Unfitted draft/);assert.equal(n.get('cal-as-fit').disabled,false);
});

test('pending conversion cannot display an old calibration result after refit',async()=>{
 let release,started;const gate=new Promise(resolve=>release=resolve),signal=new Promise(resolve=>started=resolve);
 const {nodes:n}=await harness({pauseConversion:()=>{started();return gate}});
 const pending=n.get('convert-button').dispatch('click');await signal;
 n.get('cal-as-data').value=linearText;await n.get('cal-as-fit').dispatch('click');
 release();await pending;assert.match(n.get('convert-result').textContent,/Calibration updated/);
});
