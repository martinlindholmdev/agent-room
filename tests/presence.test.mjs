import {test} from 'node:test';
import assert from 'node:assert/strict';
import {presenceText} from '../apps/desktop/src/presence.ts';
const now=2000000000000;
for(const state of ['working','idle','blocked','done']) test(state+' stays a report after contact expires',()=>{
 const b={state,state_reported_at:now/1000-3600,last_contact_at:now/1000-299};
 const fresh=presenceText(b,now), stale=presenceText(b,now+1000);
 assert.match(fresh.contact,/^Recent contact/);
 assert.match(stale.contact,/^No recent contact/);
 assert.equal(stale.work,fresh.work);
});
test('unknown/legacy/future timestamps do not claim freshness',()=>{
 assert.equal(presenceText(undefined,now).work,'Work state not reported');
 assert.equal(presenceText({state:'working'},now).work,'Last reported: Working · report time unknown');
 for(const last_contact_at of [undefined,NaN,0,now/1000+1]) assert.equal(presenceText({last_contact_at},now).contact,'Contact unknown');
});
