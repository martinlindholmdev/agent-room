"""Isolated deterministic presence probe; no installed helper or credentials."""
import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from desktop.node import Node
from desktop.secrets import MemoryVault

with tempfile.TemporaryDirectory(prefix='phase5-', dir='work') as home:
    vault = MemoryVault()
    node = Node(Path(home), vault)
    node.setup('Phase 5 isolated')
    bindings = [node.bind({'app': app, 'native': 'phase5-' + app, 'title': 'Quiet ' + app})
                for app in ['mcp', 'pull', 'claude-channel']]
    for b in bindings:
        node.set_binding_state(b['id'], 'working')
    node.sync_once()
    channel = bindings[-1]
    node.bridge_open(channel['id'], channel['native'], channel['app'])
    with patch('time.time', return_value=time.time() + 86400), patch('time.monotonic', return_value=time.monotonic() + 86400):
        node.delivery.expire_channels()
        node.sync_once()
        snap = node.snapshot()
        print(json.dumps({'simulated_elapsed_seconds':86400, 'activeCount':snap['activeCount'],
          'bindings':[{'app': b['app'], 'state':b['state'], 'bridge_connected':b['bridge_connected']} for b in snap['bindings']],
          'hub_active':[s['active'] for s in snap['sessions']],
          'local_delivery_active': {b['app']: bool(node.delivery.db.execute('SELECT active FROM sessions WHERE id=?',(b['id'],)).fetchone()[0]) for b in bindings}}))
    node.db.close(); node.delivery.db.close(); node.hub.db.close()
    node = Node(Path(home), vault)
    node.sync_once()
    print(json.dumps({'restart_working_count': node.snapshot()['activeCount']}))
    # Simulate offline removal and return of hub; no network or live process touched.
    gone = bindings[0]
    with patch.object(node, 'call', side_effect=OSError('isolated offline fixture')):
        result = node.binding_remove(gone['id'])
    node.sync_once()
    snap = node.snapshot()
    print(json.dumps({'offline_remove':result['removed'], 'local_binding_gone':not any(b['id']==gone['id'] for b in snap['bindings']),
      'hub_session_still_active':next(s['active'] for s in snap['sessions'] if s['id']==gone['id'])}))
    remaining = bindings[1]
    node.binding_remove(remaining['id']); node.sync_once()
    print(json.dumps({'online_remove_hub_active':next(s['active'] for s in node.snapshot()['sessions'] if s['id']==remaining['id'])}))
    node.db.close(); node.delivery.db.close(); node.hub.db.close()
