"""Real HTTP + stdio boundaries; synthetic MCP client, not an LLM receipt claim."""
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); cls.port=sock.getsockname()[1]
        cls.url='http://127.0.0.1:'+str(cls.port)
        env=dict(os.environ,AGENT_ROOM_HOME=cls.tmp.name,AGENT_ROOM_PORT=str(cls.port),AGENT_ROOM_TOKEN='synthetic-test-token')
        cls.daemon=subprocess.Popen([sys.executable,str(ROOT/'roomd.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.url+'/api/health',timeout=.1).close();break
            except OSError:time.sleep(.05)
        else:raise RuntimeError('synthetic daemon did not start')

    @classmethod
    def tearDownClass(cls):
        cls.daemon.terminate();cls.daemon.wait(timeout=5);cls.tmp.cleanup()

    def http(self,path,data=None,token='synthetic-test-token'):
        req=urllib.request.Request(self.url+path,json.dumps(data).encode() if data is not None else None,{'Content-Type':'application/json','Authorization':'Bearer '+token})
        return json.load(urllib.request.urlopen(req,timeout=5))

    def client(self,channel,session,notifications=False):
        env=dict(os.environ,AGENT_ROOM_URL=self.url,AGENT_ROOM_AGENT='synthetic-client',AGENT_ROOM_CHANNEL=channel,AGENT_ROOM_SESSION=session,AGENT_ROOM_TOKEN='synthetic-test-token',AGENT_ROOM_AUTOSTART='0',AGENT_ROOM_CLAUDE_CHANNEL='1' if notifications else '0')
        p=subprocess.Popen([sys.executable,str(ROOT/'room_mcp.py')],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
        def close():
            p.terminate();p.wait(timeout=5);p.stdin.close();p.stdout.close()
        self.addCleanup(close)
        return p

    def receive(self,p,timeout=5):
        data=b'';deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if select.select([p.stdout],[],[],max(0,deadline-time.monotonic()))[0]:
                ch=os.read(p.stdout.fileno(),1)
                if not ch:raise AssertionError('bridge exited')
                if ch==b'\n':return json.loads(data)
                data+=ch
        raise AssertionError('no MCP response')

    def rpc(self,p,name,args):
        p.stdin.write((json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args}})+'\n').encode());p.stdin.flush()
        response=self.receive(p)
        self.assertEqual(response.get('id'),1,response)
        return response['result']

    def test_read_post_ack_round_trip_preserves_unseen(self):
        p=self.client('paging','reader')
        self.assertFalse(self.rpc(p,'room_join',{})['isError'])
        self.http('/api/post',{'channel':'paging','from':'synthetic-human','text':'DO NOT SKIP THIS'})
        self.rpc(p,'room_post',{'text':'I have moved on to other work'})
        text=self.rpc(p,'room_read',{})['content'][0]['text']
        self.assertIn('DO NOT SKIP THIS',text)
        self.assertEqual(self.http('/api/cursor?agent=reader&channel=paging')['cursor'],0)
        self.assertTrue(self.rpc(p,'room_ack',{'read_through':999})['isError'])
        self.assertFalse(self.rpc(p,'room_ack',{'read_through':2})['isError'])
        self.assertIn('(nothing new)',self.rpc(p,'room_read',{})['content'][0]['text'])

    def test_idle_channel_notification_then_explicit_receipt(self):
        p=self.client('notification','channel-reader',True)
        self.rpc(p,'room_join',{})
        result=self.http('/api/post',{'channel':'notification','from':'synthetic-human','to_session':'channel-reader','text':'SYNTHETIC CHANNEL EVENT'})
        notice=self.receive(p)
        self.assertEqual(notice['method'],'notifications/claude/channel')
        self.assertIn('SYNTHETIC CHANNEL EVENT',notice['params']['content'])
        did=result['delivery'][0]['id']
        self.assertEqual(notice['params']['meta']['delivery_id'],did)
        self.assertFalse(self.rpc(p,'room_ack',{'delivery_ids':[did]})['isError'])
        self.assertEqual(self.http('/api/delivery?channel=notification')['deliveries'][0]['state'],'acknowledged')
        self.assertFalse(select.select([p.stdout],[],[],1.2)[0], 'duplicate event')

    def test_second_daemon_cannot_recover_or_dispatch_same_store(self):
        env=dict(os.environ, AGENT_ROOM_HOME=self.tmp.name, AGENT_ROOM_PORT='0')
        other=subprocess.run([sys.executable,str(ROOT/'roomd.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
        self.assertNotEqual(other.returncode,0)
        self.assertIn(b'another daemon owns',other.stderr)

    def test_auth_and_bad_input(self):
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.http('/api/sessions?channel=test',token='wrong')
        self.assertEqual(err.exception.code,401)
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.http('/api/register',{'channel':'../secret','session':'synthetic','agent':'synthetic'})
        self.assertEqual(err.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError):
            self.http('/api/post',[])

if __name__=='__main__':unittest.main()
