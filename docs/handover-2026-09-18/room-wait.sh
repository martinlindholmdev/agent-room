#!/bin/bash
# room-wait.sh BINDING_ID [AFTER_SEQ] [MAX_SECONDS]
#
# Generic "wait for my next message" for ANY agent that has a shell, against the
# installed Agent Room build (no code change). Blocks until a targeted message
# addressed to this binding is pending with hub seq > AFTER_SEQ, then prints ONE
# line and exits 0. Exits 2 on timeout, 3 if the binding is gone.
#
# Uses only the local control API the helper itself uses (ready.json port+token,
# control action `watch-next`, node.py:756-769). Native id and generation are
# resolved from the live snapshot on every poll, because the helper bumps every
# binding's generation on restart (node.py:131-133).
#
# Limitation of today's build: watch-next only sees TARGETED deliveries
# (room_post with to_session). Board posts (targets=[]) never create a delivery
# row and are invisible here. The room_wait tool described in
# fable-coordination.md fixes that by waiting on the cache seq instead.

B="$1"; AFTER="${2:-0}"; MAX="${3:-1500}"
HOME_DIR="${AGENT_ROOM_DESKTOP_HOME:-$HOME/Library/Application Support/Agent Room}"
[ -n "$B" ] || { echo "usage: room-wait.sh BINDING_ID [AFTER_SEQ] [MAX_SECONDS]" >&2; exit 64; }
end=$(( $(date +%s) + MAX ))
while [ "$(date +%s)" -lt "$end" ]; do
  r=$(python3 - "$HOME_DIR" "$B" <<'EOF'
import json, sys, urllib.request
home, b = sys.argv[1:]
try:
    ready = json.load(open(home + '/ready.json'))
    def call(action, data):
        req = urllib.request.Request('http://127.0.0.1:%d/control' % ready['port'],
            data=json.dumps({'action': action, 'data': data}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + ready['token']})
        return json.load(urllib.request.urlopen(req, timeout=10))
    binding = next((x for x in call('snapshot', {})['bindings'] if x['id'] == b), None)
    if binding is None:
        print('GONE'); sys.exit()
    w = call('watch-next', {'binding': b, 'native': binding['native'], 'generation': binding['generation']})
    print(w['latest'])
except Exception:
    print('ERR')
EOF
)
  case "$r" in
    GONE) echo "Agent Room: binding $B no longer exists." ; exit 3 ;;
    ERR|0|"") ;;
    *) if [ "$r" -gt "$AFTER" ] 2>/dev/null; then
         echo "Agent Room: new message pending for you (hub seq $r). Call room_read, room_ack the delivery_ids with read_through, then reply with room_post(to_session=<from_session>, reply_to=<id>), then wait again with AFTER_SEQ=$r."
         exit 0
       fi ;;
  esac
  sleep 1
done
echo "Agent Room: no message within ${MAX}s; wait again."
exit 2
