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
async function harness(){
 const nodes=new Map(),registry=new Map();
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
 const document={getElementById:id=>{assert.ok(nodes.has(id),'Missing element '+id);return nodes.get(id)},modelContext:{registerTool(tool){registry.set(tool.name,tool)}}};
 await new AsyncFunction('document','window','PythonClient',app)(document,{addEventListener(){}},PythonClient);
 return {nodes,registry};
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
