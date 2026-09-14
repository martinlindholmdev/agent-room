import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from desktop.legacy import Legacy
from desktop.node import Node
from desktop.secrets import MemoryVault
from desktop.protocol import uid


class LegacyBridgeTests(unittest.TestCase):
    def test_existing_claude_route_reply_and_receipt_without_new_native_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            env=dict(os.environ,AGENT_ROOM_HOME=str(root/'legacy'),AGENT_ROOM_PORT=str(port),AGENT_ROOM_TOKEN='')
            process=subprocess.Popen([sys.executable,'roomd.py'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            node=Node(root/'desktop',MemoryVault());node.setup('Fixture Mac');node.put('legacy_port',port)
            bridge=Legacy(node,port)
            try:
                for _ in range(60):
                    try:bridge.call('/api/health');break
                    except Exception:time.sleep(.05)
                native=uid();room_session=native+'-channel'
                bridge.call('/api/join',{'channel':'general','agent':'fixture@local'})
                bridge.call('/api/register',{'channel':'general','agent':'fixture@local','session':room_session,'adapter':'claude-channel'})
                binding=node.control('bind-local',{'session':room_session,'native':native,'title':'Existing fixture conversation'})
                original=node.enqueue('message',{'text':'Synthetic request','targets':[binding['id']]})
                node.sync_once()
                with node.delivery.db:node.delivery.db.execute('UPDATE deliveries SET updated=0')
                bridge.outbox()
                link=node.rows('SELECT * FROM legacy_links')[0]
                receipt=bridge.call('/api/delivery?channel=general&message='+link['legacy_message'])['deliveries'][0]
                self.assertEqual(room_session,receipt['session'])
                bridge.call('/api/ack',{'channel':'general','session':room_session,'delivery_ids':[receipt['id']]})
                reply=bridge.call('/api/post',{'channel':'general','from':'fixture@local','from_session':room_session,'to_session':bridge.session,
                    'text':'[desktop-reply:'+original['id']+'] Synthetic reply'})
                bridge.outbox();bridge.receive(0);node.sync_once()
                snapshot=node.snapshot()
                self.assertEqual('acknowledged',snapshot['receipts'][0]['state'])
                message=next(e for e in snapshot['events'] if e['body'].get('text')=='Synthetic reply')
                self.assertEqual(original['id'],message['body']['reply_to'])
                self.assertEqual(binding['id'],message['sender'])
                # Replaying a lost POST response reuses the original v2 journal ID.
                with node.lock,node.db:node.db.execute('UPDATE legacy_links SET legacy_message=NULL')
                bridge.outbox()
                self.assertEqual(link['legacy_message'],node.rows('SELECT * FROM legacy_links')[0]['legacy_message'])
                all_messages=bridge.call('/api/messages?channel=general')['messages']
                self.assertEqual(2,len(all_messages))
            finally:
                process.terminate();process.wait(timeout=5)
                node.db.close();node.delivery.db.close();node.hub.db.close()


if __name__=='__main__':unittest.main()
