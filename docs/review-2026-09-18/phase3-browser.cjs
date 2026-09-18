// Review harness only. Uses a disposable Chrome profile and an isolated helper.
// Run from repository root with Node on PATH. No credentials are printed.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || '/Users/irislindholm/.local/share/opencode/integrations/playwright/node_modules/playwright');
const fs=require('fs');
const path=require('path');
const home=path.resolve(process.env.REVIEW_HOME || 'work/phase3-test');
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
await test('01 first-run',async()=>{
 const before=await page.locator('main').innerText();
 if(!(await snap()).configured){await btn('Create a room').click();await dialog().getByLabel('Device name').fill('Phase 3 review');await dialog().getByRole('button',{name:'Create room'}).click();await wait();}
 return {before,after:(await page.locator('main').innerText()).slice(0,1800)};
});
await test('02 empty-room-review',async()=>{await btn('Request a review').click();const result={title:await dialog().getByRole('heading').innerText(),type:await dialog().locator('select').first().inputValue()};await page.keyboard.press('Escape');return result;});
await test('03 create-room',async()=>{await btn('New room').click();await dialog().getByLabel('Room name').fill('Browser journeys');await dialog().getByRole('button',{name:'Create room'}).click();await wait();return {room:(await snap()).activeRoom};});
await test('04 connect-manually',async()=>{await btn('Connect agent').click();await dialog().getByLabel('Agent app').selectOption('mcp');await dialog().getByLabel('Conversation title').fill('Browser reviewer');await dialog().getByLabel('Exact native session ID').fill('phase3-browser-reviewer');await dialog().getByRole('button',{name:'Connect conversation'}).click();await wait();const text=await dialog().innerText();await btn('Done').click();return {setup:text};});
await test('05 approve-decline-requests',async()=>{
 await api('request-create',{native:'phase3-approve',app:'pull',title:'Approve fixture'});await api('request-create',{native:'phase3-decline',app:'mcp',title:'Decline fixture'});await wait();await page.locator('.sidebar').getByRole('button',{name:/^Inbox/}).click();
 await page.locator('.request').filter({hasText:'Approve fixture'}).getByRole('button',{name:'Approve',exact:true}).click();await wait();
 await page.locator('.request').filter({hasText:'Decline fixture'}).getByRole('button',{name:'Decline',exact:true}).click();await wait();const s=await snap();return {pending:s.requests.length,bindingTitles:s.bindings.map(b=>b.title),rooms:s.bindings.map(b=>b.room)};
});
await page.locator('.sidebar').getByRole('button',{name:/Browser journeys/}).click();
await test('06 enter-shift-enter-reply',async()=>{
 const field=page.getByRole('textbox',{name:'Message',exact:true});await field.fill('Browser first line');await field.press('Shift+Enter');await field.type('second line');const before=await field.inputValue();await field.press('Enter');await wait();
 const message=page.locator('article.message').filter({hasText:'Browser first line'}).first();await message.getByRole('button',{name:'Reply',exact:true}).click();await field.fill('Browser reply');await btn('Send message').click();await wait();
 return {draft:before,replySource:await page.locator('.reply-source').allTextContents(),draftCleared:await field.inputValue()};
});
await test('07 long-code-many-scroll',async()=>{
 for(let i=0;i<25;i++)await api('send',{text:'Scroll fixture '+i+' '+('long text '.repeat(i===10?300:1))});
 await api('send',{text:'Code fixture\n'+String.fromCharCode(96).repeat(3)+'js\nconst x = 1;\n'+String.fromCharCode(96).repeat(3)});await wait();
 return {messages:await page.locator('article.message').count(),codeElements:await page.locator('.message-text pre,.message-text code').count(),layout:await page.locator('.conversation').evaluate(el=>({height:el.clientHeight,scroll:el.scrollHeight,top:el.scrollTop,width:el.clientWidth,contentWidth:el.scrollWidth})),unreadMarkers:await page.getByText(/unread/i).count()};
});
await test('08 recipient-survives-switch',async()=>{
 const s=await snap();const b=s.bindings.find(b=>b.native==='phase3-browser-reviewer');await page.getByLabel('Message recipient').selectOption(b.id);await page.getByRole('textbox',{name:'Message',exact:true}).fill('Unsent cross-room draft');await page.locator('.sidebar').getByRole('button',{name:/^General/}).click();await wait();
 const result={draft:await page.getByRole('textbox',{name:'Message',exact:true}).inputValue(),recipient:await page.getByLabel('Message recipient').inputValue(),note:await page.locator('.target-health').allTextContents(),room:(await snap()).activeRoom};
 await page.locator('.sidebar').getByRole('button',{name:/Browser journeys/}).click();await wait();await page.getByRole('textbox',{name:'Message',exact:true}).fill('');await page.getByLabel('Message recipient').selectOption('');return result;
});
await test('09 plan-work-decision-review',async()=>{
 await page.locator('.sidebar').getByRole('button',{name:/Plans & work/}).click();
 await btn('Plan').click();await dialog().getByLabel('Objective').fill('Browser plan');await dialog().getByLabel('Next steps',{exact:false}).fill('Step one\nStep two');await btn('Save plan').click();await wait();
 await btn('Work request').click();await dialog().getByLabel('Request',{exact:true}).fill('Browser work');await dialog().locator('select[name=owner]').selectOption({index:1});await btn('Save work').click();await wait();
 await btn('Decision').click();await dialog().getByLabel('Decision',{exact:true}).fill('Browser decision');await dialog().getByLabel('Status').selectOption('accepted');await btn('Save decision').click();await wait();
 await btn('Review').click();await dialog().getByLabel('Artifact',{exact:true}).fill('browser-artifact');await dialog().getByLabel('Exact revision').fill('v1');await dialog().getByLabel('Base revision').fill('v0');await dialog().locator('select[name=owner]').selectOption({index:1});await btn('Save review').click();await wait();
 await page.locator('.object-card').filter({hasText:'Browser work'}).click();await dialog().getByLabel('Status').selectOption('resolved');await btn('Save work').click();await wait();const s=await snap();return {objects:s.objects.map(o=>({kind:o.kind,state:o.data.state,verdict:o.data.verdict})),failed:s.outbox.filter(o=>o.state==='failed').map(o=>o.error),dialogClosed:await dialog().count()===0};
});
await test('10 inbox-counts',async()=>{await page.locator('.sidebar').getByRole('button',{name:/^Inbox/}).click();return {sidebar:await page.locator('.sidebar').innerText(),inbox:(await page.locator('main').innerText()).slice(0,3000)};});
await test('11 settings-theme-reload-backup',async()=>{
 await page.locator('.sidebar').getByRole('button',{name:'Settings',exact:true}).click();await btn('Dark').click();await page.reload();await wait();const dark=await page.locator('html').getAttribute('data-theme');await page.locator('.sidebar').getByRole('button',{name:'Settings',exact:true}).click();await btn('Light').click();const light=await page.locator('html').getAttribute('data-theme');await btn('Pause delivery').last().click();await wait();await page.reload();await wait();const paused=(await snap()).paused;await page.locator('.sidebar').getByRole('button',{name:'Settings',exact:true}).click();await btn('Resume delivery').last().click();await btn('Create a consistent backup').click();await wait();const banner=await page.getByRole('alert').innerText();await btn('Dismiss error').click();return {dark,light,pausedPersisted:paused,backupSuccessInAlert:banner.startsWith('Backup saved:')};
});
await test('12 quiet-remove-reconnect',async()=>{
 const before=(await snap()).bindings.find(b=>b.native==='phase3-browser-reviewer');await api('binding-state',{binding:before.id,state:'working'});await wait();await page.waitForTimeout(32000);const stateAfter=(await snap()).bindings.find(b=>b.id===before.id).state;
 const row=page.locator('.settings-row').filter({hasText:'Browser reviewer'});await row.getByRole('button',{name:'Remove',exact:true}).click();await btn('Remove connection').click();await wait();const removed=!(await snap()).bindings.some(b=>b.id===before.id);
 await btn('Connect a conversation').click();await dialog().getByLabel('Agent app').selectOption('mcp');await dialog().getByLabel('Conversation title').fill('Browser reviewer');await dialog().getByLabel('Exact native session ID').fill('phase3-browser-reviewer');await btn('Connect conversation').click();await wait();await btn('Done').click();const after=(await snap()).bindings.find(b=>b.native===before.native);return {quietForSeconds:32,stateAfter,removed,newIdentity:after.id!==before.id};
});
await test('13 all-static-palette-commands',async()=>{
 const labels=['Go to room','Go to inbox','Go to plans & work','Settings · connections and device','Message the room…','New work request','New shared plan','New review packet','Record a decision','Connect a conversation'];const results=[];
 for(const label of labels){await page.locator('.sidebar').getByRole('button',{name:/^Search/}).click();await page.getByLabel('Command palette').fill(label);await page.locator('.palette-item').filter({hasText:label}).first().click();await page.waitForTimeout(150);results.push({label,dialog:await dialog().getByRole('heading').allTextContents(),type:await dialog().locator('select').first().inputValue().catch(()=>null),focus:await page.evaluate(()=>document.activeElement?.getAttribute('aria-label'))});if(await dialog().count())await page.keyboard.press('Escape');}return results;
});
await test('14 keyboard-narrow-theme',async()=>{
 await page.locator('.sidebar').getByRole('button',{name:/Browser journeys/}).click();await btn('New room').click();const focused=await page.evaluate(()=>document.activeElement?.getAttribute('name'));await page.keyboard.press('Tab');const next=await page.evaluate(()=>document.activeElement?.textContent);await page.keyboard.press('Escape');const closed=await dialog().count()===0;
 await page.setViewportSize({width:600,height:800});await page.waitForTimeout(200);const size=await page.evaluate(()=>({viewport:innerWidth,body:document.body.scrollWidth,main:document.querySelector('main').getBoundingClientRect().width}));await page.screenshot({path:'docs/review-2026-09-18/phase3-narrow.png',fullPage:true});await page.setViewportSize({width:1440,height:1000});return {focused,next,closed,size};
});
await test('15 refused-action',async()=>{await btn('Connect agent').click();await dialog().getByLabel('Conversation title').fill('Invalid Codex');await dialog().getByLabel('Exact native session ID').fill('not-a-uuid');await btn('Connect conversation').click();await wait();const r={error:await page.getByRole('alert').innerText(),dialogStillOpen:await dialog().count()>0};await page.keyboard.press('Escape');await btn('Dismiss error').click();return r;});
await test('16 slow-send',async()=>{slow=true;await page.getByRole('textbox',{name:'Message',exact:true}).fill('Delayed test message');await btn('Send message').click();await page.waitForTimeout(300);const disabled=await page.getByRole('textbox',{name:'Message',exact:true}).isDisabled();await page.waitForTimeout(5000);slow=false;return {disabledWhileWaiting:disabled,draftAfter:await page.getByRole('textbox',{name:'Message',exact:true}).inputValue()};});
await test('17 helper-unavailable-simulated',async()=>{fault='Local helper unavailable';await wait();const banner=await page.getByRole('alert').innerText();const status=await page.locator('.quiet-status').innerText();await btn('Dismiss error').click();await wait();const reappeared=await page.getByRole('alert').count()>0;await page.getByRole('textbox',{name:'Message',exact:true}).fill('Offline draft');await btn('Send message').click();await page.waitForTimeout(300);const retained=await page.getByRole('textbox',{name:'Message',exact:true}).inputValue();fault='';await wait();return {banner,status,reappeared,retained};});
console.log(JSON.stringify({browserErrors:errors}));await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
