# B1 — Durable disconnect

2026-09-19. Scope: R01 only. No B2 snapshot-ordering/cold-start work, presence policy,
connector retirement, installed-app replacement or live-data access.

## Evidence and change

phase5-presence-leftovers.md and the unchanged phase5-probe.py demonstrated that an
injected offline removal deleted the local binding but left the hub session active
even after successful sync. The hub already supports idempotent soft deactivation.

- Add an additive pending_removals table. Commit the binding deletion and removal
  intent in one device transaction before attempting remote settlement.
- Disconnect local delivery/bridge bookkeeping immediately; recover interrupted
  delivery cleanup on restart. Do not delete cached or hub message events.
- Replay pending removals before binding registration on sync. Keep original room
  scope, even after a room switch. Remove intent only after a successful response;
  an already-inactive session response also completes settlement.
- Serialize registration, removal and explicit reconnection. Reconnection must first
  settle the previous removal, preventing a late removal retry from deactivating the
  reused identity. Self-report updates cannot reinsert a concurrently removed binding.
- Expose pending removal summaries in snapshots and Settings → Connections, separately
  from active local bindings. Explain offline completion and history retention in
  the confirmation dialog. Offline failures remain pending, not falsely confirmed.
- Preserve unsent content from removed senders as failed, rather than leaving an
  exception outside the send error handler that strands the item in sending state.

## Verification

New tests/test_durable_disconnect.py: eleven tests with MemoryVault and disposable
homes under work/. Covers offline recovery, restart before/after settlement, repeated
ID/native removal, online removal, reconnect ordering, lost response after hub commit,
original-room scope, retained unsent content, crash between intent commit and delivery
cleanup, additive table initialization, and an in-flight registration/removal race.
History checks compare complete hub event and local cache rows before and after.
Existing removal/receipt/ownership tests also remain passing.

Actual commands/results:

- python3 -m pytest tests -q: **198 passed in 25.60s**.
- In apps/desktop, node_modules/.bin/tsc --noEmit: **exit 0**.
- python3 docs/review-2026-09-18/phase5-probe.py:
  offline_remove=true, local_binding_gone=true, hub_session_still_active=0;
  online_remove_hub_active=0. Unchanged presence results are outside B1.
- git diff --check: no errors.

Limits: API/Python execution and TypeScript/source review, not a browser click,
installed-webview test, real remote-Mac outage or deployment. Test removal failures
are injected deterministically. Existing historical ghosts whose removal intent was
already lost by old code cannot be reconstructed by this fix. The additive table
keeps the existing schema version because it does not alter old columns; running an
older helper will not replay new pending intents until this helper resumes.

The first TypeScript invocation resolved to the environment's Goose Node wrapper,
which bootstrapped its Hermit/Node toolchain; the subsequent invocation also emitted
Hermit bootstrap output. Both exited 0. No Agent Room bundle was built or replaced.
