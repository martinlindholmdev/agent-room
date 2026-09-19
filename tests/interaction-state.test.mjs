import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createInteractionState } from '../apps/desktop/src/interaction-state.ts';
const fixture = () => createInteractionState(() => {});
test('rooms retain separate text, recipient, reply and id', () => {
  const s = fixture();
  s.patch('a', {text:'A', target:'agent-a', reply:{id:'reply-a'}});
  const a = s.draft('a');
  assert.deepEqual({...s.draft('b'), id:null}, {id:null,text:'',target:'',reply:null});
  s.patch('b', {text:'B', target:'agent-b', reply:{id:'reply-b'}});
  assert.deepEqual(s.draft('a'), a);
  assert.notEqual(s.draft('b').id, a.id);
});
test('every payload edit rotates id; send only clears its unchanged source draft', () => {
  const s = fixture();
  s.patch('a', {text:'A'});
  const old = s.draft('a').id;
  s.patch('a', {target:'agent'});
  assert.notEqual(s.draft('a').id, old);
  const targeted = s.draft('a').id;
  s.patch('a', {reply:{id:'reply'}});
  assert.notEqual(s.draft('a').id, targeted);
  s.sent('a', old);
  assert.equal(s.draft('a').text, 'A');
  s.patch('b', {text:'B'});
  const b = s.draft('b');
  s.sent('a', s.draft('a').id);
  assert.equal(s.draft('a').text, '');
  assert.equal(s.draft('a').reply, null);
  assert.equal(s.draft('a').target, 'agent');
  assert.deepEqual(s.draft('b'), b);
});
test('close/reopen even the same dialog invalidates old owners', () => {
  const s = fixture(), owner = s.openDialog();
  assert.equal(s.ownsDialog(owner), true);
  s.openDialog(); s.openDialog();
  assert.equal(s.ownsDialog(owner), false);
});
for (const reverse of [false, true]) test('overlapping completion order reverse=' + reverse, () => {
  const s = fixture(), a = s.begin(), b = s.begin();
  s.finish(reverse ? b : a);
  assert.equal(s.busy, true);
  s.finish(reverse ? b : a); // duplicate cleanup cannot decrement another action
  assert.equal(s.busy, true);
  s.finish(reverse ? a : b);
  assert.equal(s.busy, false);
});
test('room mutations cannot race actions in either direction; rejected begin does not clear busy', () => {
  const s = fixture(), a = s.begin();
  assert.throws(() => s.begin(true), /Wait/);
  assert.equal(s.busy, true);
  s.finish(a);
  const room = s.begin(true);
  assert.throws(() => s.begin(), /Wait/);
  assert.throws(() => s.begin(true), /Wait/);
  s.finish(room);
  assert.equal(s.busy, false);
  s.finish(s.begin());
});
