import os
import io
import json
import unittest
from unittest.mock import patch
from desktop.mcp import incoming, resolve_binding, run


class HostIdentityTests(unittest.TestCase):
    bindings=[{'id':'a','native':'task-a','app':'codex-queue'},
              {'id':'b','native':'task-b','app':'codex-queue'},
              {'id':'c','native':'claude-c','app':'claude-channel'},
              {'id':'d','native':'claude-c','app':'pull'}]

    def test_global_configuration_selects_only_current_host_session(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'task-b'},clear=True):
            self.assertEqual(resolve_binding(self.bindings)['id'],'b')
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,'a')
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True):
            self.assertEqual(resolve_binding(self.bindings,claude_channel=True)['id'],'c')
            self.assertEqual(resolve_binding(self.bindings,claude_app=True)['id'],'d')
            with self.assertRaises(SystemExit):resolve_binding(self.bindings)
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,'c',claude_app=True)
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,claude_channel=True,claude_app=True)

    def test_missing_unregistered_and_ambiguous_identity_fail_closed(self):
        for env in ({},{'CODEX_THREAD_ID':'unregistered'}):
            with patch.dict(os.environ,env,clear=True):
                with self.assertRaises(SystemExit):resolve_binding(self.bindings)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'task-a'},clear=True):
            with self.assertRaises(SystemExit):resolve_binding(self.bindings+[self.bindings[0]])
        for env in ({}, {'CLAUDE_CODE_SESSION_ID':'other'}):
            with patch.dict(os.environ,env,clear=True):
                with self.assertRaises(SystemExit):resolve_binding(self.bindings,claude_app=True)
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True):
            with self.assertRaises(SystemExit):resolve_binding(self.bindings+[self.bindings[-1]],claude_app=True)

    def test_claude_app_mcp_has_ordinary_tools_without_channel_bridge(self):
        binding=dict(self.bindings[-1], generation=3)
        calls=[]
        def local(_root,action,data):
            calls.append((action,data))
            if action=='snapshot':return {'bindings':[binding]}
            if action=='tool':
                self.assertEqual(binding['id'],data['binding'])
                self.assertEqual(binding['native'],data['native'])
                self.assertEqual(3,data['generation'])
                self.assertIsNone(data['lease'])
                return {'messages':[], 'read_through':0}
            self.fail('ordinary app MCP opened channel bridge: '+action)
        requests=[json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})+'\n',
                  json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/list'})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'room_read','arguments':{}}})+'\n']
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True), \
             patch('desktop.mcp.local_call',side_effect=local), \
             patch('desktop.mcp.sys.stdin',requests), \
             patch('desktop.mcp.sys.stdout',new_callable=io.StringIO) as output:
            run('unused',None,claude_app=True)
        replies=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(['snapshot','tool'],[action for action,_ in calls])
        self.assertEqual([1,2,3],[reply['id'] for reply in replies])
        self.assertNotIn('experimental',replies[0]['result']['capabilities'])
        self.assertIn('cannot wake an idle app session',replies[0]['result']['instructions'])
        self.assertIn('room_ack',[tool['name'] for tool in replies[1]['result']['tools']])
        self.assertEqual({'messages':[], 'read_through':0},json.loads(replies[2]['result']['content'][0]['text']))

    def test_host_specific_incoming_instructions(self):
        delivery={'id':'delivery-1','session':'binding-1'}
        message={'id':'message-1','from_session':'sender-1','text':'Synthetic'}
        codex=incoming(delivery,message)
        claude=incoming(delivery,message,claude_channel=True)
        for content in (codex,claude):
            self.assertIn('room_ack tool',content)
            self.assertIn('room_post tool',content)
            self.assertIn('delivery-1',content)
            self.assertIn('message-1',content)
            self.assertNotIn('agent-room-desktop room_ack',content)
        self.assertIn('installed agent-room-helper',codex)
        self.assertIn('Codex-only fallback',codex)
        self.assertNotIn('--tool room_ack',claude)
        self.assertNotIn('agent-room-helper',claude)

    def test_stale_claude_mcp_never_opens_bridge_or_retries(self):
        initial={'id':'c','native':'claude-c','app':'claude-channel','generation':1,'room':'general'}
        renewed=dict(initial,generation=2)
        calls=[]
        def local(_root,action,_data):
            calls.append(action)
            if action=='snapshot':
                return {'bindings':[initial if calls.count('snapshot')==1 else renewed]}
            self.fail('stale MCP issued '+action)
        class InlineThread:
            def __init__(self,target,daemon):self.target=target
            def start(self):self.target()
        requests=[json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})+'\n',
                  json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n']
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True), \
             patch('desktop.mcp.local_call',side_effect=local), \
             patch('desktop.mcp.threading.Thread',InlineThread), \
             patch('desktop.mcp.sys.stdin',requests), \
             patch('desktop.mcp.sys.stdout',new_callable=io.StringIO) as output:
            run('unused',None,claude_channel=True)
        self.assertEqual(['snapshot','snapshot'],calls)
        self.assertEqual(1,len(output.getvalue().splitlines()))
        self.assertNotIn('notifications/claude/channel',output.getvalue())
