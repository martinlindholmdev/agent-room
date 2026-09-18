#!/bin/bash
# Seed a test helper home with content for every view, for the 2026-09-18 UX review.
#
# This is review scaffolding only. It touches no product code and only ever talks
# to a test helper on an isolated home -- never the installed app or
# ~/Library/Application Support/Agent Room.
#
# Usage, from the repo root:
#   python3 desktop_main.py --home work/desktop-test &     # start the helper first
#   docs/review-2026-09-18/seed.sh                         # then seed it
#
#   HOME_DIR=work/desktop-other docs/review-2026-09-18/seed.sh
#
# To start over from an empty app, stop the helper, delete the home, start it again
# and re-run this script:
#   rm -rf work/desktop-test
#
# Re-running against an already-seeded home is safe: every step is reported and
# the steps that cannot repeat (device setup, room create, the objects' version 1)
# are skipped with a note rather than failing the run.

set -euo pipefail
cd "$(dirname "$0")/../.."
HOME_DIR="${HOME_DIR:-work/desktop-test}"

if [ ! -f "$HOME_DIR/ready.json" ]; then
  echo "No $HOME_DIR/ready.json. Start the test helper first:"
  echo "  python3 desktop_main.py --home $HOME_DIR &"
  exit 1
fi

HOME_DIR="$HOME_DIR" python3 - <<'PY'
import json, os, time, urllib.error, urllib.request

home = os.environ['HOME_DIR']
ready = json.load(open(home + '/ready.json'))


def call(action, data=None):
    request = urllib.request.Request(
        'http://127.0.0.1:%d/control' % ready['port'],
        data=json.dumps({'action': action, 'data': data or {}}).encode(),
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + ready['token']})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def step(label, action, data=None):
    """Run one seeding call. A rejection is reported, not fatal: most rejections
    here mean 'already seeded', which must not stop the rest of the run."""
    try:
        result = call(action, data)
        print('  ok    %s' % label)
        return result
    except urllib.error.HTTPError as error:
        detail = error.read().decode().strip()
        print('  skip  %s -- %s' % (label, detail))
        return None


print('1. device setup')
# The name is what the setup screen asks for. Only possible once per home.
step('name this node "Review M1"', 'create', {'name': 'Review M1'})

print('2. rooms')
step('rename the default room to "General"', 'room-rename',
     {'room': 'general', 'title': 'General'})
# room-create always makes a new room; it is not idempotent and a second run
# would add "Release work" again as release-work-2. Only create it if a room
# with that title is not already there.
if any(r['title'] == 'Release work' for r in call('snapshot')['rooms']):
    print('  skip  create room "Release work" -- already exists')
else:
    step('create room "Release work"', 'room-create', {'title': 'Release work'})
    # room-create switches the active room to the new room and the room list
    # only contains it after the next hub sync, so wait before binding into it.
    time.sleep(3)

print('3. agents, one per connector type')
# codex-queue requires a canonical UUID native identity (desktop/protocol.py).
# pull and mcp are the two PULL_LIKE read-on-demand connectors.
CODEX_NATIVE = '11111111-2222-4333-8444-555555555555'
step('bind a codex-queue agent into "Release work"', 'bind',
     {'native': CODEX_NATIVE, 'app': 'codex-queue',
      'title': 'Codex \u2014 release notes', 'room': 'release-work'})
step('bind a pull agent into "Release work"', 'bind',
     {'native': 'seed-claude-01', 'app': 'pull',
      'title': 'Claude app \u2014 triage', 'room': 'release-work'})
step('bind an mcp agent into "General"', 'bind',
     {'native': 'seed-generic-01', 'app': 'mcp',
      'title': 'Generic MCP \u2014 docs', 'room': 'general'})

bindings = {b['app']: b['id'] for b in call('snapshot')['bindings']}

print('4. one pending connection request (Inbox -> Connection requests)')
step('request from an unbound session', 'request-create',
     {'native': 'seed-pending-01', 'app': 'pull',
      'title': 'Claude app \u2014 new conversation',
      'directory': '/Users/irislindholm/Code', 'model': 'claude-sonnet-4-5'})

print('5. messages')
step('switch to "Release work"', 'room-select', {'room': 'release-work'})
for text in ['Kicking off the release review. Codex, can you draft the notes?',
             'Reminder: the cutoff is tonight.',
             'Here is a snippet we need to check:\n\n```python\n'
             'def total(rows):\n    return sum(r["amount"] for r in rows)\n```']:
    step('post: %s' % text.splitlines()[0][:44], 'send', {'text': text})
    time.sleep(0.3)

step('switch to "General"', 'room-select', {'room': 'general'})
step('post a board message in "General"', 'send',
     {'text': 'General room: anything to flag before the weekend?'})
if 'mcp' in bindings:
    step('post a message addressed to the mcp agent', 'send',
         {'text': 'Direct question for the docs agent \u2014 are the docs current?',
          'targets': [bindings['mcp']]})

print('6. objects: plan, work, review, decision')
step('switch to "Release work"', 'room-select', {'room': 'release-work'})
step('plan', 'object', {'id': 'seed-plan-1', 'type': 'plan', 'version': 1,
     'data': {'objective': 'Ship the 0.2 release',
              'steps': ['Draft release notes', 'Review the delivery path',
                        'Tag and publish']}})
if 'codex-queue' in bindings:
    # work requires an owner that is an exact session in this room.
    step('work request owned by the codex agent', 'object',
         {'id': 'seed-work-1', 'type': 'work', 'version': 1,
          'data': {'title': 'Draft the release notes', 'state': 'working',
                   'owner': bindings['codex-queue']}})
if 'pull' in bindings:
    # review requires an exact reviewer session in this room.
    step('review awaiting a verdict', 'object',
         {'id': 'seed-review-1', 'type': 'review', 'version': 1,
          'data': {'artifact': 'release-notes.md', 'revision': '1',
                   'base': 'main', 'verdict': 'pending',
                   'reviewer': bindings['pull']}})
step('accepted decision', 'object',
     {'id': 'seed-decision-1', 'type': 'decision', 'version': 1,
      'data': {'text': 'Retire OpenCode as a supported connector',
               'state': 'accepted'}})

print('7. presence, including one agent left quiet')
# Presence is self-reported only (desktop/node.py set_binding_state); nothing
# here infers it from activity. The mcp agent is deliberately left at its
# default 'idle' and is never connected, so it stands in for a quiet agent.
if 'codex-queue' in bindings:
    step('codex agent reports "working"', 'binding-state',
         {'binding': bindings['codex-queue'], 'state': 'working'})
if 'pull' in bindings:
    step('pull agent reports "blocked"', 'binding-state',
         {'binding': bindings['pull'], 'state': 'blocked'})
print('  note  the mcp agent is left idle and unconnected as the quiet agent')

time.sleep(2)
snapshot = call('snapshot')
print()
print('seeded: %d rooms, %d agents, %d pending request(s), %d events, '
      'needsYou=%d' % (len(snapshot['rooms']), len(snapshot['bindings']),
                       len(snapshot['requests']), len(snapshot['events']),
                       snapshot['needsYou']))
print('active room: %s' % snapshot['activeRoom'])
PY

echo
echo "Now open the dev preview:"
echo "  cd apps/desktop && node_modules/.bin/vite --host 127.0.0.1"
echo "  http://127.0.0.1:1420"
