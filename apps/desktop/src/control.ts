/** Renderer control contract. No transport or server exception text is displayed. */
export type Acceptance = "rejected" | "uncertain";
export type ErrorCode = "rejected" | "unavailable" | "timeout" | "invalid_response" | "unauthorized" | "unexpected";
export type Envelope<T> = { ok: true; result: T } | { ok: false; error: { code: ErrorCode; acceptance: Acceptance } };
const messages: Record<ErrorCode, string> = {
  rejected: "Request rejected. Check the fields, session and revision.",
  unavailable: "Operation unavailable. Acceptance is uncertain; check status before trying again.",
  timeout: "Request timed out. Acceptance is uncertain; check status before trying again.",
  invalid_response: "Invalid helper response. Acceptance is uncertain; check status before trying again.",
  unauthorized: "Local authentication failed. Reconnect the helper.",
  unexpected: "Unexpected action failure. Check the current state before trying again.",
};
export class ControlError extends Error {
  code: ErrorCode;
  acceptance: Acceptance;
  enqueueRejected: boolean;
  constructor(code: ErrorCode, acceptance: Acceptance = "uncertain") {
    super(acceptance === "rejected" && ["unavailable", "timeout", "invalid_response"].includes(code) ? "Request was not accepted. Reconnect the helper before trying again." : messages[code]); this.code = code; this.acceptance = acceptance;
    this.enqueueRejected = acceptance === "rejected";
  }
}
export const visibleError = (e: unknown) => e instanceof ControlError ? e.message : messages.unexpected;
export type Requests = {
  snapshot: {}; create: { name: string }; "join-request": { url: string; id: string; proof: string; name: string };
  "join-finish": {}; bind: { app: string; title: string; native: string; directory: string; model: string };
  "request-create": { native: string; app: string; title?: string; directory?: string; model?: string };
  "request-decide": { native: string; app: string; approve: boolean };
  send: { id: string; text: string; targets: string[]; reply_to?: string };
  object: { id: string; type: string; version: number; data: Record<string, unknown>; event_id: string };
  "outbox-status": { id: string }; pause: { paused: boolean }; "pair-create": {};
  "pair-approve": { id: string }; revoke: { device: string }; cancel: { id: string };
  backup: {}; unlock: {}; "room-select": { room: string }; "room-create": { title: string };
  "room-rename": { room?: string; title: string }; "binding-state": { binding: string; state: string };
  "binding-remove": { binding: string };
};
export type Action = keyof Requests;
export type Results = {
  create: { created: boolean }; "join-request": { requested: boolean; id: string }; "join-finish": { joined: boolean };
  "request-create": { state: "pending" | "already-connected"; binding?: string; note?: string };
  "request-decide": { state: "approved" | "rejected"; binding: string | null };
  pause: { paused: boolean }; "pair-approve": { approved: boolean }; revoke: { revoked: string };
  cancel: { cancelled: string }; unlock: { reconnecting: boolean };
  "room-rename": { id: string; title: string }; "binding-state": { id: string; state: string };
  "binding-remove": { removed: boolean; id?: string; pending?: boolean };
  snapshot: import("./types").Snapshot;
  "outbox-status": { id: string; state: "saved" | "sending" | "sent" | "failed" | "cancelled" | "unknown"; reason?: string };
  send: { id: string; state: string }; object: { id: string; state: string };
  "room-select": { room: string }; "room-create": { id: string; title: string };
  bind: { id: string }; backup: { backup: string };
  "pair-create": { id: string; proof: string };
};
export const REQUEST_MS = 8000;
export async function bounded<T>(work: () => Promise<T>, ms = REQUEST_MS, abort?: () => void): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  try {
    return await Promise.race([Promise.resolve().then(work), new Promise<never>((_, reject) => {
      timer = setTimeout(() => { abort?.(); reject(new ControlError("timeout")); }, ms);
    })]);
  } finally { clearTimeout(timer!); }
}
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
export function decode<A extends Action>(action: A, value: unknown, status = 200): Results[A] {
  if (!record(value) || typeof value.ok !== "boolean") throw new ControlError("invalid_response");
  if (!value.ok) {
    const e = value.error;
    if (!record(e) || typeof e.code !== "string" || !Object.hasOwn(messages, e.code) || !["rejected", "uncertain"].includes(String(e.acceptance))) throw new ControlError("invalid_response");
    throw new ControlError(e.code as ErrorCode, e.acceptance as Acceptance);
  }
  if (status < 200 || status >= 300 || !record(value.result)) throw new ControlError("invalid_response");
  const r = value.result;
  if (action === "snapshot" && (typeof r.configured !== "boolean" || typeof r.activeRoom !== "string" || typeof r.online !== "boolean" || !["rooms", "events", "sessions", "bindings", "receipts", "objects", "outbox", "devices", "pairing"].every(k => Array.isArray(r[k]) && (r[k] as unknown[]).every(record)))) throw new ControlError("invalid_response");
  if (action === "outbox-status" && !["saved", "sending", "sent", "failed", "cancelled", "unknown"].includes(String(r.state))) throw new ControlError("invalid_response");
  for (const key of action === "room-select" ? ["room"] : ["send", "object", "bind", "room-create"].includes(action) ? ["id"] : action === "backup" ? ["backup"] : action === "pair-create" ? ["id", "proof"] : []) {
    if (typeof r[key] !== "string") throw new ControlError("invalid_response");
  }
  if (action === "snapshot" && r.health !== undefined && (!Array.isArray(r.health) || !r.health.every(h => record(h) && ["sync", "stream", "delivery"].includes(String(h.scope))))) throw new ControlError("invalid_response");
  return r as Results[A];
}
export function createControl(native?: (action: Action, data: unknown) => Promise<unknown>, fetcher: typeof fetch = fetch, ms = REQUEST_MS) {
  return async <A extends Action>(action: A, data: Requests[A]): Promise<Results[A]> => {
    const controller = new AbortController();
    try {
      return await bounded(async () => {
        if (native) return decode(action, await native(action, data));
        const response = await fetcher("/control", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, data, contract: 1 }), signal: controller.signal });
        return decode(action, await response.json(), response.status);
      }, ms, () => controller.abort());
    } catch (e) { throw e instanceof ControlError ? e : new ControlError("unavailable"); }
  };
}
