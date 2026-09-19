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
const base = 'http://127.0.0.1:1434';
let server, browser;
before(async () => {
  server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '1434'], {
    cwd: root, env: {...process.env, AGENT_ROOM_READY: '/nonexistent/b5-synthetic-only/ready.json'}, stdio: 'pipe',
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

for (const app of ['mcp', 'pull', 'claude-channel', 'codex-queue']) test(app + ': independent reports/contact and retained connection', async () => {
  const now = 2000000000000;
  const binding = {id:'agent',native:'synthetic',app,title:'Quiet agent',room:'general',state:'working',state_reported_at:now/1000-3600,last_contact_at:now/1000-299};
  const session = {...binding,device:'device',device_name:'Test Mac',active:1};
  const page = await browser.newPage();
  try {
    await page.clock.install({time:now});
    await page.route('**/control', route => respond(route, {...fixture,bindings:[binding],sessions:[session],activeCount:1,rooms:[{id:'general',title:'General',rollup:{state:'working',needs:0}}]}));
    await page.goto(base);
    const participant = page.locator('.participant');
    await participant.getByText('Recent contact', {exact:false}).waitFor();
    assert.match(await participant.innerText(), /Last reported: Working/);
    assert.match(await participant.ariaSnapshot(), /Last reported: Working/);
    if (['mcp','pull'].includes(app)) assert.match(await participant.innerText(), /On demand · silence is expected/);
    // Age without a new snapshot/contact; threshold is inclusive at five minutes.
    await page.clock.runFor(1000);
    await participant.getByText('No recent contact', {exact:false}).waitFor();
    assert.match(await participant.innerText(), /Last reported: Working/);
    assert.match(await participant.ariaSnapshot(), /No recent contact/);
    assert.equal(await participant.count(), 1);
    await page.getByRole('button',{name:'Settings',exact:true}).click();
    await page.getByText('No recent contact', {exact:false}).first().waitFor();
    assert.equal(await page.getByRole('button',{name:'Remove',exact:true}).count(), 1);
  } finally { await page.close(); }
});
test('remote and unreported connections do not invent Idle or contact', async () => {
 const page = await pageWith(route => respond(route,{...fixture,sessions:[{id:'remote',app:'mcp',title:'Remote fixture',device:'other',device_name:'Other Mac',active:1}]}));
 try {
  const participant=page.locator('.participant');
  await participant.getByText('Contact unknown',{exact:true}).waitFor();
  assert.match(await participant.innerText(),/Work state not reported/);
  assert.doesNotMatch(await participant.innerText(),/Idle|Recent contact/);
 } finally {await page.close();}
});
