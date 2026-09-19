// Synthetic control responses only. No helper process, profile, or credentials.
// Requires Playwright (PLAYWRIGHT_MODULE may point to an existing installation)
// and Chrome; run with Node >=22.18. The test owns an isolated Vite process.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = fileURLToPath(new URL('../apps/desktop/', import.meta.url));
const base = 'http://127.0.0.1:1433';
let server, browser;
before(async () => {
  server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '1433'], {
    cwd: root, env: {...process.env, AGENT_ROOM_READY: '/nonexistent/b4-synthetic-only/ready.json'}, stdio: 'pipe',
  });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Vite startup timed out')), 15000);
    server.once('exit', code => { clearTimeout(timer); reject(Error('Vite exited: ' + code)); });
    server.stdout.on('data', chunk => { if (chunk.toString().includes(base)) { clearTimeout(timer); resolve(); } });
  });
  browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome', headless: true});
});
after(async () => { await browser?.close(); server?.kill(); });
const fixture = {
  configured:true, mode:'host', name:'Synthetic room', device:'device',
  room:'general', activeRoom:'general', rooms:[{id:'general',title:'General'},{id:'other',title:'Other'}],
  online:true, paused:false, events:[], sessions:[], bindings:[], objects:[], receipts:[], outbox:[], devices:[], pairing:[], requests:[],
};
const respond = (route, value) => route.fulfill({contentType:'application/json', body:JSON.stringify(value)});
async function waitFor(page, selector, text) {
  await page.waitForFunction(({selector, text}) => document.querySelector(selector)?.textContent.includes(text), {selector, text});
}
async function pageWith(handler) {
  const page = await browser.newPage(); page.setDefaultTimeout(8000);
  await page.route('**/control', route => handler(route, route.request().postDataJSON()));
  await page.goto(base); return page;
}
const review={id:'review',kind:'review',version:3,author:'author',data:{artifact:'patch',revision:'r1',base:'b1',reviewer:'reviewer',verdict:'approved',checks:'passed',findings:['keep']}};
async function setup(object=review,extra=()=>false){
 const requests=[];
 const page=await pageWith((route,req)=>{
  requests.push(req);if(extra(route,req))return;
  if(req.action==='snapshot')return respond(route,{...fixture,objects:object?[object]:[]});
  return respond(route,req.action==='outbox-status'?{state:'sent'}:{});
 });
 await page.getByLabel('Message',{exact:true}).waitFor();
 if(object){
  await page.locator('.sidebar').getByRole('button',{name:/Search/}).click();
  const title=object.data.artifact||object.data.title||object.data.scope;
  await page.locator('.palette input').fill(title);
  await page.locator('.palette').getByRole('button',{name:new RegExp(title)}).click();
 }else await page.getByRole('button',{name:'Request a review'}).click();
 return {page,requests};
}
for(const field of [null,'artifact','revision','base'])test('review identity change: '+field,async()=>{
 const {page,requests}=await setup();try{
  assert.equal(await page.locator('select[name=owner]').isDisabled(),true);
  await page.getByLabel('Checks and test evidence').fill('more');
  if(field)await page.locator('[name='+field+']').fill('changed');
  await page.getByRole('button',{name:'Save review',exact:true}).click();
  await page.locator('dialog').waitFor({state:'detached'});
  const saved=requests.find(r=>r.action==='object').data;
  assert.equal(saved.data.reviewer,'reviewer');assert.equal(saved.version,4);
  assert.equal(saved.data.verdict,field?'pending':'approved');assert.deepEqual(saved.data.findings,field?'':['keep']);
 }finally{await page.close();}
});
test('empty room opens review with editable new assignment',async()=>{
 const {page}=await setup(null);try{assert.equal(await page.locator('dialog select').first().inputValue(),'review');assert.equal(await page.locator('select[name=owner]').isEnabled(),true);}finally{await page.close();}
});
test('resolved work requires evidence and retains unavailable owner',async()=>{
 const {page,requests}=await setup({id:'work',kind:'work',version:1,author:'a',data:{title:'Task',owner:'missing',state:'working'}});try{
  assert.equal(await page.locator('select[name=owner]').isDisabled(),true);
  await page.locator('select[name=state]').selectOption('resolved');
  await page.getByRole('button',{name:'Save work',exact:true}).click();
  assert.equal(requests.filter(r=>r.action==='object').length,0);
  assert.equal(await page.getByLabel('Completion evidence').evaluate(e=>e.validity.valueMissing),true);
  await page.getByLabel('Completion evidence').fill('Tests pass');
  await page.getByRole('button',{name:'Save work',exact:true}).click();await page.locator('dialog').waitFor({state:'detached'});
  assert.equal(requests.find(r=>r.action==='object').data.data.owner,'missing');
 }finally{await page.close();}
});
test('claim read-only',async()=>{
 const {page,requests}=await setup({id:'claim',kind:'claim',version:1,author:'agent',data:{scope:'repo-claim',expires:2000000000,conflicts:['other']}});try{
 assert.match(await page.locator('dialog').innerText(),/read-only/);assert.match(await page.locator('dialog').innerText(),/repo-claim/);assert.equal(await page.locator('dialog form').count(),0);assert.equal(requests.filter(r=>r.action==='object').length,0);
 }finally{await page.close();}
});
for(const outcome of ['rejected','lost','generic','failed','cancelled'])test('save '+outcome,async()=>{
 let count=0;
 const {page,requests}=await setup(review,(route,req)=>{
  if(req.action==='object'&&++count===1){
   if(outcome==='lost'){void route.abort();return true;}
   if(['rejected','generic'].includes(outcome)){void respond(route,{error:'synthetic rejection',...(outcome==='rejected'?{acceptance:'rejected'}:{})});return true;}
  }
  if(req.action==='outbox-status'&&count===1&&['failed','cancelled'].includes(outcome)){void respond(route,{state:outcome,reason:'terminal failure'});return true;}
 });try{
  await page.getByRole('button',{name:'Save review',exact:true}).click();await page.locator('dialog [role=alert]').waitFor();
  const uncertain=['lost','generic'].includes(outcome);
  assert.equal(await page.getByLabel('Artifact',{exact:true}).isDisabled(),uncertain);
  if(!uncertain)await page.getByLabel('Checks and test evidence').fill('corrected');
  await page.getByRole('button',{name:uncertain?'Check save status':'Save review',exact:true}).click();await page.locator('dialog').waitFor({state:'detached'});
  const sent=requests.filter(r=>r.action==='object').map(r=>r.data);assert.equal(sent.length,2);
  if(uncertain)assert.deepEqual(sent[1],sent[0]);else{assert.notEqual(sent[1].event_id,sent[0].event_id);assert.equal(sent[1].data.checks,'corrected');}
 }finally{await page.close();}
});
for(const state of ['saved','unknown'])test('nonterminal status stays locked: '+state,async()=>{
 let settle=false;
 const {page,requests}=await setup(review,(route,req)=>{
  if(req.action==='outbox-status'){void respond(route,{state:settle?'sent':state});return true;}
 });try{
  await page.getByRole('button',{name:'Save review',exact:true}).click();
  await page.locator('dialog [role=alert]').waitFor({timeout:18000});
  assert.equal(await page.getByLabel('Artifact',{exact:true}).isDisabled(),true);
  settle=true;await page.getByRole('button',{name:'Check save status',exact:true}).click();
  await page.locator('dialog').waitFor({state:'detached'});
  const sent=requests.filter(r=>r.action==='object');assert.deepEqual(sent[0].data,sent[1].data);
 }finally{await page.close();}
});
