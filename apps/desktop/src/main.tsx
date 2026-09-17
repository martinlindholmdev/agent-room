import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { invoke, isTauri } from "@tauri-apps/api/core";
import {
  ArrowUp,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  Circle,
  Command,
  Hash,
  Inbox,
  MessageSquare,
  Monitor,
  MoreHorizontal,
  PanelRightClose,
  PanelRightOpen,
  Pause,
  Play,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Terminal,
  Users,
  X,
} from "lucide-react";
import "./styles.css";

type Session = {
  id: string;
  native: string;
  app: string;
  title: string;
  device: string;
  device_name: string;
  active: number;
  bridge_connected?: boolean;
  model?: string;
  state?: string;
};
type Event = {
  id: string;
  seq: number;
  kind: string;
  sender: string;
  device: string;
  created: number;
  body: { text?: string; targets?: string[]; reply_to?: string };
};
type ObjectItem = {
  id: string;
  kind: string;
  version: number;
  author: string;
  data: Record<string, any>;
};
type Receipt = {
  message: string;
  target: string;
  state: string;
  reason: string;
};
type RoomRollup = { state: string; needs: number };
type Room = { id: string; title: string; rollup?: RoomRollup };
type Snapshot = {
  configured: boolean;
  mode: string;
  name: string;
  room: string;
  activeRoom: string;
  rooms: Room[];
  device: string;
  online: boolean;
  error: string;
  paused: boolean;
  events: Event[];
  sessions: Session[];
  bindings: Session[];
  receipts: Receipt[];
  objects: ObjectItem[];
  outbox: { id: string; state: string; error: string; event: Event }[];
  devices: { id: string; name: string; active: number; role: string }[];
  pairing: { id: string; name: string; device: string; expires: number }[];
  requests?: {
    native: string;
    app: string;
    title: string;
    directory: string;
    requested: number;
    state: string;
    model?: string;
  }[];
  needsYou?: number;
  activeCount?: number;
};
const empty: Snapshot = {
  configured: false,
  mode: "",
  name: "",
  room: "general",
  activeRoom: "general",
  rooms: [{ id: "general", title: "General" }],
  device: "",
  online: false,
  error: "",
  paused: false,
  events: [],
  sessions: [],
  bindings: [],
  receipts: [],
  objects: [],
  outbox: [],
  devices: [],
  pairing: [],
  requests: [],
  needsYou: 0,
  activeCount: 0,
};
const roomName = (rooms: Room[], id: string) =>
  rooms.find((r) => r.id === id)?.title || (id === "general" ? "General" : id);
// Read-on-demand app types: no push, no idle-wake. "pull" is the Claude-app
// connector; "mcp" is the generic, self-identified connector for any MCP client.
const PULL_LIKE = ["pull", "mcp"];
const appName = (app: string) =>
  ({
    "codex-queue": "Codex",
    "opencode-bridge": "OpenCode",
    "claude-channel": "Claude Code",
    pull: "Read on demand",
    mcp: "MCP (any agent)",
  })[app] || app;
const appLabel = (app: string, model?: string) =>
  model ? appName(app) + " · " + model : appName(app);
// Self-reported presence only (detection is clever; being told is sturdier).
const PRESENCE_LABEL: Record<string, string> = {
  working: "Working",
  idle: "Idle",
  blocked: "Blocked",
  done: "Done",
};
const presenceLabel = (state?: string) => PRESENCE_LABEL[state || "idle"];
type DeliveryHealth = "good" | "warn" | "down";
const targetHealth = (
  target: string,
  sessions: Session[],
  bindings: Session[],
  selfDevice: string,
): { health: DeliveryHealth; note: string } => {
  if (!target) return { health: "good", note: "" };
  const session = sessions.find((p) => p.id === target);
  const binding = bindings.find((b) => b.id === target);
  if (!session)
    return { health: "down", note: "Session is not active in this room" };
  if (session.device !== selfDevice)
    return {
      health: "warn",
      note: "On another Mac · delivery depends on that device being online",
    };
  if (PULL_LIKE.includes(session.app))
    return {
      health: "warn",
      note: "Read on demand · the agent reads when it is active",
    };
  if (session.app === "codex-queue")
    return {
      health: "good",
      note: "Wakes an idle task · arrives next turn if busy",
    };
  if (!binding || !binding.bridge_connected)
    return {
      health: "down",
      note: "Bridge not connected · message will be queued until it reconnects",
    };
  return { health: "good", note: "Bridge active · routed to this conversation" };
};
const receiptName = (state: string, target?: Session) =>
  state === "unavailable" && target && PULL_LIKE.includes(target.app)
    ? "Read on demand · awaiting agent"
    : ({
        waiting: "Waiting for device",
        pending: "Waiting for agent app",
        submitted: "Submitted to agent app",
        acknowledged: "Agent acknowledged",
        unavailable: "Needs connection",
        uncertain: "Send uncertain",
        saved: "Saved on this Mac",
        failed: "Needs attention",
      })[state] || state;
async function api(action: string, data: Record<string, unknown> = {}) {
  const result = isTauri()
    ? await invoke<any>("control", { action, data })
    : await fetch("/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, data }),
      }).then((r) => r.json());
  if (result.error) throw Error(result.error);
  return result;
}
type PaletteAction = {
  id: string;
  label: string;
  hint?: string;
  group: string;
};
function Palette({
  s,
  onClose,
  onExecute,
}: {
  s: Snapshot;
  onClose: () => void;
  onExecute: (a: PaletteAction) => void;
}) {
  const [q, setQ] = useState(""),
    [cursor, setCursor] = useState(0),
    input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => setCursor(0), [q]);
  const session = (id: string) => s.sessions.find((p) => p.id === id);
  const author = (event: Event) =>
    event.sender
      ? session(event.sender)?.title || "Agent conversation"
      : s.devices.find((d) => d.id === event.device)?.name || "You";
  const needle = q.trim().toLowerCase();
  const matches = (...parts: string[]) =>
    !needle || parts.join(" ").toLowerCase().includes(needle);
  const actions: PaletteAction[] = [
    { id: "goto-room", label: "Go to room", hint: "Conversation", group: "Navigate" },
    { id: "goto-inbox", label: "Go to inbox", hint: "Needs you and waiting items", group: "Navigate" },
    { id: "goto-objects", label: "Go to plans & work", hint: "Plans, requests, reviews, decisions", group: "Navigate" },
    { id: "goto-settings", label: "Settings · connections and device", group: "Navigate" },
    { id: "new-message", label: "Message the room…", hint: "Focus composer", group: "Compose" },
    { id: "new-work", label: "New work request", group: "Compose" },
    { id: "new-plan", label: "New shared plan", group: "Compose" },
    { id: "new-review", label: "New review packet", group: "Compose" },
    { id: "new-decision", label: "Record a decision", group: "Compose" },
    { id: "connect", label: "Connect a conversation", group: "Compose" },
  ];
  s.events
    .filter(
      (e) => e.kind === "message" && matches(e.body.text || "", author(e)),
    )
    .slice(-40)
    .reverse()
    .forEach((e) =>
      actions.push({
        id: "msg-" + e.id,
        label: (e.body.text || "").slice(0, 90),
        hint: author(e) + " · message",
        group: "Messages",
      }),
    );
  s.sessions
    .filter((p) => p.active && matches(p.title, appName(p.app), p.device_name))
    .forEach((p) =>
      actions.push({
        id: "session-" + p.id,
        label: p.title,
        hint: appName(p.app) + " · " + p.device_name,
        group: "Participants",
      }),
    );
  s.objects.forEach((o) => {
    const label =
      o.data.title || o.data.objective || o.data.artifact || o.data.text || "";
    if (!matches(String(label), o.kind)) return;
    actions.push({
      id: "object-" + o.id,
      label: String(label).slice(0, 90),
      hint: o.kind,
      group: "Plans, work and reviews",
    });
  });
  const flat = actions.filter((a) => matches(a.label, a.hint || "", a.group));
  const pick = (index: number) =>
    flat[Math.max(0, Math.min(index, flat.length - 1))];
  const execute = (index: number) => {
    const a = pick(index);
    if (a) onExecute(a);
  };
  return (
    <dialog open className="palette" onCancel={onClose}>
      <div
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <div className="palette-input">
          <Search size={15} />
          <input
            ref={input}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search messages, participants, plans or jump…"
            aria-label="Command palette"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setCursor((c) => Math.min(c + 1, flat.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setCursor((c) => Math.max(c - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                execute(cursor);
              } else if (e.key === "Escape") {
                onClose();
              }
            }}
          />
          <kbd>esc</kbd>
        </div>
        <div className="palette-list">
          {flat.map((a, i) => {
            const previous = i > 0 ? flat[i - 1].group : "";
            return (
              <React.Fragment key={a.id}>
                {a.group !== previous && (
                  <div className="palette-group">{a.group}</div>
                )}
                <button
                  className={"palette-item " + (i === cursor ? "active" : "")}
                  onMouseEnter={() => setCursor(i)}
                  onClick={() => execute(i)}
                >
                  <span>{a.label}</span>
                  {a.hint && <small>{a.hint}</small>}
                </button>
              </React.Fragment>
            );
          })}
          {!flat.length && (
            <div className="palette-empty">No matches for “{q}”.</div>
          )}
        </div>
      </div>
    </dialog>
  );
}
// Signature element: a live status dot + app name + model, in mono.
// Repeated in the participants panel, message author lines and connection
// cards so "app + model + state" is the one visual through-line of the app.
function IdentityChip({
  label,
  model,
  status,
}: {
  label: string;
  model?: string;
  status?: string;
}) {
  return (
    <span className={"identity-chip status-" + (status || "idle")}>
      <span className="identity-dot" />
      <span className="identity-text">
        {label}
        {model ? " · " + model : ""}
      </span>
    </span>
  );
}
function Dialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        <button className="icon" aria-label="Close dialog" onClick={onClose}>
          <X size={18} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
