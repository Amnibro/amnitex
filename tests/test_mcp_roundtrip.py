"""test_mcp_roundtrip: spawn `atex serve` as subprocess, drive 7 JSON-RPC calls + shutdown, assert each."""
import json,os,shutil,subprocess,sys,time,unittest
from pathlib import Path
_REPO=Path(__file__).resolve().parents[1]
_SAMPLE=_REPO/'tests'/'fixtures'/'sample_project'
class JsonRpcClient:
    def __init__(self,proc):
        self.proc=proc;self._next_id=1
    def call(self,method:str,params=None,timeout:float=10.0):
        req={'jsonrpc':'2.0','id':self._next_id,'method':method}
        if params is not None:req['params']=params
        self._next_id+=1
        line=json.dumps(req)+'\n'
        self.proc.stdin.write(line);self.proc.stdin.flush()
        deadline=time.time()+timeout
        while time.time()<deadline:
            resp_line=self.proc.stdout.readline()
            if not resp_line:time.sleep(0.01);continue
            try:return json.loads(resp_line.strip())
            except json.JSONDecodeError:continue
        raise TimeoutError(f'no response to {method} within {timeout}s')
    def notify(self,method:str,params=None):
        req={'jsonrpc':'2.0','method':method}
        if params is not None:req['params']=params
        self.proc.stdin.write(json.dumps(req)+'\n');self.proc.stdin.flush()
class TestMcpRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmpdir=Path(_REPO/'.smoke_tmp')
        if self.tmpdir.exists():shutil.rmtree(self.tmpdir)
        self.tmpdir.mkdir(parents=True)
        self.atex_dir=self.tmpdir/'.atex'
        env=os.environ.copy();env['PYTHONPATH']=str(_REPO)+(os.pathsep+env.get('PYTHONPATH','') if env.get('PYTHONPATH') else '')
        env['PYTHONIOENCODING']='utf-8'
        init_proc=subprocess.run([sys.executable,'-m','atex.cli','init','--root',str(_SAMPLE),'--atex-dir',str(self.atex_dir),'--no-gitignore'],capture_output=True,text=True,env=env,cwd=str(_REPO))
        self.assertEqual(init_proc.returncode,0,f'init failed:\nSTDOUT={init_proc.stdout}\nSTDERR={init_proc.stderr}')
        self.assertTrue((self.atex_dir/'index.json').exists(),'index.json not created by init')
        self.serve=subprocess.Popen([sys.executable,'-m','atex.cli','serve','--atex-dir',str(self.atex_dir)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,cwd=str(_REPO),bufsize=1)
        time.sleep(0.5)
        self.client=JsonRpcClient(self.serve)
    def tearDown(self):
        if self.serve.poll() is None:
            try:self.serve.terminate();self.serve.wait(timeout=2)
            except Exception:self.serve.kill()
        if self.tmpdir.exists():shutil.rmtree(self.tmpdir,ignore_errors=True)
    def test_seven_calls_round_trip(self):
        r=self.client.call('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'smoke','version':'0.0'}})
        self.assertIn('result',r,f'initialize: {r}')
        self.assertEqual(r['result']['protocolVersion'],'2024-11-05')
        self.assertEqual(r['result']['serverInfo']['name'],'atex')
        self.client.notify('notifications/initialized')
        r=self.client.call('tools/list')
        self.assertIn('result',r,f'tools/list: {r}')
        names=[t['name'] for t in r['result']['tools']]
        for expected in ['atex_search','atex_recall','atex_remember','atex_list_keys','atex_stats']:
            self.assertIn(expected,names,f'missing tool: {expected}')
        r=self.client.call('tools/call',{'name':'atex_stats','arguments':{}})
        self.assertIn('result',r,f'atex_stats: {r}')
        self.assertFalse(r['result'].get('isError',False))
        stats_text=r['result']['content'][0]['text']
        self.assertIn('entries=',stats_text)
        r=self.client.call('tools/call',{'name':'atex_search','arguments':{'query':'how does authentication work HMAC','k':3}})
        self.assertIn('result',r,f'atex_search: {r}')
        self.assertFalse(r['result'].get('isError',False))
        search_text=r['result']['content'][0]['text']
        self.assertTrue('auth.py' in search_text or 'HMAC' in search_text or 'hmac' in search_text,f'expected auth-related hit, got: {search_text[:200]}')
        r=self.client.call('tools/call',{'name':'atex_remember','arguments':{'key':'smoke-test-fact','text':'this fact was written by the MCP smoke test on iteration 3'}})
        self.assertIn('result',r,f'atex_remember: {r}')
        self.assertFalse(r['result'].get('isError',False))
        r=self.client.call('tools/call',{'name':'atex_recall','arguments':{'key':'manual::smoke-test-fact'}})
        self.assertIn('result',r,f'atex_recall: {r}')
        self.assertFalse(r['result'].get('isError',False))
        recall_text=r['result']['content'][0]['text']
        self.assertIn('iteration 3',recall_text)
        r=self.client.call('tools/call',{'name':'atex_list_keys','arguments':{'prefix':'project::','max':50}})
        self.assertIn('result',r,f'atex_list_keys: {r}')
        self.assertFalse(r['result'].get('isError',False))
        keys_text=r['result']['content'][0]['text']
        self.assertIn('project::',keys_text)
        r=self.client.call('shutdown')
        self.assertIn('result',r,f'shutdown: {r}')
    def test_remember_input_validation(self):
        self.client.call('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'smoke','version':'0.0'}})
        self.client.notify('notifications/initialized')
        r=self.client.call('tools/call',{'name':'atex_remember','arguments':{'key':'../etc/passwd','text':'evil'}})
        self.assertIn('error',r,f'expected error on path-traversal key, got: {r}')
        r=self.client.call('tools/call',{'name':'atex_remember','arguments':{'key':'has space','text':'evil'}})
        self.assertIn('error',r,f'expected error on space-in-key, got: {r}')
        r=self.client.call('tools/call',{'name':'atex_remember','arguments':{'key':'good_key','text':'x'*(2*1024*1024)}})
        self.assertIn('error',r,f'expected error on >1MiB text, got: {r}')
        self.client.call('shutdown')
if __name__=='__main__':
    unittest.main(verbosity=2)
