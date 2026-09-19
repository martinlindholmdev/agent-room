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
const base = 'http://127.0.0.1:1432';
let server, browser;
before(async () => {
  server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '1432'], {
    cwd: root, env: {...process.env, AGENT_ROOM_READY: '/nonexistent/b3-synthetic-only/ready.json'}, stdio: 'pipe',
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
const respond = (route, value) => route.fulfill({contentType:'application/json', body:JSON.stringify(value.error && !('configured' in value) ? {ok:false,error:{code:value.acceptance === 'rejected' ? 'rejected' : 'unavailable',acceptance:value.acceptance || 'uncertain'}} : {ok:true,result:value})});
async function waitFor(page, selector, text) {
  await page.waitForFunction(({selector, text}) => document.querySelector(selector)?.textContent.includes(text), {selector, text});
}
async function pageWith(handler) {
  const page = await browser.newPage(); page.setDefaultTimeout(8000);
  await page.route('**/control', route => handler(route, route.request().postDataJSON()));
  await page.goto(base); return page;
}
const agent = room => ({id:'agent-'+room, title:'Agent '+room, app:'mcp', active:1, device:'device',device_name:'Synthetic',room});
const message = room => ({id:'message-'+room,kind:'message',sender:'agent-'+room,device:'device',created:1,seq:1,body:{text:'Hello '+room}});
async function roomPage(extra = () => false) {
  let room = 'general';
  const requests = [];
  const page = await pageWith((route, req) => {
    requests.push(req);
    if (extra(route, req)) return;
    if (req.action === 'room-select') {room = req.data.room; return respond(route,{room});}
    if (req.action === 'snapshot') return respond(route,{...fixture, room, activeRoom:room, sessions:[agent(room)],events:[message(room)]});
    return respond(route,{id:'synthetic',state:'saved'});
  });
  await page.getByLabel('Message', {exact:true}).waitFor();
  return {page, requests};
}
async function switchRoom(page, title) {
  await page.locator('.sidebar').getByRole('button',{name:title,exact:true}).click();
  await waitFor(page,'.breadcrumb',title);
  await page.waitForFunction(() => !document.querySelector('textarea').disabled);
}
async function reply(page, text) {
  await page.getByRole('button',{name:'Reply',exact:true}).click();
  await page.getByLabel('Message',{exact:true}).fill(text);
}
test('round-trip retains independent room drafts, targets and replies; send payload stays in its room', async () => {
  const {page,requests} = await roomPage();
  try {
    await reply(page,'draft A');
    await switchRoom(page,'Other');
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'');
    assert.equal(await page.getByLabel('Message recipient').inputValue(),'');
    assert.equal(await page.locator('.replying').count(),0);
    await reply(page,'draft B');
    await switchRoom(page,'General');
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'draft A');
    assert.equal(await page.getByLabel('Message recipient').inputValue(),'agent-general');
    assert.match(await page.locator('.replying').innerText(),/Hello general/);
    await page.getByRole('button',{name:'Cancel reply'}).click();
    await switchRoom(page,'Other');
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'draft B');
    assert.equal(await page.getByLabel('Message recipient').inputValue(),'agent-other');
    assert.match(await page.locator('.replying').innerText(),/Hello other/);
    await page.getByRole('button',{name:'Send message'}).click();
    await page.waitForFunction(() => document.querySelector('textarea').value === '');
    const sent = requests.find(r => r.action === 'send').data;
    assert.equal(sent.text,'draft B'); assert.deepEqual(sent.targets,['agent-other']); assert.equal(sent.reply_to,'message-other');
    await switchRoom(page,'General');
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'draft A');
    assert.equal(await page.locator('.replying').count(),0);
  } finally {await page.close();}
});
for (const outcome of ['success','failure']) test('old room-create '+outcome+' cannot close a reopened dialog of the same kind', async () => {
  let held;
  const {page} = await roomPage((route,req) => {if(req.action === 'room-create') {held=route; return true;}});
  try {
    await page.getByRole('button',{name:'New room',exact:true}).click();
    await page.getByLabel('Room name',{exact:true}).fill('Old request');
    await page.locator('dialog').getByRole('button',{name:'Create room'}).click();
    while (!held) await page.waitForTimeout(10);
    await page.locator('dialog').getByRole('button',{name:'Close dialog',exact:true}).click();
    await page.getByRole('button',{name:'New room',exact:true}).click();
    await page.getByLabel('Room name',{exact:true}).fill('New draft');
    await respond(held,outcome === 'success' ? {id:'general'} : {error:'synthetic rejection'});
    await page.waitForFunction(() => !document.querySelector('dialog .primary').disabled);
    assert.equal(await page.getByLabel('Room name',{exact:true}).inputValue(),'New draft');
    assert.equal(await page.locator('dialog').count(),1);
  } finally {await page.close();}
});
test('overlapping actions keep composer busy until both settle, including failure', async () => {
  const held=[];
  const {page} = await roomPage((route,req) => {if(req.action === 'pause') {held.push(route);return true;}});
  try {
    const pause = page.getByRole('button',{name:'Pause delivery',exact:true});
    await pause.click(); await pause.click();
    while(held.length < 2) await page.waitForTimeout(10);
    assert.equal(await page.getByLabel('Message',{exact:true}).isDisabled(),true);
    await respond(held[0],{}); await page.waitForTimeout(100);
    assert.equal(await page.getByLabel('Message',{exact:true}).isDisabled(),true);
    await respond(held[1],{error:'second action failed'});
    await page.waitForFunction(() => !document.querySelector('textarea').disabled);
  } finally {await page.close();}
});
test('held send blocks room mutation; failure retains draft for retry', async () => {
  let held;
  const {page,requests} = await roomPage((route,req) => {if(req.action==='send'){held=route;return true;}});
  try {
    await reply(page,'keep me');
    await page.getByRole('button',{name:'Send message'}).click();
    while(!held) await page.waitForTimeout(10);
    await page.locator('.sidebar').getByRole('button',{name:'Other',exact:true}).click();
    await page.waitForTimeout(100);
    assert.equal(requests.filter(r=>r.action==='room-select').length,0);
    await respond(held,{error:'send rejected'});
    await page.waitForFunction(() => !document.querySelector('textarea').disabled);
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'keep me');
    await switchRoom(page,'Other');
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'');
  } finally {await page.close();}
});
test('palette recipient is room-scoped; Escape clears only the current room reply', async () => {
  const {page} = await roomPage();
  try {
    await reply(page,'A');
    await switchRoom(page,'Other');
    await page.locator('.sidebar').getByRole('button',{name:/Search/}).click();
    await page.locator('.palette input').fill('Agent other');
    await page.locator('.palette').getByRole('button',{name:/^Agent other MCP/}).click();
    assert.equal(await page.getByLabel('Message recipient').inputValue(),'agent-other');
    await reply(page,'B');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.replying').count(),0);
    await switchRoom(page,'General');
    assert.match(await page.locator('.replying').innerText(),/Hello general/);
    assert.equal(await page.getByLabel('Message recipient').inputValue(),'agent-general');
    await switchRoom(page,'Other');
    assert.equal(await page.getByLabel('Message recipient').inputValue(),'agent-other');
    assert.equal(await page.locator('.replying').count(),0);
  } finally {await page.close();}
});
test('inactive retained recipient is explicit and cannot silently send to the board', async () => {
  let inactive = false;
  const {page,requests} = await roomPage((route,req) => {
    if(inactive && req.action==='snapshot') {void respond(route,{...fixture,events:[message('general')],sessions:[]}); return true;}
  });
  try {
    await reply(page,'do not misroute');
    inactive=true;
    await page.getByRole('button',{name:'Pause delivery',exact:true}).click();
    await page.getByRole('option',{name:'Unavailable recipient — choose another'}).waitFor({state:'attached'});
    await page.getByRole('button',{name:'Send message'}).click();
    await waitFor(page,'[role=alert]','Choose an active recipient');
    assert.equal(requests.filter(r=>r.action==='send').length,0);
    assert.equal(await page.getByLabel('Message',{exact:true}).inputValue(),'do not misroute');
  } finally {await page.close();}
});
test('late bind result cannot replace a newer dialog with connection setup', async () => {
  let held;
  const {page} = await roomPage((route,req) => {if(req.action==='bind'){held=route;return true;}});
  try {
    await page.getByRole('button',{name:'Connect agent',exact:true}).first().click();
    await page.getByLabel('Conversation title',{exact:true}).fill('Old connection');
    await page.getByLabel('Exact native session ID',{exact:true}).fill('synthetic-native');
    await page.locator('dialog').getByRole('button',{name:'Connect conversation'}).click();
    while(!held) await page.waitForTimeout(10);
    await page.locator('dialog').getByRole('button',{name:'Close dialog'}).click();
    await page.getByRole('button',{name:'New room',exact:true}).click();
    await page.getByLabel('Room name',{exact:true}).fill('Keep this');
    await respond(held,{id:'synthetic-binding',title:'Old connection',app:'mcp',native:'synthetic-native'});
    await page.waitForFunction(() => !document.querySelector('dialog .primary').disabled);
    assert.equal(await page.getByLabel('Room name',{exact:true}).inputValue(),'Keep this');
  } finally {await page.close();}
});