function App() {
  const [s, setS] = useState<Snapshot>(empty),
    [loaded, setLoaded] = useState(false),
    [error, setError] = useState(""),
    [connectionError, setConnectionError] = useState(""),
    [view, setView] = useState("room"),
    [context, setContext] = useState(true),
    [query, setQuery] = useState(""),
    [dialog, setDialog] = useState(""),
    [busy, setBusy] = useState(false),
    [text, setText] = useState(""),
    [target, setTarget] = useState(""),
    [reply, setReply] = useState<Event | null>(null),
    [pair, setPair] = useState<any>(null),
    [editing, setEditing] = useState<ObjectItem | null>(null),
    [runtime, setRuntime] = useState<any>({}),
    [palette, setPalette] = useState(false),
    [appearance, setAppearance] = useState(() => {
      try {
        return localStorage.getItem("appearance") || "system";
      } catch {
        return "system";
      }
    });
  const search = useRef<HTMLInputElement>(null),
    composer = useRef<HTMLTextAreaElement>(null),
    bottom = useRef<HTMLDivElement>(null);
  const previous = useRef(0),
    draftId = useRef(crypto.randomUUID());
  const refresh = async () => {
    try {
      const next = await api("snapshot");
      setS({ ...empty, ...next });
      setConnectionError("");
      setLoaded(true);
    } catch (e) {
      setConnectionError(String(e));
      setLoaded(true);
    }
  };
  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 1800);
    if (isTauri()) void invoke("runtime_info").then(setRuntime);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPalette(true);
      }
      if (e.key === "Escape") {
        setQuery("");
        setReply(null);
      }
    };
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);
  useEffect(() => {
    if (appearance === "system") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", appearance);
    }
    try {
      localStorage.setItem("appearance", appearance);
    } catch {
      /* private mode or blocked storage: theme choice just won't persist */
    }
  }, [appearance]);
  useEffect(() => {
    if (s.events.length > previous.current && !query) {
      bottom.current?.scrollIntoView({ behavior: "instant" });
    }
    previous.current = s.events.length;
  }, [s.events.length, query]);
  const act = async (
    action: string,
    data: Record<string, unknown> = {},
    close = true,
  ) => {
    setBusy(true);
    setError("");
    try {
      const result = await api(action, data);
      await refresh();
      if (close) setDialog("");
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setBusy(false);
    }
  };
  const safe = (fn: () => Promise<unknown>) => () => {
    void fn().catch(() => {});
  };
  const session = (id: string) => s.sessions.find((p) => p.id === id);
  const author = (event: Event) =>
    event.sender
      ? session(event.sender)?.title || "Agent conversation"
      : s.devices.find((d) => d.id === event.device)?.name || "You";
  const pending = s.receipts.filter((r) => r.state !== "acknowledged");
  const waiting = s.objects.filter(
    (o) =>
      o.kind === "work" &&
      o.data.state !== "resolved" &&
      o.data.state !== "cancelled",
  );
  const unacknowledged = s.events.filter(
    (e) =>
      e.kind === "message" &&
      !e.sender &&
      e.body.targets?.length &&
      s.receipts.some(
        (r) =>
          r.message === e.id &&
          ["waiting", "pending", "submitted"].includes(r.state),
      ),
  );
  const messages = s.events.filter(
    (e) =>
      e.kind === "message" &&
      (!query ||
        `${e.body.text} ${author(e)}`
          .toLowerCase()
          .includes(query.toLowerCase())),
  );
  const send = async () => {
    if (!text.trim()) return;
    const message = text.trim();
    await act(
      "send",
      {
        id: draftId.current,
        text: message,
        targets: target ? [target] : [],
        reply_to: reply?.id,
      },
      false,
    );
    setText("");
    draftId.current = crypto.randomUUID();
    setReply(null);
    composer.current?.focus();
  };
  const activeSessions = s.sessions.filter((p) => p.active);
  const formSubmit =
    (fn: (data: FormData) => Promise<unknown>) =>
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      void fn(data).catch(() => {});
    };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <MessageSquare size={18} strokeWidth={1.8} />
          </div>
          <span>Agent Room</span>
          <span className="version">01</span>
        </div>
        <button
          className={"nav " + (view === "inbox" ? "selected" : "")}
          onClick={() => setView("inbox")}
        >
          <Inbox size={17} />
          Inbox
          {pending.length + (s.requests?.length || 0) > 0 && (
            <span className="count">
              {pending.length + (s.requests?.length || 0)}
            </span>
          )}
        </button>
        <button
          className={"nav " + (view === "objects" ? "selected" : "")}
          onClick={() => setView("objects")}
        >
          <Users size={17} />
          Plans & work
          {(waiting.length > 0 || s.objects.length > 0) && (
            <span className="count">{s.objects.length}</span>
          )}
        </button>
        <button
          className="nav"
          onClick={() => {
            setPalette(true);
          }}
        >
          <Search size={17} />
          Search<span className="shortcut">⌘ K</span>
        </button>
        {s.configured && (
          <>
            <div className="nav-label">VIEWS</div>
            <button
              className="nav pinned-view"
              onClick={() => {
                setView("inbox");
                setQuery("");
              }}
            >
              <Circle size={17} />
              Needs you
              {(s.needsYou || 0) > 0 && (
                <span className="count">{s.needsYou}</span>
              )}
            </button>
            <button className="nav pinned-view" onClick={() => {}}>
              <Play size={17} />
              Active
              {(s.activeCount || 0) > 0 && (
                <span className="count">{s.activeCount}</span>
              )}
            </button>
          </>
        )}
        <div className="nav-label">YOUR ROOMS</div>
        {(s.rooms.length ? s.rooms : empty.rooms).map((r) => (
          <button
            key={r.id}
            className={
              "nav " +
              (view === "room" && s.activeRoom === r.id ? "selected" : "")
            }
            onClick={safe(async () => {
              if (r.id !== s.activeRoom) await act("room-select", { room: r.id }, false);
              setView("room");
              setQuery("");
            })}
          >
            <Hash size={17} />
            {r.title}
            <span
              className={
                "status-dot status-" + (r.rollup?.state || "idle")
              }
            />
            {(r.rollup?.needs || 0) > 0 && (
              <span className="count">{r.rollup!.needs}</span>
            )}
            {s.activeRoom === r.id && <span className="room-dot" />}
          </button>
        ))}
        <button
          className="nav"
          onClick={safe(async () => {
            const title = window.prompt("Name this room")?.trim();
            if (!title) return;
            await act("room-create", { title }, false);
            setView("room");
            setQuery("");
          })}
        >
          <Plus size={17} />
          New room
        </button>
        <div className="sidebar-note">
          <div className="tiny-rule" />
          <p>
            Sessions stay in
            <br />
            their own apps.
          </p>
        </div>
        <div className="sidebar-bottom">
          <button
            className={"nav " + (view === "settings" ? "selected" : "")}
            onClick={() => setView("settings")}
          >
            <Settings size={17} />
            Settings
          </button>
          <div className="device-label">
            <Monitor size={14} />
            <span>{s.name || "This Mac"}</span>
            <span className={"connection-dot " + (s.online ? "online" : "")} />
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Room <ChevronRight size={13} />
            <strong>
              {view === "room"
                ? roomName(s.rooms, s.activeRoom)
                : view === "inbox"
                  ? "Inbox"
                  : view === "objects"
                    ? "Plans & work"
                    : "Settings"}
            </strong>
          </div>
          <div className="header-actions">
            <span className="quiet-status">
              <span
                className={"connection-dot " + (s.online ? "online" : "")}
              />
              {s.paused
                ? "Delivery paused"
                : s.online
                  ? "Room hub connected"
                  : "Connecting"}
            </span>
            {s.configured && (
              <button
                className="icon"
                title={s.paused ? "Resume delivery" : "Pause delivery"}
                aria-label={s.paused ? "Resume delivery" : "Pause delivery"}
                onClick={safe(() => act("pause", { paused: !s.paused }, false))}
              >
                {s.paused ? <Play size={16} /> : <Pause size={16} />}
              </button>
            )}
            <button
              className="icon"
              aria-label="Toggle room context"
              onClick={() => setContext(!context)}
            >
              {context ? (
                <PanelRightClose size={18} />
              ) : (
                <PanelRightOpen size={18} />
              )}
            </button>
          </div>
        </header>
        {(error || connectionError) && (
          <div className="error-banner" role="alert">
            <span>{error || connectionError}</span>
            <button
              className="icon"
              aria-label="Dismiss error"
              onClick={() => {
                setError("");
                setConnectionError("");
              }}
            >
              <X size={15} />
            </button>
          </div>
        )}
        {!s.online && s.configured && (
          <div className="notice">
            Connection unavailable. New messages stay saved on this Mac and sync
            when the hub returns.
          </div>
        )}
        <div className="main-row">
          <main>
            {!loaded ? (
              <div className="empty-state">
                <div className="brand-mark">
                  <MessageSquare />
                </div>
                <h1>Opening your room</h1>
                <p>Connecting to the local helper…</p>
              </div>
            ) : !s.configured ? (
              <div className="onboarding">
                <div className="eyebrow">SETUP</div>
                <h1>Set up Agent Room</h1>
                <p>
                  Connect existing Codex, Claude Code and OpenCode sessions.
                  Send messages, share plans and request reviews.
                </p>
                <div className="onboard-line">
                  <span>01</span>
                  <div>
                    <strong>Create a room on this Mac</strong>
                    <p>Other devices can connect while this Mac is awake.</p>
                  </div>
                </div>
                <div className="onboard-line">
                  <span>02</span>
                  <div>
                    <strong>Connect existing sessions</strong>
                    <p>
                      Each agent keeps its own session, tools and permissions.
                    </p>
                  </div>
                </div>
                <div className="onboard-actions">
                  <button
                    className="primary"
                    onClick={() => setDialog("create")}
                  >
                    Create a room <ArrowUpRight size={16} />
                  </button>
                  <button
                    className="secondary"
                    onClick={() => setDialog("join")}
                  >
                    Join an existing room
                  </button>
                </div>
              </div>
            ) : view === "settings" ? (
              <div className="settings-page">
                <div className="eyebrow">SETTINGS</div>
                <h1>Room settings</h1>
                <section>
                  <h3>Appearance</h3>
                  <p>Choose a theme.</p>
                  <div className="segmented">
                    {["system", "light", "dark"].map((a) => (
                      <button
                        key={a}
                        className={a === appearance ? "active" : ""}
                        onClick={() => setAppearance(a)}
                      >
                        {a[0].toUpperCase() + a.slice(1)}
                      </button>
                    ))}
                  </div>
                </section>
                <section>
                  <h3>Devices</h3>
                  <p>
                    {s.mode === "host"
                      ? `${s.name} hosts this room. Keep it awake for other Macs to connect.`
                      : "This Mac connects outward to the private room hub."}
                  </p>
                  {s.devices.map((d) => (
                    <div className="settings-row" key={d.id}>
                      <Monitor size={18} />
                      <div>
                        <strong>{d.name}</strong>
                        <small>
                          {d.id === s.device
                            ? "This Mac"
                            : d.active
                              ? "Paired device"
                              : "Access revoked"}{" "}
                          ·{" "}
                          {d.role === "admin"
                            ? "Room administrator"
                            : "Room member"}
                        </small>
                      </div>
                      {d.id !== s.device && d.active && s.mode === "host" && (
                        <button
                          className="text-button"
                          onClick={safe(() =>
                            act("revoke", { device: d.id }, false),
                          )}
                        >
                          Revoke access
                        </button>
                      )}
                    </div>
                  ))}
                  {s.mode === "host" && (
                    <button
                      className="secondary"
                      onClick={safe(async () => {
                        setPair(await act("pair-create", {}, false));
                        setDialog("pair");
                      })}
                    >
                      <Plus size={15} />
                      Pair another Mac
                    </button>
                  )}
                  {s.pairing.map((p) => (
                    <div className="pair-request" key={p.id}>
                      <ShieldCheck size={20} />
                      <div>
                        <strong>{p.name} wants to join</strong>
                        <small>Device {p.device}</small>
                      </div>
                      <button
                        className="primary"
                        onClick={safe(() =>
                          act("pair-approve", { id: p.id }, false),
                        )}
                      >
                        Approve device
                      </button>
                    </div>
                  ))}
                </section>
                <section>
                  <h3>Background delivery</h3>
                  {isTauri() && (
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={!!runtime.login_start}
                        onChange={(e) => {
                          void invoke<any>("set_login_start", {
                            enabled: e.target.checked,
                          })
                            .then((value) =>
                              setRuntime({ ...runtime, ...value }),
                            )
                            .catch((e) => setError(String(e)));
                        }}
                      />
                      Start Agent Room at login
                    </label>
                  )}
                  <p>
                    Close the window to keep the room running. Reopen Agent Room
                    from the Dock. Quit Agent Room to stop this device’s helper;
                    saved messages remain on disk.
                  </p>
                  <button
                    className="secondary"
                    onClick={safe(() =>
                      act("pause", { paused: !s.paused }, false),
                    )}
                  >
                    {s.paused ? "Resume delivery" : "Pause delivery"}
                  </button>
                </section>
                <section>
                  <h3>Connections</h3>
                  <p>
                    Each binding points to one exact existing conversation. A
                    new session gets a new identity.
                  </p>
                  {s.bindings.map((p) => (
                    <div className="settings-row" key={p.id}>
                      <Terminal size={18} />
                      <div>
                        <strong>{p.title}</strong>
                        <div className="binding-meta">
                          <IdentityChip
                            label={appName(p.app)}
                            model={p.model}
                            status={p.state}
                          />
                          <small className="mono">{p.native}</small>
                        </div>
                        <small>
                          {p.app === "codex-queue"
                            ? "Configured for next-turn delivery; check receipts"
                            : PULL_LIKE.includes(p.app)
                              ? "Configured for on-demand reading"
                              : p.bridge_connected
                                ? "Helper bridge active; agent receipt still required"
                                : "Helper bridge inactive; check host setup"}
                        </small>
                      </div>
                      <button
                        className="text-button"
                        onClick={() => {
                          setEditing({
                            id: p.id,
                            kind: "connection",
                            version: 1,
                            author: "",
                            data: p,
                          });
                          setDialog("connection");
                        }}
                      >
                        Setup details
                      </button>
                      <button
                        className="text-button"
                        onClick={safe(() => {
                          if (
                            !window.confirm(
                              `Remove the connection to "${p.title}"? The session is disconnected; reconnecting later creates a new one.`,
                            )
                          )
                            return Promise.resolve();
                          return act("binding-remove", { binding: p.id }, false);
                        })}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    className="secondary"
                    onClick={() => setDialog("connect")}
                  >
                    <Plus size={15} />
                    Connect a conversation
                  </button>
                </section>
                <section>
                  <h3>About this build</h3>
                  {!s.online && (
                    <button
                      className="secondary"
                      onClick={safe(() => act("unlock", {}, false))}
                    >
                      Reconnect with Keychain
                    </button>
                  )}
                  <p>Agent Room 0.1.0 · Local preview release</p>
                  <p>
                    Native credentials stay on their own Mac. Device credentials
                    are stored in Keychain. Updates are manual until a signed
                    release service is configured.
                  </p>
                  <button
                    className="secondary"
                    onClick={safe(async () => {
                      const result = await act("backup", {}, false);
                      setError("Backup saved: " + result.backup);
                    })}
                  >
                    Create a consistent backup
                  </button>
                  {runtime.hub_port && (
                    <details>
                      <summary>Private hub setup</summary>
                      <p>
                        Expose only the protocol listener through Tailscale
                        Serve HTTPS. Keep the local control listener private.
                      </p>
                      <code>
                        tailscale serve --bg http://127.0.0.1:{runtime.hub_port}
                      </code>
                    </details>
                  )}
                </section>
              </div>
            ) : view === "objects" ? (
              <div className="objects-page">
                <div className="eyebrow">PLANS & WORK</div>
                <h1>Shared planning</h1>
                <p className="lead">
                  Plans, work requests, reviews and decisions for this room.
                </p>
                <div className="objects-actions">
                  <button
                    className="secondary"
                    onClick={() => {
                      setEditing(null);
                      setDialog("workflow:plan");
                    }}
                  >
                    <Plus size={15} />
                    Plan
                  </button>
                  <button
                    className="secondary"
                    onClick={() => {
                      setEditing(null);
                      setDialog("workflow:work");
                    }}
                  >
                    <Plus size={15} />
                    Work request
                  </button>
                  <button
                    className="secondary"
                    onClick={() => {
                      setEditing(null);
                      setDialog("workflow:review");
                    }}
                  >
                    <Plus size={15} />
                    Review
                  </button>
                  <button
                    className="secondary"
                    onClick={() => {
                      setEditing({
                        id: crypto.randomUUID(),
                        kind: "decision",
                        version: 0,
                        author: "",
                        data: {},
                      });
                      setDialog("workflow:decision");
                    }}
                  >
                    <Plus size={15} />
                    Decision
                  </button>
                </div>
                {!s.objects.length && (
                  <div className="quiet-empty">
                    <Check size={17} />
                    No plans or work requests yet. Create one above, or use ⌘K.
                  </div>
                )}
                {s.objects
                  .filter((o) => o.kind === "plan")
                  .map((o) => (
                    <button
                      className="object-card"
                      key={o.id}
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow:plan");
                      }}
                    >
                      <div className="object-card-head">
                        <strong>{o.data.objective}</strong>
                        <span className="count">v{o.version}</span>
                      </div>
                      <ol>
                        {(o.data.steps || []).map((step: string, i: number) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ol>
                    </button>
                  ))}
                {s.objects
                  .filter((o) => o.kind === "work")
                  .map((o) => (
                    <button
                      className={"object-card state-" + (o.data.state || "proposed")}
                      key={o.id}
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow:work");
                      }}
                    >
                      <div className="object-card-head">
                        <strong>{o.data.title}</strong>
                        <span className="object-state">
                          {o.data.state || "proposed"}
                        </span>
                      </div>
                      {o.data.scope && <p>{o.data.scope}</p>}
                      <small>
                        {o.data.owner
                          ? "Owner: " +
                            (session(o.data.owner)?.title || "exact session")
                          : "Unassigned"}
                        {o.data.evidence ? " · evidence: " + o.data.evidence : ""}
                      </small>
                    </button>
                  ))}
                {s.objects
                  .filter((o) => o.kind === "review")
                  .map((o) => (
                    <button
                      className="object-card"
                      key={o.id}
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow:review");
                      }}
                    >
                      <div className="object-card-head">
                        <strong>{o.data.artifact}</strong>
                        <span
                          className={
                            "object-state " +
                            (o.data.verdict === "approved" ? "ok" : "")
                          }
                        >
                          {o.data.verdict || "pending"}
                        </span>
                      </div>
                      <small>
                        Revision {o.data.revision}
                        {o.data.base ? " · base " + o.data.base : ""}
                        {o.data.reviewer
                          ? " · reviewer: " +
                            (session(o.data.reviewer)?.title || "exact session")
                          : ""}
                      </small>
                      {o.data.checks && <p>{o.data.checks}</p>}
                    </button>
                  ))}
                {s.objects
                  .filter((o) => o.kind === "decision")
                  .map((o) => (
                    <button
                      className="object-card"
                      key={o.id}
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow:decision");
                      }}
                    >
                      <div className="object-card-head">
                        <strong>{o.data.text}</strong>
                        <span className="object-state">{o.data.state}</span>
                      </div>
                      <small>
                        {o.data.accepted_by
                          ? "Accepted by " +
                            (session(o.data.accepted_by)?.title ||
                              s.devices.find((d) => d.id === o.data.accepted_by)
                                ?.name ||
                              o.data.accepted_by)
                          : "Proposed for discussion"}
                      </small>
                    </button>
                  ))}
              </div>
            ) : view === "inbox" ? (
              <div className="inbox-page">
                <div className="eyebrow">INBOX</div>
                <h1>Open requests</h1>
                <p className="lead">Open work and delivery issues.</p>
                {(s.requests?.length || 0) > 0 && (
                  <div className="request-list">
                    <h3>
                      Connection requests{" "}
                      <span className="count">{s.requests!.length}</span>
                    </h3>
                    {s.requests!.map((r) => (
                      <div className="inbox-item request" key={r.native + r.app}>
                        <Circle size={18} />
                        <div>
                          <strong>{r.title}</strong>
                          <p>
                            <IdentityChip label={appName(r.app)} model={r.model} />{" "}
                            wants to join this room. Approving connects its
                            exact session; nothing is routed until then.
                          </p>
                          <small className="mono">{r.native}</small>
                        </div>
                        <span className="request-actions">
                          <button
                            className="primary"
                            disabled={busy}
                            onClick={safe(() =>
                              act("request-decide", {
                                native: r.native,
                                app: r.app,
                                approve: true,
                              }),
                            )}
                          >
                            Approve
                          </button>
                          <button
                            className="secondary"
                            disabled={busy}
                            onClick={safe(() =>
                              act("request-decide", {
                                native: r.native,
                                app: r.app,
                                approve: false,
                              }),
                            )}
                          >
                            Decline
                          </button>
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <h3>
                  Needs you{" "}
                  <span className="count">
                    {(s.requests?.length || 0) +
                      s.receipts.filter((r) => {
                        const target = session(r.target);
                        const binding = s.bindings.find(
                          (b) => b.id === r.target,
                        );
                        return (
                          ["unavailable", "uncertain"].includes(r.state) ||
                          (r.state === "pending" &&
                            target &&
                            target.device === s.device &&
                            !["pull", "mcp", "codex-queue"].includes(
                              target.app,
                            ) &&
                            !(binding?.bridge_connected ?? false))
                        );
                      }).length +
                      s.outbox.filter((o) => o.state === "failed").length}
                  </span>
                </h3>
                {s.receipts
                  .filter((r) => {
                    const target = session(r.target);
                    const binding = s.bindings.find(
                      (b) => b.id === r.target,
                    );
                    return (
                      ["unavailable", "uncertain"].includes(r.state) ||
                      (r.state === "pending" &&
                        target &&
                        target.device === s.device &&
                        !["pull", "mcp", "codex-queue"].includes(target.app) &&
                        !(binding?.bridge_connected ?? false))
                    );
                  })
                  .map((r) => {
                    const target = session(r.target);
                    const binding = s.bindings.find(
                      (b) => b.id === r.target,
                    );
                    const stuck =
                      r.state === "pending" &&
                      target &&
                      target.device === s.device &&
                      !["pull", "mcp", "codex-queue"].includes(target.app) &&
                      !(binding?.bridge_connected ?? false);
                    return (
                      <button
                        className="inbox-item"
                        key={r.message + r.target}
                        onClick={() => {
                          setView("room");
                          setQuery(
                            s.events
                              .find((e) => e.id === r.message)
                              ?.body.text?.slice(0, 40) || "",
                          );
                        }}
                      >
                        <Circle size={18} />
                        <div>
                          <strong>
                            {stuck
                              ? "Queued · bridge not connected"
                              : receiptName(r.state, target)}
                          </strong>
                          <p>
                            {stuck
                              ? "Reconnect or resume the exact session to deliver this message"
                              : r.reason}
                          </p>
                          <small>{target?.title}</small>
                        </div>
                        <ArrowUpRight size={17} />
                      </button>
                    );
                  })}
                {s.outbox
                  .filter((o) => o.state === "failed")
                  .map((o) => (
                    <div className="inbox-item" key={o.id}>
                      <Circle size={18} />
                      <div>
                        <strong>Message needs attention</strong>
                        <p>{o.error}</p>
                        <small>{o.event.body.text}</small>
                      </div>
                    </div>
                  ))}
                {!s.receipts.some((r) => {
                  const target = session(r.target);
                  const binding = s.bindings.find((b) => b.id === r.target);
                  return (
                    ["unavailable", "uncertain"].includes(r.state) ||
                    (r.state === "pending" &&
                      target &&
                      target.device === s.device &&
                      !["pull", "mcp", "codex-queue"].includes(target.app) &&
                      !(binding?.bridge_connected ?? false))
                  );
                }) &&
                  !s.outbox.some((o) => o.state === "failed") &&
                  !(s.requests?.length || 0) && (
                    <div className="quiet-empty">
                      <Check size={17} />
                      Nothing needs your attention right now.
                    </div>
                  )}
                <h3>
                  Waiting on agents{" "}
                  <span className="count">
                    {waiting.length + unacknowledged.length}
                  </span>
                </h3>
                {unacknowledged.map((e) => {
                  const outstanding = s.receipts.filter(
                    (r) =>
                      r.message === e.id &&
                      ["waiting", "pending", "submitted"].includes(r.state),
                  );
                  return (
                    <button
                      className="inbox-item"
                      key={"unacked-" + e.id}
                      onClick={() => {
                        setView("room");
                        setQuery("");
                        setTimeout(
                          () =>
                            document
                              .getElementById("message-" + e.id)
                              ?.scrollIntoView({ block: "center" }),
                          30,
                        );
                      }}
                    >
                      <Circle size={18} />
                      <div>
                        <strong>
                          {outstanding.length > 1
                            ? `Awaiting ${outstanding.length} agents`
                            : receiptName(
                                outstanding[0].state,
                                session(outstanding[0].target),
                              )}
                        </strong>
                        <p>{e.body.text?.slice(0, 90)}</p>
                        <small>
                          {outstanding
                            .map((r) => session(r.target)?.title)
                            .join(", ")}
                        </small>
                      </div>
                      <ArrowUpRight size={17} />
                    </button>
                  );
                })}
                {waiting.map((o) => (
                  <button
                    className="inbox-item"
                    key={o.id}
                    onClick={() => {
                      setEditing(o);
                      setDialog("workflow");
                    }}
                  >
                    <Circle size={18} />
                    <div>
                      <strong>{o.data.title}</strong>
                      <p>
                        {o.data.state} · {session(o.data.owner)?.title}
                      </p>
                    </div>
                    <ChevronRight size={16} />
                  </button>
                ))}
                {!waiting.length && !unacknowledged.length && (
                  <div className="quiet-empty">
                    Your next work request will appear here.
                  </div>
                )}
                <h3>Completed</h3>
                {s.objects
                  .filter(
                    (o) => o.kind === "work" && o.data.state === "resolved",
                  )
                  .map((o) => (
                    <div className="inbox-item" key={o.id}>
                      <CheckCheck size={18} />
                      <div>
                        <strong>{o.data.title}</strong>
                        <p>{o.data.evidence}</p>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <>
                <div className="room-heading">
                  <div>
                    <div className="eyebrow">SHARED ROOM</div>
                    <h1>
                      General<span className="subtle-hash">#</span>
                    </h1>
                    <p>Messages, plans and reviews.</p>
                  </div>
                  <button
                    className="secondary"
                    onClick={() => setDialog("connect")}
                  >
                    <Plus size={15} />
                    Connect agent
                  </button>
                </div>
                <div className="conversation-toolbar">
                  <span>
                    <MessageSquare size={14} />
                    Conversation{" "}
                    <span className="count">
                      {s.events.filter((e) => e.kind === "message").length}
                    </span>
                  </span>
                  <div className="search-field">
                    <Search size={14} />
                    <input
                      ref={search}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search this room"
                      aria-label="Search this room"
                    />
                    <kbd>⌘ K</kbd>
                  </div>
                </div>
                <div className="conversation" aria-live="polite">
                  {!messages.length && !query ? (
                    <div className="room-welcome">
                      <div className="welcome-symbol">
                        <MessageSquare size={30} strokeWidth={1} />
                        <span>+</span>
                      </div>
                      <h2>No messages yet</h2>
                      <p>Connect an agent, then send a message.</p>
                      <div className="suggestions">
                        <button
                          onClick={() => {
                            setText(
                              "Let’s agree on the objective and the first three steps.",
                            );
                            composer.current?.focus();
                          }}
                        >
                          Start a plan <ArrowUpRight size={14} />
                        </button>
                        <button
                          onClick={() => {
                            setEditing(null);
                            setDialog("workflow");
                          }}
                        >
                          Request a review <ArrowUpRight size={14} />
                        </button>
                      </div>
                      <div className="room-principles">
                        <span>
                          <Check size={13} />
                          Existing sessions
                        </span>
                        <span>
                          <Check size={13} />
                          Explicit receipts
                        </span>
                        <span>
                          <Check size={13} />
                          Saved on your Mac
                        </span>
                      </div>
                    </div>
                  ) : !messages.length ? (
                    <div className="quiet-empty">
                      No messages match “{query}”.
                    </div>
                  ) : (
                    <>
                      <div className="day-divider">
                        <span>ROOM CONVERSATION</span>
                      </div>
                      {messages.map((event) => {
                        const participant = session(event.sender),
                          receipts = s.receipts.filter(
                            (r) => r.message === event.id,
                          );
                        return (
                          <article
                            className="message"
                            id={"message-" + event.id}
                            key={event.id}
                          >
                            <div
                              className={
                                "avatar " + (!event.sender ? "human" : "")
                              }
                            >
                              {event.sender ? (
                                <Terminal size={15} />
                              ) : (
                                author(event).slice(0, 1).toUpperCase()
                              )}
                            </div>
                            <div className="message-main">
                              <div className="message-meta">
                                <strong>{author(event)}</strong>
                                {participant && (
                                  <IdentityChip
                                    label={appName(participant.app)}
                                    model={participant.model}
                                    status={
                                      s.bindings.find(
                                        (b) => b.id === participant.id,
                                      )?.state
                                    }
                                  />
                                )}
                                <time
                                  title={new Date(
                                    event.created * 1000,
                                  ).toLocaleString()}
                                >
                                  {new Date(
                                    event.created * 1000,
                                  ).toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </time>
                                <button
                                  className="message-reply"
                                  onClick={() => {
                                    setReply(event);
                                    setTarget(event.sender || "");
                                    composer.current?.focus();
                                  }}
                                >
                                  Reply
                                </button>
                              </div>
                              {event.body.reply_to && (
                                <button
                                  className="reply-source"
                                  onClick={() => {
                                    setQuery("");
                                    setTimeout(
                                      () =>
                                        document
                                          .getElementById(
                                            "message-" + event.body.reply_to,
                                          )
                                          ?.scrollIntoView({ block: "center" }),
                                      30,
                                    );
                                  }}
                                >
                                  ↳ Reply to{" "}
                                  {s.events
                                    .find((e) => e.id === event.body.reply_to)
                                    ?.body.text?.slice(0, 90) ||
                                    "earlier message"}
                                </button>
                              )}
                              <div className="message-text">
                                {event.body.text}
                              </div>
                              <div className="message-foot">
                                {event.body.targets?.length ? (
                                  <span>
                                    To{" "}
                                    {event.body.targets
                                      .map(
                                        (id) =>
                                          session(id)?.title || "Exact session",
                                      )
                                      .join(", ")}
                                  </span>
                                ) : (
                                  <span>Room board</span>
                                )}
                                {receipts.map((r) => {
                                  const target = session(r.target);
                                  const binding = s.bindings.find(
                                    (b) => b.id === r.target,
                                  );
                                  const stuck =
                                    r.state === "pending" &&
                                    target &&
                                    target.device === s.device &&
                                    !["pull", "mcp", "codex-queue"].includes(
                                      target.app,
                                    ) &&
                                    !(binding?.bridge_connected ?? false);
                                  return (
                                    <span
                                      title={
                                        stuck
                                          ? "Bridge not connected · message queued until reconnect"
                                          : r.reason
                                      }
                                      className={
                                        "receipt " +
                                        (stuck ? "stuck" : r.state)
                                      }
                                      key={r.target}
                                    >
                                      {r.state === "acknowledged" ? (
                                        <CheckCheck size={12} />
                                      ) : r.state === "submitted" ? (
                                        <Check size={12} />
                                      ) : (
                                        <Circle size={9} />
                                      )}{" "}
                                      {stuck
                                        ? "Queued · bridge not connected"
                                        : receiptName(r.state, target)}
                                    </span>
                                  );
                                })}
                              </div>
                            </div>
                          </article>
                        );
                      })}
                    </>
                  )}
                  {s.outbox
                    .filter(
                      (o) =>
                        o.event.kind === "message" &&
                        !s.events.some((e) => e.id === o.id),
                    )
                    .map((o) => (
                      <article className="message unsynced" key={o.id}>
                        <div className="avatar human">{s.name.slice(0, 1)}</div>
                        <div className="message-main">
                          <div className="message-meta">
                            <strong>You</strong>
                          </div>
                          <div className="message-text">
                            {o.event.body.text}
                          </div>
                          <div className="message-foot">
                            {receiptName(o.state)}
                            {o.state === "saved" && (
                              <button
                                className="text-button"
                                onClick={safe(() =>
                                  act("cancel", { id: o.id }, false),
                                )}
                              >
                                Cancel unsent message
                              </button>
                            )}
                          </div>
                        </div>
                      </article>
                    ))}
                  <div ref={bottom} />
                </div>
                <div className="composer-area">
                  {reply && (
                    <div className="replying">
                      <span>
                        Replying to {author(reply)}:{" "}
                        {reply.body.text?.slice(0, 70)}
                      </span>
                      <button
                        className="icon"
                        aria-label="Cancel reply"
                        onClick={() => setReply(null)}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}
                  <form
                    className="composer"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void send().catch(() => {});
                    }}
                  >
                    <div className="composer-target">
                      <span>To</span>
                      <select
                        aria-label="Message recipient"
                        disabled={busy}
                        value={target}
                        onChange={(e) => setTarget(e.target.value)}
                      >
                        <option value="">Room board</option>
                        {activeSessions.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.title} · {appName(p.app)} · {p.device_name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={12} />
                      {targetHealth(target, s.sessions, s.bindings, s.device)
                        .health !== "good" && (
                        <span
                          className={
                            "target-health " +
                            targetHealth(
                              target,
                              s.sessions,
                              s.bindings,
                              s.device,
                            ).health
                          }
                        >
                          {
                            targetHealth(
                              target,
                              s.sessions,
                              s.bindings,
                              s.device,
                            ).note
                          }
                        </span>
                      )}
                    </div>
                    <textarea
                      ref={composer}
                      aria-label="Message"
                      disabled={busy}
                      value={text}
                      onChange={(e) => {
                        setText(e.target.value);
                        draftId.current = crypto.randomUUID();
                      }}
                      placeholder={
                        target ? "Message this agent…" : "Message the room…"
                      }
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                          e.preventDefault();
                          void send().catch(() => {});
                        }
                      }}
                    />
                    <div className="composer-bottom">
                      <span>
                        {target
                          ? "Routed to this exact conversation"
                          : "Posted to the board · choose an agent to request delivery"}
                      </span>
                      <button
                        type="submit"
                        aria-label="Send message"
                        className="send"
                        disabled={!text.trim() || busy}
                      >
                        <ArrowUp size={18} />
                      </button>
                    </div>
                  </form>
                  <div className="composer-help">
                    <span>
                      Saved locally before sending. Receipts show when an agent
                      has read it.
                    </span>
                    <span>⌘ ↵ to send</span>
                  </div>
                </div>
              </>
            )}
          </main>
          {context && s.configured && view === "room" && (
            <aside className="context">
              <div className="context-title">
                In this room{" "}
                <button
                  className="icon"
                  aria-label="Room settings"
                  onClick={() => setView("settings")}
                >
                  <MoreHorizontal size={17} />
                </button>
              </div>
              <section>
                <div className="section-label">
                  PARTICIPANTS <span>{activeSessions.length}</span>
                </div>
                {!activeSessions.length ? (
                  <p className="context-empty">
                    Connect an agent’s existing conversation to get started.
                  </p>
                ) : (
                  activeSessions.map((p) => (
                    <div className="participant" key={p.id}>
                      <div className="avatar">
                        <Terminal size={14} />
                      </div>
                      <div>
                        <strong title={presenceLabel(
                          s.bindings.find((b) => b.id === p.id)?.state,
                        )}>{p.title}</strong>
                        <IdentityChip
                          label={appName(p.app)}
                          model={s.bindings.find((b) => b.id === p.id)?.model}
                          status={s.bindings.find((b) => b.id === p.id)?.state}
                        />
                        <small>{p.device_name}</small>
                        <span className="participant-status">
                          {p.app === "codex-queue"
                            ? "Next-turn delivery"
                            : PULL_LIKE.includes(p.app)
                              ? "Read on demand"
                              : p.device !== s.device
                                ? "On another Mac · check receipts"
                              : s.bindings.find((b) => b.id === p.id)
                                    ?.bridge_connected
                                ? "Helper bridge active · check receipts"
                                : "Helper bridge inactive · check setup"}
                        </span>
                      </div>
                    </div>
                  ))
                )}
                <button
                  className="text-button"
                  onClick={() => setDialog("connect")}
                >
                  <Plus size={13} />
                  Connect a conversation
                </button>
              </section>
              <section>
                <div className="section-label">
                  CURRENT PLAN{" "}
                  <button
                    className="icon"
                    aria-label="Add plan"
                    onClick={() => {
                      setEditing({
                        id: crypto.randomUUID(),
                        kind: "plan",
                        version: 0,
                        author: "",
                        data: {},
                      });
                      setDialog("workflow");
                    }}
                  >
                    <Plus size={14} />
                  </button>
                </div>
                {s.objects
                  .filter((o) => o.kind === "plan")
                  .map((o) => (
                    <button
                      key={o.id}
                      className="object-block"
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow");
                      }}
                    >
                      <strong>{o.data.objective}</strong>
                      <ol>
                        {o.data.steps.map((step: string, i: number) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ol>
                      <small>Version {o.version}</small>
                    </button>
                  ))}
                {!s.objects.some((o) => o.kind === "plan") && (
                  <p className="context-empty">No plan yet.</p>
                )}
              </section>
              <section>
                <div className="section-label">
                  WORK & REVIEWS
                  <button
                    className="icon"
                    aria-label="Add work request"
                    onClick={() => {
                      setEditing(null);
                      setDialog("workflow");
                    }}
                  >
                    <Plus size={14} />
                  </button>
                </div>
                {s.objects
                  .filter((o) => ["work", "review"].includes(o.kind))
                  .map((o) => (
                    <button
                      className="object-block"
                      key={o.id}
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow");
                      }}
                    >
                      <strong>{o.data.title || o.data.artifact}</strong>
                      <p>{o.data.state || o.data.verdict}</p>
                      {o.kind === "review" && (
                        <small>
                          Revision {o.data.revision}
                          {o.data.self_review ? " · Self-review" : ""}
                        </small>
                      )}
                    </button>
                  ))}
                {!s.objects.some((o) =>
                  ["work", "review"].includes(o.kind),
                ) && (
                  <p className="context-empty">No work requests or reviews.</p>
                )}
              </section>
              <section>
                <div className="section-label">
                  DECISIONS
                  <button
                    className="icon"
                    aria-label="Add decision"
                    onClick={() => {
                      setEditing({
                        id: crypto.randomUUID(),
                        kind: "decision",
                        version: 0,
                        author: "",
                        data: {},
                      });
                      setDialog("workflow");
                    }}
                  >
                    <Plus size={14} />
                  </button>
                </div>
                {s.objects
                  .filter((o) => o.kind === "decision")
                  .map((o) => (
                    <button
                      className="object-block"
                      key={o.id}
                      onClick={() => {
                        setEditing(o);
                        setDialog("workflow");
                      }}
                    >
                      <strong>{o.data.text}</strong>
                      <p>{o.data.state}</p>
                      <small>
                        {o.data.accepted_by
                          ? "Accepted by " +
                            (session(o.data.accepted_by)?.title ||
                              s.devices.find((d) => d.id === o.data.accepted_by)
                                ?.name ||
                              o.data.accepted_by)
                          : "Proposed for discussion"}
                      </small>
                    </button>
                  ))}
                {!s.objects.some((o) => o.kind === "decision") && (
                  <p className="context-empty">No decisions recorded.</p>
                )}
              </section>
              <div className="context-footer">
                <ShieldCheck size={15} />
                <span>Messages use exact session IDs.</span>
              </div>
            </aside>
          )}
        </div>
      </div>
      {dialog === "create" && (
        <Dialog title="Create room" onClose={() => setDialog("")}>
          <form
            onSubmit={formSubmit((d) => act("create", { name: d.get("name") }))}
          >
            <p>
              This Mac will host the room. You can pair more Macs once it’s
              ready.
            </p>
            <label>
              Device name
              <input
                name="name"
                required
                maxLength={80}
                placeholder="My Mac"
                autoFocus
              />
            </label>
            <button className="primary wide" disabled={busy}>
              Create room <ArrowUpRight size={16} />
            </button>
          </form>
        </Dialog>
      )}
      {dialog === "join" && (
        <Dialog title="Join an existing room" onClose={() => setDialog("")}>
          <form
            onSubmit={formSubmit((d) =>
              act(
                "join-request",
                {
                  url: d.get("url"),
                  id: d.get("id"),
                  proof: d.get("proof"),
                  name: d.get("name"),
                },
                false,
              ),
            )}
          >
            <p>
              Create a pairing invitation on the Mac that hosts your room. Use
              its private HTTPS address.
            </p>
            <label>
              This device’s name
              <input name="name" required placeholder="My other Mac" />
            </label>
            <label>
              Private hub address
              <input
                name="url"
                type="url"
                required
                placeholder="https://your-mac.your-tailnet.ts.net"
              />
            </label>
            <label>
              Invitation ID
              <input name="id" required />
            </label>
            <label>
              Pairing proof
              <input name="proof" type="password" required autoComplete="off" />
            </label>
            <button className="primary wide" disabled={busy}>
              Request to join
            </button>
            <button
              type="button"
              className="secondary wide"
              onClick={safe(() => act("join-finish"))}
            >
              I’ve approved this Mac — finish pairing
            </button>
          </form>
        </Dialog>
      )}
      {dialog === "pair" && (
        <Dialog title="Pair another Mac" onClose={() => setDialog("")}>
          <p>
            Open Agent Room on your other Mac and choose{" "}
            <strong>Join an existing room</strong>. This invitation expires in
            five minutes.
          </p>
          <label>
            Invitation ID
            <input className="mono" readOnly value={pair?.id || ""} />
          </label>
          <label>
            Single-use proof
            <input
              className="mono"
              readOnly
              type="password"
              value={pair?.proof || ""}
              onFocus={(e) => e.target.select()}
            />
          </label>
          <p className="small">
            Copy these directly into the other app. Then approve the device in
            Settings on this Mac. The invitation grants access only to General.
          </p>
          <button
            className="primary wide"
            onClick={() => {
              setDialog("");
              setView("settings");
            }}
          >
            View pairing requests
          </button>
        </Dialog>
      )}
      {dialog === "connect" && (
        <Dialog
          title="Connect an existing conversation"
          onClose={() => setDialog("")}
        >
          <form
            onSubmit={formSubmit(async (d) => {
              const result = await act("bind", {
                app: d.get("app"),
                title: d.get("title"),
                native: d.get("native"),
                directory: d.get("directory"),
                model: d.get("model"),
              });
              setEditing({
                id: result.id,
                kind: "connection",
                version: 1,
                author: "",
                data: result,
              });
              setDialog("connection");
            })}
          >
            <p>
              Choose a conversation on <strong>{s.name}</strong>. Its native
              identity stays unchanged.
            </p>
            <label>
              Agent app
              <select name="app">
                <option value="codex-queue">Codex</option>
                <option value="opencode-bridge">OpenCode</option>
                <option value="claude-channel">Claude Code</option>
                <option value="pull">Claude app · read on demand</option>
                <option value="mcp">MCP (any agent) · read on demand</option>
              </select>
            </label>
            <label>
              Conversation title
              <input
                name="title"
                required
                placeholder="Implementation review"
                maxLength={200}
              />
            </label>
            <label>
              Exact native session ID
              <input
                name="native"
                required
                placeholder="Task UUID or ses_…"
                maxLength={128}
              />
            </label>
            <label>
              Local directory · required for OpenCode
              <input
                name="directory"
                placeholder="/absolute/path/to/workspace"
              />
            </label>
            <label>
              Model · optional
              <input
                name="model"
                placeholder="e.g. claude-opus-4-8"
                maxLength={100}
              />
            </label>
            <p className="small">
              Codex can receive on its next turn. OpenCode needs the local
              plugin. Claude app sessions can read messages using ordinary MCP
              tools during a turn; channel push needs separate host support.
              Any other MCP client can connect generically, self-identifying
              its own session. Registration alone doesn’t prove receipt.
            </p>
            <button className="primary wide" disabled={busy}>
              Connect conversation <ArrowUpRight size={16} />
            </button>
          </form>
        </Dialog>
      )}
      {dialog === "connection" && editing && (
        <Dialog
          title={editing.data.title || "Conversation setup"}
          onClose={() => setDialog("")}
        >
          <div className="setup-kind">
            <Terminal size={18} />
            {appName(editing.data.app)}
          </div>
          <p>
            {editing.data.app === "codex-queue"
              ? "Delivery uses the installed Codex queue for this exact task. Replies and receipts need the separate desktop room tools below."
              : editing.data.app === "opencode-bridge"
                ? "Copy the bundled OpenCode plugin into your OpenCode plugins folder, then restart OpenCode when its sessions are idle. The plugin finds this exact conversation automatically."
                : editing.data.app === "pull"
                  ? "Claude app read-on-demand uses ordinary MCP tools in this existing conversation. For optional background watch, the agent can call room_monitor_setup and start its returned command with the native app Monitor tool under normal host permissions. Each watch expires after at most 30 minutes and must be renewed; real idle delivery needs a receiving read and acknowledgement."
                  : editing.data.app === "mcp"
                    ? "Generic MCP read-on-demand uses ordinary MCP tools in this existing conversation. The connecting client self-identifies its own native session; no push and no idle-wake, the agent reads when it is active."
                    : "Connect the bundled MCP helper to this same native conversation. Claude Code channels require host support and a launch opt-in. Custom channels in research preview require the development allowlist flag; check whether this Desktop host can supply it."}
          </p>
          <label>
            Native conversation
            <input className="mono" value={editing.data.native} readOnly />
          </label>
          <label>
            Desktop room binding
            <input className="mono" value={editing.id} readOnly />
          </label>
          {editing.data.app === "opencode-bridge" ? (
            <p className="small">
              Plugin files are inside Agent Room.app at Contents/Resources/adapters.
              Copy agent-room-desktop.ts and the agent-room-desktop folder together
              into ~/.config/opencode/plugins. No password or binding file is needed.
            </p>
          ) : (
            <p className="small">
              Use the bundled agent-room-helper with <code>--mcp</code>
              {editing.data.app === "claude-channel"
                ? " and --claude-channel"
                : editing.data.app === "pull"
                  ? " and --claude-app"
                  : editing.data.app === "mcp"
                    ? " and --generic (set AGENT_ROOM_NATIVE, and optionally AGENT_ROOM_MODEL)"
                    : ""}.
              Replace the old Agent Room MCP command. The host supplies this
              conversation’s identity; never put a shared session ID in global
              configuration. Reload the MCP connection when the session is ready.
            </p>
          )}
          {editing.data.app === "claude-channel" && (
            <p className="small">
              For the Claude Code CLI research preview, launch with <code>
                --dangerously-load-development-channels server:agent-room
              </code>. This opts in the custom channel only. If the Desktop Code
              host cannot provide an equivalent launch opt-in and native session
              identity, push delivery remains unsupported there. A loaded MCP
              tool list or active helper process does not establish receipt.
            </p>
          )}
          <p className="small">
            A receipt means the receiving agent explicitly confirmed reading.
            “Submitted” only means its app accepted the prompt.
          </p>
          <button className="primary wide" onClick={() => setDialog("")}>
            Done
          </button>
        </Dialog>
      )}
      {dialog.startsWith("workflow") && (
        <Workflow
          editing={editing}
          kind={dialog.split(":")[1]}
          sessions={activeSessions}
          busy={busy}
          onClose={() => setDialog("")}
          onSave={(data) => act("object", data)}
        />
      )}
      {palette && (
        <Palette
          s={s}
          onClose={() => setPalette(false)}
          onExecute={(a) => {
            setPalette(false);
            if (a.id === "goto-room") {
              setView("room");
              setQuery("");
            } else if (a.id === "goto-inbox") {
              setView("inbox");
            } else if (a.id === "goto-objects") {
              setView("objects");
            } else if (a.id === "goto-settings") {
              setView("settings");
            } else if (a.id === "new-message") {
              setView("room");
              setQuery("");
              setTimeout(() => composer.current?.focus(), 50);
            } else if (a.id === "new-work") {
              setView("room");
              setEditing(null);
              setDialog("workflow:work");
            } else if (a.id === "new-plan") {
              setView("room");
              setEditing(null);
              setDialog("workflow:plan");
            } else if (a.id === "new-review") {
              setView("room");
              setEditing(null);
              setDialog("workflow:review");
            } else if (a.id === "new-decision") {
              setView("room");
              setEditing({
                id: crypto.randomUUID(),
                kind: "decision",
                version: 0,
                author: "",
                data: {},
              });
              setDialog("workflow");
            } else if (a.id === "connect") {
              setView("room");
              setDialog("connect");
            } else if (a.id.startsWith("msg-")) {
              const id = a.id.slice(4);
              setView("room");
              setQuery("");
              setTimeout(
                () =>
                  document
                    .getElementById("message-" + id)
                    ?.scrollIntoView({ block: "center" }),
                60,
              );
            } else if (a.id.startsWith("session-")) {
              const id = a.id.slice(8);
              setView("room");
              setQuery("");
              setTarget(id);
              setTimeout(() => composer.current?.focus(), 50);
            } else if (a.id.startsWith("object-")) {
              const id = a.id.slice(7);
              const o = s.objects.find((item) => item.id === id) || null;
              setView("room");
              setEditing(o);
              setDialog("workflow");
            }
          }}
        />
      )}
    </div>
  );
}
function Workflow({
  editing,
  kind: initialKind,
  sessions,
  busy,
  onClose,
  onSave,
}: {
  editing: ObjectItem | null;
  kind?: string;
  sessions: Session[];
  busy: boolean;
  onClose: () => void;
  onSave: (data: any) => Promise<any>;
}) {
  const [kind, setKind] = useState(editing?.kind || initialKind || "work");
  const d = editing?.data || {};
  return (
    <Dialog
      title={editing?.version ? "Update " + kind : "New request"}
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const value = (key: string) => String(f.get(key) || "");
          let data: Record<string, unknown> = {};
          if (kind === "plan")
            data = {
              objective: value("objective"),
              steps: value("steps").split("\n").filter(Boolean),
            };
          if (kind === "work")
            data = {
              title: value("title"),
              owner: value("owner"),
              scope: value("scope"),
              state: value("state"),
              evidence: value("evidence"),
            };
          if (kind === "decision")
            data = { text: value("text"), state: value("state") };
          if (kind === "review")
            data = {
              artifact: value("artifact"),
              revision: value("revision"),
              base: value("base"),
              reviewer: value("owner"),
              verdict: "pending",
              checks: value("checks"),
              findings: "",
            };
          void onSave({
            id: editing?.id || crypto.randomUUID(),
            type: kind,
            version: (editing?.version || 0) + 1,
            data,
          }).catch(() => {});
        }}
      >
        <label>
          Type
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            disabled={!!editing?.version}
          >
            <option value="work">Work request</option>
            <option value="plan">Shared plan</option>
            <option value="decision">Decision</option>
            <option value="review">Review packet</option>
          </select>
        </label>
        {kind === "plan" ? (
          <>
            <label>
              Objective
              <input
                name="objective"
                defaultValue={d.objective}
                required
                placeholder="What are we trying to achieve?"
              />
            </label>
            <label>
              Next steps · one per line
              <textarea
                name="steps"
                defaultValue={d.steps?.join("\n")}
                required
                rows={5}
              />
            </label>
          </>
        ) : kind === "decision" ? (
          <>
            <label>
              Decision
              <textarea name="text" defaultValue={d.text} required rows={4} />
            </label>
            <label>
              Status
              <select name="state" defaultValue={d.state || "proposed"}>
                {["proposed", "accepted", "superseded"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <p className="small">
              Accepting records you as the decision maker. It doesn’t grant new
              tool permissions.
            </p>
          </>
        ) : (
          <>
            {kind === "work" ? (
              <>
                <label>
                  Request
                  <input
                    name="title"
                    defaultValue={d.title}
                    required
                    placeholder="Review the delivery recovery behavior"
                  />
                </label>
                <label>
                  Scope and acceptance
                  <textarea name="scope" defaultValue={d.scope} rows={3} />
                </label>
              </>
            ) : (
              <>
                <label>
                  Artifact
                  <input
                    name="artifact"
                    defaultValue={d.artifact}
                    required
                    placeholder="Repository / artifact reference"
                  />
                </label>
                <div className="form-grid">
                  <label>
                    Exact revision
                    <input
                      name="revision"
                      defaultValue={d.revision}
                      required
                      placeholder="Commit or content digest"
                    />
                  </label>
                  <label>
                    Base revision
                    <input name="base" defaultValue={d.base} required />
                  </label>
                </div>
                <label>
                  Checks and test evidence
                  <textarea name="checks" defaultValue={d.checks} rows={3} />
                </label>
                <p className="small">
                  Only the exact reviewer can issue a verdict through their room
                  tools. Changing the artifact resets approval.
                </p>
              </>
            )}
            <label>
              {kind === "review" ? "Reviewer" : "Owner"}
              <select
                name="owner"
                defaultValue={d.owner || d.reviewer || ""}
                required
              >
                <option value="" disabled>
                  Choose an exact conversation
                </option>
                {sessions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} · {appName(p.app)}
                  </option>
                ))}
              </select>
            </label>
            {kind === "work" && (
              <>
                <label>
                  Status
                  <select name="state" defaultValue={d.state || "proposed"}>
                    {[
                      "proposed",
                      "accepted",
                      "working",
                      "blocked",
                      "ready for review",
                      "resolved",
                      "cancelled",
                    ].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Completion evidence
                  <textarea
                    name="evidence"
                    defaultValue={d.evidence}
                    rows={2}
                  />
                </label>
              </>
            )}
          </>
        )}
        <button className="primary wide" disabled={busy}>
          Save {kind} <Check size={15} />
        </button>
      </form>
    </Dialog>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
