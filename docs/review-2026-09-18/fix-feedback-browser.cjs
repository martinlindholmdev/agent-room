// Review harness only. Uses a disposable Chrome profile and an isolated helper.
// Run from repository root with Node on PATH. No credentials are printed.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || '/Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/playwright');
const fs=require('fs');
const assert=require('node:assert/strict');
const path=require('path');
const home=path.resolve('work/fix-feedback');
const ready=JSON.parse(fs.readFileSync(path.join(home,'ready.json'),'utf8'));
async function api(action,data={}) {
 const r=await fetch('http://127.0.0.1:'+ready.port+'/control',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+ready.token},body:JSON.stringify({action,data})});
 return r.json();
}
(async()=>{
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
page.setDefaultTimeout(6000); let fault='',slow=false; const errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.route('**/control',async route=>{
 if(fault) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:fault})});
 const request=route.request().postDataJSON();
 if(slow && request.action==='send') await new Promise(r=>setTimeout(r,3000));
 const data=await api(request.action,request.data);
 await route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
});
const wait=()=>page.waitForTimeout(2200);
const btn=(name)=>page.getByRole('button',{name,exact:true});
const dialog=()=>page.locator('dialog[open]');
const snap=()=>api('snapshot');
async function test(name,fn){try{console.log(JSON.stringify({journey:name,result:await fn()}));}catch(e){console.log(JSON.stringify({journey:name,error:e.message.slice(0,900)}));await page.keyboard.press('Escape').catch(()=>{});}}
await page.goto('http://127.0.0.1:1420');await wait();
await page.locator('.sidebar').getByRole('button',{name:/Plans & work/}).click();await page.locator('.object-card').filter({hasText:'Browser work'}).click();await dialog().getByLabel('Status').selectOption('resolved');await dialog().getByLabel('Completion evidence').fill('');await btn('Save work').click();await page.waitForTimeout(3500);
console.log(JSON.stringify({failedSaveDialog:await dialog().count(),inlineError:await dialog().getByRole('alert').allTextContents(),editable:await dialog().getByLabel('Completion evidence').isEnabled()}));
assert.equal(await dialog().count(),1);
assert.equal(await dialog().getByLabel('Completion evidence').isEnabled(),true);
assert.match(await dialog().getByRole('alert').innerText(),/completion evidence/);
await dialog().getByLabel('Completion evidence').fill('Verified evidence');await btn('Save work').click();await page.waitForTimeout(3500);
console.log(JSON.stringify({successfulSaveClosed:await dialog().count()===0,workState:(await snap()).objects.find(o=>o.kind==='work').data.state,failedReceiptCount:(await snap()).outbox.filter(o=>o.event.kind==='receipt'&&o.state==='failed').length}));
assert.equal(await dialog().count(),0);
assert.equal((await snap()).objects.find(o=>o.kind==='work').data.state,'resolved');
assert.equal((await snap()).outbox.filter(o=>o.event.kind==='receipt'&&o.state==='failed').length,0);
fault='Local helper unavailable';await wait();console.log(JSON.stringify({offlineStatus:await page.locator('.quiet-status').innerText(),notice:await page.locator('.notice').innerText()}));assert.match(await page.locator('.quiet-status').innerText(),/Local helper unavailable/);fault='';await wait();console.log(JSON.stringify({recoveredStatus:await page.locator('.quiet-status').innerText()}));await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
