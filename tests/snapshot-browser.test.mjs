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
const base = 'http://127.0.0.1:1431';
let server, browser;
before(async () => {
  server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '1431'], {
    cwd: root, env: {...process.env, AGENT_ROOM_READY: '/nonexistent/b2-synthetic-only/ready.json'}, stdio: 'pipe',
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
for (const configured of [true, false]) {
  test('cold helper failure never shows setup; recovery configured=' + configured, async () => {
    let available = false;
    const page = await pageWith(route => respond(route, available ? {...fixture, configured} : {error:'Local helper unavailable'}));
    try {
      await waitFor(page, 'main', 'Local helper unavailable');
      assert.equal(await page.getByRole('heading', {name:'Set up Agent Room'}).count(), 0);
      await page.getByRole('button', {name:'Dismiss error'}).click();
      assert.match(await page.locator('.quiet-status').innerText(), /Local helper unavailable/);
      assert.equal(await page.getByRole('heading', {name:'Set up Agent Room'}).count(), 0);
      available = true; // normal interval must recover without a reload or retry click
      if (configured) {
        await waitFor(page, '.device-label', 'Synthetic room');
        assert.equal(await page.getByRole('heading', {name:'Set up Agent Room'}).count(), 0);
        await waitFor(page, '.quiet-status', 'Room hub connected');
      } else await page.getByRole('heading', {name:'Set up Agent Room'}).waitFor();
      assert.equal(await page.getByRole('heading', {name:'Local helper unavailable'}).count(), 0);
    } finally { await page.close(); }
  });
}
for (const outcome of ['success', 'failure']) {
test('post-action refresh supersedes held poll; stale ' + outcome + ' cannot undo recovery', async () => {
  let count = 0, held;
  const page = await pageWith((route, {action}) => {
    if (action !== 'snapshot') return respond(route, {});
    count++;
    if (count === 2) { held = route; return; }
    return respond(route, {...fixture, name:count === 1 ? 'INITIAL' : 'NEWER'});
  });
  try {
    await waitFor(page, '.device-label', 'INITIAL');
    while (!held) await page.waitForTimeout(20);
    await page.getByRole('button', {name:'Pause delivery', exact:true}).click();
    await waitFor(page, '.device-label', 'NEWER');
    await respond(held, outcome === 'failure' ? {error:'delayed old failure'} : {...fixture, name:'OLDER', online:false});
    await page.waitForTimeout(100);
    assert.match(await page.locator('.device-label').innerText(), /NEWER/);
    assert.match(await page.locator('.quiet-status').innerText(), /Room hub connected/);
    assert.equal(await page.getByRole('alert').count(), 0);
  } finally { await page.close(); }
});
}
for (const action of ['room-select', 'room-create']) {
  test(action + ' rejects a delayed older-room snapshot', async () => {
    let count = 0, held, room = 'general';
    const page = await pageWith((route, request) => {
      if (request.action === action) { room = 'other'; return respond(route, {room, id:room}); }
      if (request.action !== 'snapshot') return respond(route, {});
      count++;
      if (count === 2) { held = route; return; }
      return respond(route, {...fixture, activeRoom:room, room, name:room === 'other' ? 'NEW ROOM' : 'INITIAL'});
    });
    try {
      await waitFor(page, '.device-label', 'INITIAL');
      while (!held) await page.waitForTimeout(20);
      if (action === 'room-select') await page.locator('.sidebar').getByRole('button', {name:'Other', exact:true}).click();
      else {
        await page.locator('.sidebar').getByRole('button', {name:'New room', exact:true}).click();
        await page.getByLabel('Room name', {exact:true}).fill('Other');
        await page.locator('dialog').getByRole('button', {name:'Create room', exact:true}).click();
      }
      await waitFor(page, '.device-label', 'NEW ROOM');
      await respond(held, {...fixture, name:'OLDER ROOM'});
      await page.waitForTimeout(100);
      assert.match(await page.locator('.device-label').innerText(), /NEW ROOM/);
      assert.match(await page.locator('.breadcrumb').innerText(), /Other/);
      assert.match(await page.locator('.quiet-status').innerText(), /Room hub connected/);
    } finally { await page.close(); }
  });
}
