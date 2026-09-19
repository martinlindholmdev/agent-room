"""B6 real HTTP contract tests; in-memory fake node, no helper profile or vault."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import Mock
import pytest
from desktop_main import handler
from desktop.control_contract import result_envelope

@pytest.fixture
def endpoint():
    node = Mock()
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(node, 'synthetic'))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(action='object', contract=True, credential='synthetic'):
        body = {'action': action, 'data': {}}
        if contract: body['contract'] = 1
        req = Request('http://127.0.0.1:%s/control' % server.server_port,
                      json.dumps(body).encode(), {'Authorization': 'Bearer '+credential})
        try: response = urlopen(req, timeout=2)
        except HTTPError as exc: response = exc
        with response: return response.status, json.load(response)
    yield node, call
    server.shutdown(); server.server_close(); thread.join(2)

def test_success_and_legacy_consumers(endpoint):
    node, call = endpoint
    node.control.return_value = {'id': 'event', 'state': 'saved'}
    assert call()[1] == {'ok': True, 'result': node.control.return_value}
    assert call(contract=False)[1] == node.control.return_value

def test_snapshot_error_is_operational_data(endpoint):
    node, call = endpoint
    node.control.return_value = {'error': 'Delivery needs attention', 'health': [{'scope':'delivery'}]}
    body = call('snapshot')[1]
    assert body['ok'] is True
    assert body['result']['sessions'] == []
    assert body['result']['objects'] == []

@pytest.mark.parametrize('exc,status', [(ValueError('Bearer PRIVATE'),400), (OSError('proof=PRIVATE'),503), (KeyError('PRIVATE'),400)])
def test_exceptions_do_not_claim_rejection_or_leak_credentials(endpoint, exc, status):
    node, call = endpoint
    node.control.side_effect = exc
    code, body = call()
    assert code == status
    assert body['error']['acceptance'] == 'uncertain'
    assert 'PRIVATE' not in json.dumps(body)

def test_explicit_enqueue_rejection_and_auth(endpoint):
    node, call = endpoint
    node.control.return_value = {'error':'PRIVATE', 'acceptance':'rejected'}
    assert call()[1] == {'ok':False,'error':{'code':'rejected','acceptance':'rejected'}}
    assert call(credential='wrong')[1] == {'ok':False,'error':{'code':'unauthorized','acceptance':'rejected'}}

def test_unknown_failure_is_not_rejection():
    assert result_envelope('object', {'error':'PRIVATE'})['error']['acceptance'] == 'uncertain'

def test_health_scopes_survive_unrelated_sync():
    # Reuse isolated work/ fixture setup without starting native dispatch.
    import tempfile
    from pathlib import Path
    from desktop.node import Node
    from desktop.secrets import MemoryVault
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'work') as home:
        node = Node(Path(home), MemoryVault(), allow_loopback=True)
        try:
            node.setup('Synthetic B6')
            node.health.update(delivery=True, stream=True, sync=True)
            node.sync_once()
            assert node.snapshot()['health'] == [{'scope':'delivery'}, {'scope':'stream'}]
        finally:
            node.stop.set(); node.db.close(); node.delivery.db.close(); node.hub.db.close()
