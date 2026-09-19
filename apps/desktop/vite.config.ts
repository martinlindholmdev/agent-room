import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
// Development only. The installed renderer uses a narrow Rust IPC command;
// credentials never enter JavaScript or the Vite bundle.
export default defineConfig({
  plugins: [
    react(),
    {
      name: "local-preview",
      configureServer(server) {
        server.middlewares.use("/control", async (req, res) => {
          if (req.method !== "POST") {
            res.statusCode = 405;
            res.end();
            return;
          }
          try {
            const origin = req.headers.origin;
            if (
              origin &&
              !/^http:\/\/(127\.0\.0\.1|localhost):1420$/.test(origin)
            )
              throw Error("origin");
            const ready = JSON.parse(
              fs.readFileSync(
                process.env.AGENT_ROOM_READY ||
                  "../../work/desktop-test/ready.json",
                "utf8",
              ),
            );
            const chunks: Buffer[] = [];
            for await (const chunk of req) {
              chunks.push(chunk);
              if (Buffer.concat(chunks).length > 250000) throw Error("size");
            }
            const result = await fetch(
              `http://127.0.0.1:${ready.port}/control`,
              {
                method: "POST",
                signal: AbortSignal.timeout(8000),
                redirect: "error",
                headers: {
                  Authorization: `Bearer ${ready.token}`,
                  "Content-Type": "application/json",
                },
                body: Buffer.concat(chunks).toString(),
              },
            );
            res.statusCode = result.status;
            res.setHeader("Content-Type", "application/json");
            res.end(await result.text());
          } catch {
            res.statusCode = 503;
            res.end(JSON.stringify({ ok: false, error: { code: "unavailable", acceptance: "uncertain" } }));
          }
        });
      },
    },
  ],
  server: { port: 1420, strictPort: true },
  clearScreen: false,
});
