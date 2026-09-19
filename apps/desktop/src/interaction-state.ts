/** In-memory room drafts and operation ownership; no helper/profile persistence. */
export function createInteractionState<Reply>(changed: () => void) {
  type Draft = { id: string; text: string; target: string; reply: Reply | null };
  const drafts = new Map<string, Draft>();
  const pending = new Map<symbol, boolean>();
  let dialog = 0;
  const state = {
    get busy() { return pending.size > 0; },
    get dialog() { return dialog; },
    openDialog() { dialog++; changed(); return dialog; },
    ownsDialog(owner: number) { return owner === dialog; },
    draft(room: string): Draft {
      if (!drafts.has(room)) drafts.set(room, { id: crypto.randomUUID(), text: '', target: '', reply: null });
      return drafts.get(room)!;
    },
    patch(room: string, patch: Partial<Omit<Draft, 'id'>>) {
      drafts.set(room, { ...state.draft(room), ...patch, id: crypto.randomUUID() });
      changed();
    },
    sent(room: string, id: string) {
      if (state.draft(room).id !== id) return;
      state.patch(room, { text: '', reply: null });
    },
    begin(roomChange = false) {
      // The helper chooses a global room at request execution time. Do not let
      // room mutations race queued actions, including a send not yet accepted.
      if ([...pending.values()].some(Boolean) || (roomChange && pending.size)) {
        throw Error('Wait for the current action before changing rooms or submitting another action');
      }
      const id = Symbol();
      pending.set(id, roomChange);
      changed();
      return id;
    },
    finish(id: symbol) { pending.delete(id); changed(); },
  };
  return state;
}
