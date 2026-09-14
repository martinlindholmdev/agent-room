import { tool, type Plugin } from "@opencode-ai/plugin";
import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
// @ts-ignore JavaScript adapter deliberately has no runtime dependency.
import { submitExisting, incoming } from "./opencode-client.mjs";

type Binding = { id: string; native: string; app: string; directory?: string };

export const AgentRoomDesktop: Plugin = async ({ client, directory }) => {
  const root =
    process.env.AGENT_ROOM_DESKTOP_HOME ||
    join(homedir(), "Library/Application Support/Agent Room");
  let closed = false;
  const running = new Set<string>();
  const leases = new Map<string, { lease: string; generation: number }>();
  const local = async (action: string, data: Record<string, unknown> = {}) => {
    // Private local rendezvous rotates with every helper process. Never log it.
    const ready = JSON.parse(await readFile(join(root, "ready.json"), "utf8"));
    if (!Number.isInteger(ready.port) || ready.port < 1 || ready.port > 65535)
      throw Error("helper unavailable");
    const response = await fetch(`http://127.0.0.1:${ready.port}/control`, {
      method: "POST",
      redirect: "error",
      signal: AbortSignal.timeout(30000),
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ready.token}`,
      },
      body: JSON.stringify({ action, data }),
    });
    if (!response.ok) throw Error("desktop room unavailable");
    return response.json();
  };
  const bindings = async (): Promise<Binding[]> =>
    (await local("snapshot")).bindings.filter(
      (b: Binding) =>
        b.app === "opencode-bridge" &&
        b.directory &&
        resolve(b.directory) === resolve(directory),
    );
  const forSession = async (native: string): Promise<Binding> => {
    const matches = (await bindings()).filter((b) => b.native === native);
    if (matches.length !== 1)
      throw Error("Connect this exact native session in Agent Room first");
    return matches[0];
  };
  const pause = (ms: number) =>
    new Promise<void>((r) => {
      const timer = setTimeout(r, ms);
      timer.unref?.();
    });
  const pump = async (binding: Binding) => {
    if (running.has(binding.id)) return;
    running.add(binding.id);
    try {
      // Validate existing session with the host's authenticated client.
      const existing = await client.session.get({
        path: { id: binding.native },
        query: { directory },
      });
      if (
        existing.error ||
        existing.data?.id !== binding.native ||
        resolve(existing.data.directory) !== resolve(directory)
      )
        return;
      const opened = await local("bridge-open", {
        binding: binding.id,
        native: binding.native,
        app: "opencode-bridge",
      });
      leases.set(binding.id, opened);
      while (!closed) {
        // Avoid submitting into an already busy native session. No new session is
        // created, and native idempotency is not assumed from an optional ID.
        const status = await client.session.status({ query: { directory } });
        if (status.error) throw Error("native status unavailable");
        const current = status.data?.[binding.native];
        if (current && current.type !== "idle") {
          await local("bridge-heartbeat", {
            binding: binding.id,
            lease: opened.lease,
          });
          await pause(2000);
          continue;
        }
        const result = await local("bridge-next", {
          binding: binding.id,
          lease: opened.lease,
        });
        if (!result.delivery) continue;
        const state = await submitExisting(
          client,
          directory,
          binding.native,
          incoming(result.delivery, result.message),
        );
        await local("bridge-sent", {
          binding: binding.id,
          lease: opened.lease,
          delivery_id: result.delivery.id,
          state,
        });
      }
    } catch {
      /* Status stays unavailable/uncertain; never print host errors/secrets. */
    } finally {
      running.delete(binding.id);
    }
  };
  // Network bridge only: this timer never invokes a model itself. Queues are
  // consumed by authenticated long-poll and native session status gates sends.
  const discover = async () => {
    try {
      for (const binding of await bindings()) void pump(binding);
    } catch {}
  };
  const timer = setInterval(() => {
    if (!closed) void discover();
  }, 10000);
  timer.unref?.();
  void discover();
  const execute =
    (name: string) =>
    async (args: Record<string, unknown>, context: { sessionID: string }) => {
      const binding = await forSession(context.sessionID);
      const lease = leases.get(binding.id);
      if (!lease) throw Error("Desktop bridge not connected for this session");
      return JSON.stringify(
        await local("tool", {
          binding: binding.id,
          native: context.sessionID,
          generation: lease.generation,
          lease: lease.lease,
          name,
          args,
        }),
      );
    };
  return {
    event: async ({ event }) => {
      if (event.type === "server.instance.disposed") {
        closed = true;
        clearInterval(timer);
      }
      if (event.type === "session.created" || event.type === "session.idle")
        void discover();
    },
    tool: {
      desktop_room_read: tool({
        description:
          "Read oldest complete unread desktop room messages. Does not acknowledge.",
        args: {},
        execute: execute("room_read"),
      }),
      desktop_room_context: tool({
        description:
          "Read shared plans, decisions, requests and exact sessions.",
        args: {},
        execute: execute("room_context"),
      }),
      desktop_room_post: tool({
        description:
          "Reply in the desktop room using exact to_session and reply_to. Posting never acknowledges.",
        args: {
          text: tool.schema.string(),
          to_session: tool.schema.string().optional(),
          reply_to: tool.schema.string().optional(),
          request_id: tool.schema.string().optional(),
        },
        execute: execute("room_post"),
      }),
      desktop_room_ack: tool({
        description:
          "Acknowledge only complete messages you have actually read.",
        args: {
          delivery_ids: tool.schema.array(tool.schema.string()).optional(),
          read_through: tool.schema.number().int().optional(),
        },
        execute: execute("room_ack"),
      }),
      desktop_room_workflow: tool({
        description:
          "Create/update a versioned work request, plan, decision, review or advisory claim.",
        args: {
          id: tool.schema.string(),
          type: tool.schema.enum([
            "work",
            "plan",
            "decision",
            "review",
            "claim",
          ]),
          version: tool.schema.number().int(),
          data: tool.schema.record(tool.schema.string(), tool.schema.unknown()),
        },
        execute: execute("room_workflow"),
      }),
    },
  };
};
