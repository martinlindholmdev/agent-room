import os
import io
import json
import unittest
from unittest.mock import patch
from desktop.mcp import incoming, resolve_binding, room_connect, run


class HostIdentityTests(unittest.TestCase):
    bindings=[{'id':'a','native':'task-a','app':'codex-queue'},
              {'id':'b','native':'task-b','app':'codex-queue'},
              {'id':'c','native':'claude-c','app':'claude-channel'},
              {'id':'e','native':'agent-x','app':'mcp'},
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

    def test_generic_mode_self_identifies_from_env_or_flag(self):
        with patch.dict(os.environ,{'AGENT_ROOM_NATIVE':'agent-x'},clear=True):
            self.assertEqual(resolve_binding(self.bindings,generic=True)['id'],'e')
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(resolve_binding(self.bindings,generic=True,native_arg='agent-x')['id'],'e')
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,generic=True)

    def test_generic_mode_is_mutually_exclusive_with_claude_flags(self):
        with patch.dict(os.environ,{'AGENT_ROOM_NATIVE':'agent-x'},clear=True):
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,claude_app=True,generic=True)
            with self.assertRaises(SystemExit):resolve_binding(self.bindings,claude_channel=True,generic=True)

    def test_generic_room_connect_requires_native_identity_and_reports_connected(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):room_connect('unused',generic=True)
        with patch.dict(os.environ,{'AGENT_ROOM_NATIVE':'agent-x','AGENT_ROOM_MODEL':'glm-5-3'},clear=True), \
             patch('desktop.mcp.local_call',return_value={'bindings':self.bindings}) as local:
            result=room_connect('unused',generic=True)
            self.assertEqual({'state':'connected','binding':'e','note':'This session is already connected to the room.'},result)
            local.assert_called_once_with('unused','snapshot',{})

    def test_generic_mcp_run_reads_on_demand_without_monitor_tools(self):
        binding=dict(next(b for b in self.bindings if b['id']=='e'), generation=1)
        calls=[]
        def local(_root,action,data):
            calls.append((action,data))
            if action=='snapshot':return {'bindings':[binding]}
            if action=='tool':
                self.assertEqual(binding['id'],data['binding'])
                self.assertEqual(binding['native'],data['native'])
                self.assertIsNone(data['lease'])
                return {'messages':[], 'read_through':0}
            self.fail('generic MCP issued unexpected local action: '+action)
        requests=[json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/list'})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'room_read','arguments':{}}})+'\n']
        with patch.dict(os.environ,{'AGENT_ROOM_NATIVE':'agent-x'},clear=True), \
             patch('desktop.mcp.local_call',side_effect=local), \
             patch('desktop.mcp.sys.stdin',requests), \
             patch('desktop.mcp.sys.stdout',new_callable=io.StringIO) as output:
            run('unused',None,generic=True)
        replies=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([1,2,3],[reply['id'] for reply in replies])
        self.assertNotIn('experimental',replies[0]['result']['capabilities'])
        tool_names=[tool['name'] for tool in replies[1]['result']['tools']]
        self.assertNotIn('room_monitor_setup',tool_names)
        self.assertNotIn('room_monitor_status',tool_names)
        self.assertIn('room_read',tool_names)
        self.assertEqual({'messages':[], 'read_through':0},json.loads(replies[2]['result']['content'][0]['text']))

    def test_generic_mcp_exposes_room_wait_and_resident_protocol_instructions(self):
        binding = dict(next(b for b in self.bindings if b['id'] == 'e'), generation=1)
        def local(_root, action, data):
            if action == 'snapshot':
                return {'bindings': [binding]}
            self.fail('tools/list issued unexpected local action: '+action)
        requests = [json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})+'\n',
                    json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})+'\n']
        with patch.dict(os.environ, {'AGENT_ROOM_NATIVE': 'agent-x'}, clear=True), \
             patch('desktop.mcp.local_call', side_effect=local), \
             patch('desktop.mcp.sys.stdin', requests), \
             patch('desktop.mcp.sys.stdout', new_callable=io.StringIO) as output:
            run('unused', None, generic=True)
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        instructions = replies[0]['result']['instructions']
        self.assertIn('room_wait', instructions)
        self.assertIn('Resident protocol', instructions)
        self.assertNotIn('there is no push and no idle-wake', instructions)
        tool_names = [tool['name'] for tool in replies[1]['result']['tools']]
        self.assertIn('room_wait', tool_names)

    def test_room_wait_polls_wait_next_hops_until_ready_then_returns_room_read_page(self):
        binding = dict(next(b for b in self.bindings if b['id'] == 'e'), generation=1)
        clock = {'t': 0.0}
        wait_calls = {'n': 0}
        calls = []
        def local(_root, action, data):
            calls.append((action, data))
            if action == 'snapshot':
                return {'bindings': [binding]}
            if action == 'wait-next':
                self.assertEqual(binding['id'], data['binding'])
                self.assertEqual(binding['native'], data['native'])
                self.assertLessEqual(data['timeout'], 20)
                wait_calls['n'] += 1
                clock['t'] += data['timeout']
                return {'ready': wait_calls['n'] >= 2, 'seq': 5}
            if action == 'tool':
                self.assertEqual('room_read', data['name'])
                self.assertIsNone(data['lease'])
                return {'messages': [{'id': 'm1'}], 'read_through': 5, 'deliveries': []}
            self.fail('room_wait issued unexpected local action: '+action)
        requests = [json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})+'\n',
                    json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                'params': {'name': 'room_wait', 'arguments': {'timeout_seconds': 600}}})+'\n']
        with patch.dict(os.environ, {'AGENT_ROOM_NATIVE': 'agent-x'}, clear=True), \
             patch('desktop.mcp.local_call', side_effect=local), \
             patch('desktop.mcp.time.monotonic', side_effect=lambda: clock['t']), \
             patch('desktop.mcp.sys.stdin', requests), \
             patch('desktop.mcp.sys.stdout', new_callable=io.StringIO) as output:
            run('unused', None, generic=True)
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        value = json.loads(replies[1]['result']['content'][0]['text'])
        self.assertEqual([{'id': 'm1'}], value['messages'])
        self.assertEqual(5, value['read_through'])
        self.assertIn('room_wait', value['instructions'])
        self.assertEqual(2, wait_calls['n'])

    def test_room_wait_times_out_cleanly_with_no_new_content(self):
        binding = dict(next(b for b in self.bindings if b['id'] == 'e'), generation=1)
        clock = {'t': 0.0}
        def local(_root, action, data):
            if action == 'snapshot':
                return {'bindings': [binding]}
            if action == 'wait-next':
                clock['t'] += data['timeout']
                return {'ready': False, 'seq': 0}
            self.fail('room_wait issued unexpected local action on timeout path: '+action)
        requests = [json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})+'\n',
                    json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                'params': {'name': 'room_wait', 'arguments': {'timeout_seconds': 5}}})+'\n']
        with patch.dict(os.environ, {'AGENT_ROOM_NATIVE': 'agent-x'}, clear=True), \
             patch('desktop.mcp.local_call', side_effect=local), \
             patch('desktop.mcp.time.monotonic', side_effect=lambda: clock['t']), \
             patch('desktop.mcp.sys.stdin', requests), \
             patch('desktop.mcp.sys.stdout', new_callable=io.StringIO) as output:
            run('unused', None, generic=True)
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        value = json.loads(replies[1]['result']['content'][0]['text'])
        self.assertEqual([], value['messages'])
        self.assertIn('room_wait again', value['note'])

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
        self.assertIn('Setup alone cannot prove idle wake',replies[0]['result']['instructions'])
        self.assertIn('room_ack',[tool['name'] for tool in replies[1]['result']['tools']])
        self.assertIn('room_monitor_setup',[tool['name'] for tool in replies[1]['result']['tools']])
        self.assertEqual({'messages':[], 'read_through':0},json.loads(replies[2]['result']['content'][0]['text']))

    def test_claude_monitor_setup_status_and_renewal_keep_exact_mcp_identity(self):
        binding=dict(self.bindings[-1], generation=7)
        calls=[]
        feeds=[]
        def local(_root,action,data):
            calls.append((action,data))
            if action=='snapshot':return {'bindings':[binding]}
            if action=='watch-next':
                self.assertEqual({'binding':'d','native':'claude-c','generation':7},data)
                return {'oldest':0,'latest':0}
            self.fail('Monitor setup used other local action: '+action)
        class FakeFeed:
            def __init__(self,root,identity,native,generation,fetch):
                self.assertion=(root,identity,native,generation)
                self.closed=False
                feeds.append(self)
            def start(self,duration):
                if duration!=60:raise AssertionError('wrong native Monitor deadline')
                return {'command':'synthetic helper','timeout_ms':60000}
            def status(self):return {'connected':True,'seconds_remaining':60}
            def close(self):self.closed=True
        requests=[json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'room_monitor_setup','arguments':{'duration_seconds':60}}})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'room_monitor_status','arguments':{}}})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'room_monitor_setup','arguments':{'duration_seconds':60}}})+'\n']
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True), \
             patch('desktop.mcp.local_call',side_effect=local), \
             patch('desktop.monitor.MonitorFeed',FakeFeed), \
             patch('desktop.mcp.sys.stdin',requests), \
             patch('desktop.mcp.sys.stdout',new_callable=io.StringIO) as output:
            run('synthetic-root',None,claude_app=True)
        replies=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([1,2,3,4],[reply['id'] for reply in replies])
        self.assertEqual(['snapshot','watch-next','watch-next','watch-next'],[action for action,_ in calls])
        self.assertEqual(2,len(feeds))
        self.assertTrue(all(feed.assertion==('synthetic-root','d','claude-c',7) and feed.closed for feed in feeds))
        self.assertTrue(json.loads(replies[2]['result']['content'][0]['text'])['connected'])
        self.assertEqual(60000,json.loads(replies[3]['result']['content'][0]['text'])['timeout_ms'])

    def test_room_status_tool_is_listed_and_dispatches_like_other_room_tools(self):
        binding = dict(self.bindings[-1], generation=3)
        calls = []
        def local(_root, action, data):
            calls.append((action, data))
            if action == 'snapshot':
                return {'bindings': [binding]}
            if action == 'tool':
                self.assertEqual(binding['id'], data['binding'])
                self.assertEqual('room_status', data['name'])
                self.assertEqual({'state': 'blocked'}, data['args'])
                return {'id': binding['id'], 'state': 'blocked'}
            self.fail('room_status issued unexpected local action: '+action)
        requests=[json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/list'})+'\n',
                  json.dumps({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'room_status','arguments':{'state':'blocked'}}})+'\n']
        with patch.dict(os.environ,{'CLAUDE_CODE_SESSION_ID':'claude-c'},clear=True), \
             patch('desktop.mcp.local_call',side_effect=local), \
             patch('desktop.mcp.sys.stdin',requests), \
             patch('desktop.mcp.sys.stdout',new_callable=io.StringIO) as output:
            run('unused',None,claude_app=True)
        replies=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([1,2,3],[reply['id'] for reply in replies])
        tools = {tool['name']: tool for tool in replies[1]['result']['tools']}
        self.assertIn('room_status', tools)
        self.assertEqual(['working', 'idle', 'blocked', 'done'],
                          tools['room_status']['inputSchema']['properties']['state']['enum'])
        self.assertEqual({'id': binding['id'], 'state': 'blocked'},
                          json.loads(replies[2]['result']['content'][0]['text']))

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
