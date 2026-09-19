import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createControl, decode, ControlError, visibleError, bounded } from '../apps/desktop/src/control.ts';
const ok = result => ({ok:true,result});
const fail = (code='rejected',acceptance='rejected') => ({ok:false,error:{code,acceptance,message:'Bearer PRIVATE proof=PRIVATE'}});
const response = (body,status=200) => ({status,json:async()=>body});
for(const native of [false,true]) {
 test((native?'native':'browser')+' success and explicit rejection parity',async()=>{
  let value=ok({id:'event',state:'saved'});
  const call=createControl(native?async()=>value:undefined,async()=>response(value));
  assert.equal((await call('object',{})).id,'event');
  value=fail(); await assert.rejects(call('object',{}),e=>e instanceof ControlError && e.enqueueRejected && !e.message.includes('PRIVATE'));
  value=fail('unavailable','uncertain'); await assert.rejects(call('object',{}),e=>!e.enqueueRejected);
 });
 test((native?'native':'browser')+' hanging request bounded without retry; late success ignored',async()=>{
  let calls=0, resolve;
  const hang=()=>{calls++;return new Promise(r=>resolve=r);};
  const call=createControl(native?hang:undefined,native?undefined:hang,15);
  await assert.rejects(call('object',{}),e=>e.code==='timeout' && e.acceptance==='uncertain');
  resolve(native?ok({id:'late'}):response(ok({id:'late'})));await new Promise(r=>setTimeout(r,5));assert.equal(calls,1);
 });
 test((native?'native':'browser')+' thrown credentials never become diagnostics',async()=>{
  const bad=async()=>{throw Error('https://user:PRIVATE@host Bearer PRIVATE');};
  await assert.rejects(createControl(native?bad:undefined,bad)('pause',{paused:true}), e=>!visibleError(e).includes('PRIVATE'));
 });
}
test('HTTP status checked even for a success-looking body',async()=>{
 await assert.rejects(createControl(undefined,async()=>response(ok({}),503))('pause',{paused:true}),e=>e.code==='invalid_response'&&e.acceptance==='uncertain');
});
test('body read is bounded and aborts fetch',async()=>{
 let signal;
 const call=createControl(undefined,async(_,options)=>{signal=options.signal;return {status:200,json:()=>new Promise(()=>{})};},15);
 await assert.rejects(call('snapshot',{}),e=>e.code==='timeout');assert.equal(signal.aborted,true);
});
for(const value of [null,{}, {error:'PRIVATE'},ok(null),fail('PRIVATE'),{ok:false,error:{code:'rejected',acceptance:'yes'}},ok({state:'surprise'})]) test('malformed response fails closed '+JSON.stringify(value),()=>{
 assert.throws(()=>decode('outbox-status',value), e=>e.code==='invalid_response'&&!e.enqueueRejected&&!e.message.includes('PRIVATE'));
});
test('snapshot operational health is data, not a transport failure',()=>{
 const snapshot={configured:true,online:true,activeRoom:'general',error:'delivery needs attention',health:[{scope:'delivery'}],rooms:[],events:[],sessions:[],bindings:[],receipts:[],objects:[],outbox:[],devices:[],pairing:[]};
 assert.equal(decode('snapshot',ok(snapshot)),snapshot);
 assert.throws(()=>decode('snapshot',ok({...snapshot,events:null})),ControlError);
});
test('unexpected callbacks get safe visible text',()=>{assert.match(visibleError(Error('PRIVATE')),/Unexpected action failure/);});
test('synchronous callback throws are caught by bound',async()=>{await assert.rejects(bounded(()=>{throw Error('synthetic');}),/synthetic/);});