// B6 scoped errors and operational health.
test('B6 concurrent failures persist independently through later success', async () => {
 const held=[]; let fail=true;
 const {page}=await roomPage((route,req)=>{if(req.action==='pause'&&fail){held.push(route);return true;}});
 try {
  await page.getByRole('button',{name:'Pause delivery',exact:true}).click();
  await page.getByRole('button',{name:'Pause delivery',exact:true}).click();
  while(held.length<2)await page.waitForTimeout(10);
  await respond(held[0],{error:'PRIVATE'});await respond(held[1],{error:'PRIVATE'});
  await page.waitForFunction(()=>document.querySelectorAll('.error-banner').length===2);
  fail=false;await page.getByRole('button',{name:'Pause delivery',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('textarea').disabled);
  assert.equal(await page.locator('.error-banner').count(),2);
  assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE/);
  await page.getByRole('button',{name:'Dismiss action error'}).first().click();
  assert.equal(await page.locator('.error-banner').count(),1);
 }finally{await page.close();}
});
test('B6 current form errors are visible inside modal, not leaked raw exceptions',async()=>{
 const {page}=await roomPage((route,req)=>{if(req.action==='room-create'){void respond(route,{error:'PRIVATE'});return true;}});
 try{
  await page.getByRole('button',{name:'New room',exact:true}).click();await page.getByLabel('Room name',{exact:true}).fill('Draft');
  await page.locator('dialog').getByRole('button',{name:'Create room'}).click();await page.locator('dialog [role=alert]').waitFor();
  assert.match(await page.locator('dialog [role=alert]').innerText(),/room-create.*General/);
  assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE/);
 }finally{await page.close();}
});
test('B6 unexpected post-send callback failure is visible without raw text',async()=>{
 const {page}=await roomPage();try{
  await page.getByLabel('Message',{exact:true}).fill('Message');
  await page.getByLabel('Message',{exact:true}).evaluate(e=>{e.focus=()=>{throw Error('PRIVATE');};});
  await page.getByRole('button',{name:'Send message'}).click();await page.locator('.error-banner').waitFor();
  assert.match(await page.locator('.error-banner').innerText(),/Unexpected action failure/);
  assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE/);
 }finally{await page.close();}
});
test('B6 delivery health remains visible through polling and clears on recovery',async()=>{
 let degraded=true;
 const {page}=await roomPage((route,req)=>{if(req.action==='snapshot'){void respond(route,{...fixture,error:'PRIVATE',health:degraded?[{scope:'delivery'}]:[]});return true;}});
 try{
  await page.locator('.error-banner').waitFor();assert.match(await page.locator('.error-banner').innerText(),/uncertain sends are not retried/);
  await page.waitForTimeout(2000);assert.equal(await page.locator('.error-banner').count(),1);
  assert.doesNotMatch(await page.locator('body').innerText(),/PRIVATE/);
  degraded=false;await page.locator('.error-banner').waitFor({state:'detached'});
 }finally{await page.close();}
});
