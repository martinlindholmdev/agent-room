import {test} from 'node:test';
import assert from 'node:assert/strict';
import {submitExisting,incoming} from '../adapters/agent-room-desktop/opencode-client.mjs';
test('existing exact native ID and directory; HTTP 204 only submits',async()=>{
  let request;
  const client={session:{promptAsync:async(data)=>{request=data;return {response:{status:204}};}}};
  assert.equal(await submitExisting(client,'/fixture/work','ses_exact','Synthetic'), 'submitted');
  assert.deepEqual(request,{path:{id:'ses_exact'},query:{directory:'/fixture/work'},body:{parts:[{type:'text',text:'Synthetic'}]}});
});
test('lost response is uncertain and is attempted once',async()=>{
  let attempts=0;
  const client={session:{promptAsync:async()=>{attempts++;throw Error('host secret must not escape');}}};
  assert.equal(await submitExisting(client,'/fixture','ses_a','Synthetic'),'uncertain');
  assert.equal(attempts,1);
});
test('auth failure unavailable, unexpected response uncertain',async()=>{
  for(const [status,state] of [[401,'unavailable'],[403,'unavailable'],[404,'unavailable'],[500,'uncertain'],[200,'uncertain']]){
    assert.equal(await submitExisting({session:{promptAsync:async()=>({response:{status}})}},'/fixture','ses_a','Synthetic'),state);
  }
});
test('prompt requires explicit acknowledgement and correlated reply',()=>{
  const prompt=incoming({id:'delivery-1'},{from_session:'sender-exact',id:'message-1',text:'Synthetic'});
  assert.match(prompt,/desktop_room_ack/);assert.match(prompt,/sender-exact/);assert.match(prompt,/message-1/);
});
