"""B4 isolated protocol/enqueue regressions; no installed profile."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from desktop.node import Node
from desktop.protocol import uid
from desktop.secrets import MemoryVault

@pytest.fixture
def node():
    root = Path(__file__).resolve().parents[1] / 'work'
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='b4-test-', dir=root) as home:
        n = Node(Path(home), MemoryVault(), allow_loopback=True)
        n.setup('Synthetic B4')
        yield n
        n.stop.set()
        n.db.close()
        n.delivery.db.close()
        n.hub.db.close()

def packet(data, identity, version, sender=''):
    return {'version': 1, 'id': uid(), 'room': 'general', 'sender': sender,
            'generation': 1, 'kind': 'object',
            'body': {'id': identity, 'type': 'review', 'version': version, 'data': data}}

@pytest.mark.parametrize('verdict', ['approved', 'changes requested', 'pending'])
def test_preserve_review_and_reject_forgery(node, verdict):
    # Bootstrap device is available through the local node's authenticated call.
    reviewer = node.bind({'native': uid(), 'app': 'mcp', 'title': 'Reviewer'})
    identity = uid()
    d = dict(artifact='patch', revision='r1', base='b1', reviewer=reviewer['id'],
             verdict=verdict, checks='passed', findings=['finding'])
    node.call('event', packet(d, identity, 1, reviewer['id']))
    changed = dict(d, checks='additional checks')
    node.call('event', packet(changed, identity, 2))
    saved = node.call('snapshot', {'room':'general'})['objects'][0]
    assert saved['data']['verdict'] == verdict
    assert saved['data']['findings'] == ['finding']
    for forged in [dict(changed, findings=[]), dict(changed, verdict='approved' if verdict != 'approved' else 'pending')]:
        with pytest.raises(ValueError):
            node.call('event', packet(forged, identity, 3))

@pytest.mark.parametrize('field', ['artifact', 'revision', 'base'])
def test_only_artifact_identity_changes_invalidate(node, field):
    reviewer = node.bind({'native': uid(), 'app': 'mcp', 'title': 'Reviewer'})
    identity = uid()
    d = dict(artifact='patch', revision='r1', base='b1', reviewer=reviewer['id'],
             verdict='approved', checks='passed', findings=['old finding'])
    node.call('event', packet(d, identity, 1, reviewer['id']))
    changed = dict(d, **{field:'changed'})
    with pytest.raises(ValueError):
        node.call('event', packet(changed, identity, 2))
    changed['verdict'] = 'pending'
    node.call('event', packet(changed, identity, 2))
    saved = node.call('snapshot', {'room':'general'})['objects'][0]['data']
    assert saved['verdict'] == 'pending' and saved['findings'] == ''

def test_enqueue_rejection_is_explicit_only_without_persisted_event(node):
    data = {'event_id':uid(), 'id':uid(), 'type':'plan', 'version':1,
            'data':{'objective':'Plan', 'steps':[]}}
    with patch('desktop.node.MAX_QUEUE', 0):
        assert node.control('object', data)['acceptance'] == 'rejected'
    assert not node.rows('SELECT * FROM outbox')
    accepted = node.control('object', data)
    assert accepted['state'] == 'saved'
    assert node.control('object', data)['id'] == accepted['id']
    with pytest.raises(ValueError):
        node.control('object', dict(data, version=2))
    with patch.object(node.work, 'set', side_effect=ValueError('after persistence')):
        with pytest.raises(ValueError):
            node.control('object', dict(data, event_id=uid()))
    with patch.object(node, 'enqueue', side_effect=OSError('unknown')):
        with pytest.raises(OSError):
            node.control('object', dict(data, event_id=uid()))
