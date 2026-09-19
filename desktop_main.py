#!/usr/bin/env python3
"""Frozen helper entry point; also runs MCP in the exact configured binding."""
import argparse
import fcntl
import hashlib
import json
import os
import secrets
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from desktop.node import Node, hub_call
from desktop.secrets import Vault
from desktop.control_contract import failure, result_envelope


def default_root():
    return Path(os.environ.get('AGENT_ROOM_DESKTOP_HOME', str(Path.home()/'Library/Application Support/Agent Room')))


def local_call(root, action, data):
    import urllib.request
    ready = json.loads((Path(root)/'ready.json').read_text())
    request = urllib.request.Request('http://127.0.0.1:%d/control' % ready['port'],
        data=json.dumps({'action': action, 'data': data}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+ready['token']})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def handler(node, token, protocol_only=False):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass  # No request bodies, URLs or native credentials in diagnostics.

        def send(self, code, body):
            if getattr(self, 'contract', False) and not (isinstance(body, dict) and 'ok' in body):
                body = failure('unauthorized' if code == 401 else 'rejected' if code in (403, 404, 413) else 'unavailable',
                               'rejected' if code in (401, 403, 404, 413) else 'uncertain')
            payload = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            self.send(404, {'error': 'use the authenticated protocol'})

        def do_POST(self):
            self.contract = False
            self.connection.settimeout(8)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 250_000:
                    self.close_connection = True
                    return self.send(413, {'error': 'request too large or empty'})
                if self.headers.get('Origin'):
                    return self.send(403, {'error': 'browser origin not permitted on helper API'})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('JSON object required')
                self.contract = not protocol_only and body.get('contract') == 1
                credential = self.headers.get('Authorization', '').removeprefix('Bearer ')
                if protocol_only:
                    if not self.path.startswith('/v1/') or not node.hub:
                        return self.send(404, {'error': 'no such protocol route'})
                    result = hub_call(node.hub, credential, self.path[4:], body)
                else:
                    if not secrets.compare_digest(credential, token):
                        return self.send(401, {'error': 'local authentication required'})
                    if self.path != '/control':
                        return self.send(404, {'error': 'no such local route'})
                    result = node.control(body['action'], body.get('data', {}))
                self.send(200, result_envelope(body['action'], result) if self.contract else result)
            except (ValueError, KeyError, TypeError, AttributeError):
                self.send(400, {'error': 'Request rejected. Check exact session, pairing, fields and revision.'})
            except Exception:
                self.send(503, {'error': 'Operation unavailable; local messages are retained.'})
    return Handler


def serve(root, port=0, hub_port=0, ready_stdout=False):
    os.umask(0o077)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    owner = open(root/'helper.lock', 'a')
    try:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('another helper owns this desktop profile')
    # Bind before opening/recovering either database.
    local = ThreadingHTTPServer(('127.0.0.1', port), BaseHTTPRequestHandler)
    listener = root/'listener.json'
    if not hub_port and listener.exists():
        hub_port = json.loads(listener.read_text())['hub_port']
    protocol = ThreadingHTTPServer(('127.0.0.1', hub_port), BaseHTTPRequestHandler)
    listener.write_text(json.dumps({'hub_port': protocol.server_port}))
    vault = Vault(hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:24])
    node = Node(root, vault)
    token = secrets.token_urlsafe(48)
    local.RequestHandlerClass = handler(node, token)
    protocol.RequestHandlerClass = handler(node, '', True)
    local.daemon_threads = protocol.daemon_threads = True
    node.put('hub_port', protocol.server_port)
    ready = {'port': local.server_port, 'hub_port': protocol.server_port, 'token': token, 'pid': os.getpid(), 'version': '0.1.0'}
    temp = root/'ready.tmp'
    temp.write_text(json.dumps(ready))
    os.replace(temp, root/'ready.json')
    if ready_stdout:
        # Machine-only pipe for a native launcher; never print credentials.
        print(json.dumps({'port': local.server_port, 'hub_port': protocol.server_port}), flush=True)
    node.start()
    threading.Thread(target=protocol.serve_forever, daemon=True).start()
    def shutdown(*_):
        node.stop.set()
        threading.Thread(target=local.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        local.serve_forever()
    finally:
        node.stop.set()
        protocol.shutdown()
        local.server_close()
        protocol.server_close()
        (root/'ready.json').unlink(missing_ok=True)
        owner.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=default_root())
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--hub-port', type=int, default=0)
    parser.add_argument('--mcp', action='store_true')
    parser.add_argument('--binding')
    parser.add_argument('--claude-channel', action='store_true')
    parser.add_argument('--claude-app', action='store_true')
    parser.add_argument('--generic', action='store_true', help='Run as a generic, self-identified MCP connector (app=mcp); read-on-demand, no push.')
    parser.add_argument('--native', help='Native session identity for --generic mode; falls back to AGENT_ROOM_NATIVE.')
    parser.add_argument('--watch-socket')
    parser.add_argument('--watch-seconds', type=int, default=1800)
    parser.add_argument('--restore-from', type=Path)
    parser.add_argument('--stage-legacy', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--tool', choices=['room_read', 'room_post', 'room_ack', 'room_sessions', 'room_context', 'room_workflow'])
    args = parser.parse_args()
    if args.watch_socket:
        if args.mcp or args.tool or args.claude_app or args.claude_channel or args.generic:
            parser.error('--watch-socket is only a native Monitor stdout client')
        from desktop.monitor import watch_socket
        watch_socket(args.home, args.watch_socket, args.watch_seconds)
    elif args.restore_from or args.stage_legacy:
        if not args.destination:parser.error('--destination required')
        from desktop.recovery import restore, stage_legacy
        result=restore(args.restore_from,args.destination) if args.restore_from else stage_legacy(args.stage_legacy,args.destination)
        print(json.dumps(result))
    elif args.mcp:
        if sum((args.claude_channel, args.claude_app, args.generic)) > 1:
            parser.error('select only one of --claude-channel, --claude-app, --generic')
        if args.native and not args.generic:
            parser.error('--native only applies to --generic')
        from desktop.mcp import run
        run(args.home, args.binding, args.claude_channel, args.claude_app, args.generic, args.native)
    elif args.tool:
        if not args.binding:
            parser.error('--binding required')
        bindings=local_call(args.home,'snapshot',{})['bindings']
        binding=next((b for b in bindings if b['id']==args.binding),None)
        native=os.environ.get('CODEX_THREAD_ID')
        if not binding or binding['app']!='codex-queue' or native!=binding['native']:
            parser.error('this tool fallback requires the exact Codex task identity supplied by its host; other agents use their native bridge')
        result = local_call(args.home, 'tool', {'binding': args.binding, 'native':native,'generation':binding['generation'],'name': args.tool, 'args': json.load(sys.stdin)})
        print(json.dumps(result, ensure_ascii=False))
    else:
        serve(args.home, args.port, args.hub_port)


if __name__ == '__main__':
    main()
