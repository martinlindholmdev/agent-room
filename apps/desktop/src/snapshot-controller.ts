/** Owns snapshot ordering, not action/dialog/draft state. */
export function createSnapshotController<T extends { activeRoom: string }>(
  read: () => Promise<T>,
  apply: (snapshot: T) => void,
  fail: (error: unknown) => void,
) {
  let generation = 0;
  let sequence = 0;
  const pending = new Set<number>();
  let active = true;
  let changingRoom = false;
  let expectedRoom: string | undefined;

  async function refresh(poll = false) {
    // Polls are single-flight. Explicit post-action refreshes may supersede them.
    if (!active || changingRoom || (poll && pending.has(sequence))) return;
    const request = ++sequence;
    const scope = generation;
    const current = () => active && scope === generation && request === sequence;
    pending.add(request);
    try {
      const next = await read();
      if (!current()) return;
      if (expectedRoom && next.activeRoom !== expectedRoom) {
        fail(new Error("Waiting for the selected room snapshot"));
        return;
      }
      apply(next);
    } catch (error) {
      if (current()) fail(error);
    } finally {
      pending.delete(request);
    }
  }

  return {
    refresh,
    start() { active = true; },
    stop() { active = false; generation++; sequence++; },
    async changeRoom<R>(change: () => Promise<R>, roomOf: (result: R) => string) {
      // The helper's selected room is global. Do not send concurrent mutations.
      if (changingRoom) throw new Error("A room change is already in progress");
      changingRoom = true;
      generation++;
      sequence++;
      expectedRoom = undefined;
      try {
        const result = await change();
        expectedRoom = roomOf(result);
        return result;
      } finally {
        changingRoom = false;
        // Also refresh after failure: the helper may have committed before a lost response.
        await refresh();
      }
    },
  };
}
