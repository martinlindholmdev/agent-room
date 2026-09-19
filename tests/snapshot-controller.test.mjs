import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createSnapshotController } from '../apps/desktop/src/snapshot-controller.ts';

const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function fixture() {
  const requests = [], applied = [], failures = [];
  const controller = createSnapshotController(() => {
    const request = deferred(); requests.push(request); return request.promise;
  }, value => applied.push(value), error => failures.push(String(error)));
  return { controller, requests, applied, failures };
}
const snapshot = (name, activeRoom = 'general') => ({ name, activeRoom });

test('older success cannot overwrite a newer success', async () => {
  const f = fixture(), old = f.controller.refresh(), fresh = f.controller.refresh();
  f.requests[1].resolve(snapshot('new')); await fresh;
  f.requests[0].resolve(snapshot('old')); await old;
  assert.deepEqual(f.applied, [snapshot('new')]);
});
test('older failure cannot mark a newer success unavailable', async () => {
  const f = fixture(), old = f.controller.refresh(), fresh = f.controller.refresh();
  f.requests[1].resolve(snapshot('new')); await fresh;
  f.requests[0].reject(Error('old failure')); await old;
  assert.deepEqual(f.failures, []);
});
test('older success cannot clear a newer failure; next poll recovers', async () => {
  const f = fixture(), old = f.controller.refresh(), fresh = f.controller.refresh();
  f.requests[1].reject(Error('helper down')); await fresh;
  f.requests[0].resolve(snapshot('old')); await old;
  assert.equal(f.applied.length, 0); assert.equal(f.failures.length, 1);
  const recovery = f.controller.refresh(true);
  f.requests[2].resolve(snapshot('recovered')); await recovery;
  assert.deepEqual(f.applied, [snapshot('recovered')]);
});
test('polls are single-flight but explicit refresh can supersede a held poll', async () => {
  const f = fixture(), old = f.controller.refresh(true);
  await f.controller.refresh(true); assert.equal(f.requests.length, 1);
  const fresh = f.controller.refresh(); assert.equal(f.requests.length, 2);
  f.requests[1].resolve(snapshot('new')); await fresh;
  f.requests[0].resolve(snapshot('old')); await old;
  assert.deepEqual(f.applied, [snapshot('new')]);
});
for (const outcome of ['success', 'failure']) {
  test('room transition invalidates held old-room ' + outcome + ' after settlement', async () => {
    const f = fixture(), old = f.controller.refresh(), mutation = deferred();
    const changing = f.controller.changeRoom(() => mutation.promise, result => result.room);
    await f.controller.refresh(true); await f.controller.refresh();
    assert.equal(f.requests.length, 1);
    await assert.rejects(f.controller.changeRoom(() => assert.fail('must not send'), r => r.room), /already in progress/);
    mutation.resolve({room:'other'}); await Promise.resolve();
    f.requests[1].resolve(snapshot('new room', 'other')); await changing;
    if (outcome === 'success') f.requests[0].resolve(snapshot('old room'));
    else f.requests[0].reject(Error('old-room failure'));
    await old;
    assert.deepEqual(f.applied, [snapshot('new room', 'other')]);
    assert.deepEqual(f.failures, []);
  });
}
test('room transition rejects old response while mutation is still pending', async () => {
  const f = fixture(), old = f.controller.refresh(), mutation = deferred();
  const changing = f.controller.changeRoom(() => mutation.promise, r => r.room);
  f.requests[0].resolve(snapshot('old room')); await old;
  assert.deepEqual(f.applied, []);
  mutation.resolve({room:'other'}); await Promise.resolve();
  f.requests[1].resolve(snapshot('new room', 'other')); await changing;
  assert.deepEqual(f.applied, [snapshot('new room', 'other')]);
});
test('snapshot from wrong room is rejected even from a current request', async () => {
  const f = fixture();
  const changing = f.controller.changeRoom(async () => ({id:'created'}), result => result.id);
  await Promise.resolve(); f.requests[0].resolve(snapshot('wrong')); await changing;
  assert.equal(f.applied.length, 0); assert.match(f.failures[0], /selected room/);
  const recovery = f.controller.refresh(); f.requests[1].resolve(snapshot('right', 'created')); await recovery;
  assert.deepEqual(f.applied, [snapshot('right', 'created')]);
});
test('failed room mutation refreshes authoritative state and releases the guard', async () => {
  const f = fixture(), mutation = deferred();
  const changing = f.controller.changeRoom(() => mutation.promise, r => r.room);
  const rejected = assert.rejects(changing, /lost response/);
  mutation.reject(Error('lost response')); await Promise.resolve();
  f.requests[0].resolve(snapshot('actually changed', 'other')); await rejected;
  assert.deepEqual(f.applied, [snapshot('actually changed', 'other')]);
  const next = f.controller.refresh(true); f.requests[1].resolve(snapshot('next', 'other')); await next;
});
test('superseded hung request does not block polling after a newer result', async () => {
  const f = fixture(), old = f.controller.refresh(true), fresh = f.controller.refresh();
  f.requests[1].resolve(snapshot('new')); await fresh;
  const poll = f.controller.refresh(true);
  assert.equal(f.requests.length, 3);
  f.requests[2].resolve(snapshot('latest')); await poll;
  f.requests[0].resolve(snapshot('old')); await old;
  assert.deepEqual(f.applied, [snapshot('new'), snapshot('latest')]);
});
test('cleanup invalidates pending responses even after effect restarts', async () => {
  const f = fixture(), old = f.controller.refresh();
  f.controller.stop(); await f.controller.refresh(); assert.equal(f.requests.length, 1);
  f.controller.start(); const fresh = f.controller.refresh();
  f.requests[0].resolve(snapshot('unmounted')); await old;
  f.requests[1].resolve(snapshot('remounted')); await fresh;
  assert.deepEqual(f.applied, [snapshot('remounted')]);
});
