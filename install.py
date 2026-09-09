#!/usr/bin/env python3
"""Plug the agent room into the AI apps on this machine.

Every app is given its own name in the room, so you can tell who said what.
Safe to run twice: it replaces its own entries and leaves everything else
alone. Every file it touches is backed up first.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.join(HERE, "room_mcp.py")
# /usr/bin/python3 is the stable path on macOS; sys.executable may point inside
# an app bundle that moves when that app updates.
PYTHON = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable


def backup(path):
    if os.path.exists(path):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        copy = "%s.before-agent-room-%s" % (path, stamp)
        shutil.copy2(path, copy)
        return copy
    return None



def drop_json_key(text, key):
    """Remove `"key": { ... }` and its trailing comma, counting braces.

    A regex cannot do this safely: the object contains nested objects, so the
    first closing brace is not the right one.
    """
    marker = '"%s"' % key
    start = text.find(marker)
    if start < 0:
        return text
    brace = text.find("{", start)
    if brace < 0:
        return text
    depth, i, in_string, escaped = 0, brace, False, False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    end = i + 1
    while end < len(text) and text[end] in ", ":
        end += 1
    while start > 0 and text[start - 1] in " \t":
        start -= 1
    if start > 0 and text[start - 1] == "\n":
        start -= 1
    return text[:start] + text[end:]


def env_for(agent, channel, url, token):
    env = {"AGENT_ROOM_AGENT": agent, "AGENT_ROOM_CHANNEL": channel, "AGENT_ROOM_URL": url}
    if token:
        env["AGENT_ROOM_TOKEN"] = token
    return env


# ---------------------------------------------------------------- Claude Code

def install_claude_code(agent, channel, url, token):
    if not shutil.which("claude"):
        return "skipped — the claude command is not installed"
    subprocess.run(["claude", "mcp", "remove", "-s", "user", "agent-room"],
                   capture_output=True, text=True)
    cmd = ["claude", "mcp", "add", "-s", "user", "agent-room"]
    for key, value in env_for(agent, channel, url, token).items():
        cmd += ["-e", "%s=%s" % (key, value)]
    cmd += ["--", PYTHON, BRIDGE]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return "failed — %s" % (result.stderr or result.stdout).strip()[:200]
    return "added as '%s'" % agent


# --------------------------------------------------- Codex / the ChatGPT app

def install_codex(agent, channel, url, token):
    path = os.path.expanduser("~/.codex/config.toml")
    if not os.path.isdir(os.path.dirname(path)):
        return "skipped — no ~/.codex directory"
    text = open(path).read() if os.path.exists(path) else ""
    backup(path)

    # drop any block we wrote before, then append a fresh one
    text = re.sub(r"\n*# --- agent room ---.*?# --- end agent room ---\n*", "\n", text, flags=re.S)
    text = re.sub(r"\n*\[mcp_servers\.agent_room\](?:\n(?!\[).*)*", "\n", text)

    env = env_for(agent, channel, url, token)
    env_line = ", ".join('%s = "%s"' % (k, v) for k, v in env.items())
    block = (
        "\n# --- agent room ---\n"
        "[mcp_servers.agent_room]\n"
        'command = "%s"\n'
        'args = ["%s"]\n'
        "env = { %s }\n"
        "# --- end agent room ---\n" % (PYTHON, BRIDGE, env_line)
    )
    open(path, "w").write(text.rstrip("\n") + "\n" + block)
    return "added as '%s' (this also covers Codex inside the ChatGPT app)" % agent


# ------------------------------------------------------------------ OpenCode

def install_opencode(agent, channel, url, token):
    path = os.path.expanduser("~/.config/opencode/opencode.jsonc")
    if not os.path.exists(path):
        return "skipped — no opencode config found"
    text = open(path).read()
    backup(path)

    text = drop_json_key(text, "agent-room")

    env = env_for(agent, channel, url, token)
    entry = (
        '\n    "agent-room": {\n'
        '      "type": "local",\n'
        '      "enabled": true,\n'
        '      "command": ["%s", "%s"],\n'
        '      "environment": {\n%s\n      }\n'
        '    },' % (PYTHON, BRIDGE,
                    ",\n".join('        "%s": "%s"' % (k, v) for k, v in env.items()))
    )
    if '"mcp"' not in text:
        return "skipped — no mcp section in the opencode config"
    text = re.sub(r'("mcp"\s*:\s*\{)', lambda m: m.group(1) + entry, text, count=1)
    open(path, "w").write(text)
    try:
        json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))
    except ValueError as exc:
        return "written, but the file no longer parses cleanly (%s) — restore the backup" % exc
    return "added as '%s'" % agent


# ------------------------------------------------- start the room at login

def install_launch_agent(port):
    label = "com.agentroom.daemon"
    path = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % label)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logs = os.path.expanduser("~/.agent-room/daemon.log")
    plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>%s</string>
  <key>ProgramArguments</key>
  <array><string>%s</string><string>%s</string><string>--port</string><string>%d</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>%s</string>
  <key>StandardErrorPath</key><string>%s</string>
</dict></plist>
""" % (label, PYTHON, os.path.join(HERE, "roomd.py"), port, logs, logs)
    open(path, "w").write(plist)
    subprocess.run(["launchctl", "unload", path], capture_output=True)
    result = subprocess.run(["launchctl", "load", path], capture_output=True, text=True)
    if result.returncode != 0:
        return "written but not loaded — %s" % (result.stderr or "").strip()[:160]
    return "the room now starts automatically at login"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine", default="", help="short label for this machine, e.g. m1")
    parser.add_argument("--channel", default="general")
    parser.add_argument("--url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", default=os.environ.get("AGENT_ROOM_TOKEN", ""))
    parser.add_argument("--no-login-start", action="store_true")
    args = parser.parse_args()

    machine = args.machine.strip() or re.sub(r"[^a-z0-9]+", "", os.uname().nodename.lower())[:8]
    suffix = "@" + machine if machine else ""
    port = int(args.url.rsplit(":", 1)[-1])

    print("Agent room -> %s   channel '%s'\n" % (args.url, args.channel))
    steps = [
        ("Claude Code", install_claude_code, "claude-code" + suffix),
        ("Codex / ChatGPT app", install_codex, "codex" + suffix),
        ("OpenCode", install_opencode, "opencode" + suffix),
    ]
    for label, fn, agent in steps:
        try:
            print("  %-22s %s" % (label + ":", fn(agent, args.channel, args.url, args.token)))
        except Exception as exc:
            print("  %-22s failed — %s" % (label + ":", exc))

    if not args.no_login_start:
        try:
            print("  %-22s %s" % ("Start at login:", install_launch_agent(port)))
        except Exception as exc:
            print("  %-22s failed — %s" % ("Start at login:", exc))

    print("\nOpen the room at %s" % args.url)
    print("Restart each app for it to pick up the new tools.")


if __name__ == "__main__":
    main()
