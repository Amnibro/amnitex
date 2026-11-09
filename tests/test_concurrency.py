"""Several processes and both engines sharing one knowledge base."""
import json,os,re,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest import mock
import atex
from atex import kb as kb_module
from atex import serve
from atex.kb import KnowledgeBase,KnowledgeBaseError
from atex.tex_grid import TexGrid
from atex.tex_retriever import TexRetriever
ROOT=Path(__file__).resolve().parent.parent
WRITER="import sys\nfrom atex.kb import KnowledgeBase\nkb=KnowledgeBase(sys.argv[1])\nkb.add(sys.argv[2],sys.argv[3])\n"
def _native()->str:
    found=os.environ.get('ATEX_NATIVE_BIN') or shutil.which('atex-helium')
    return found if found and os.access(found,os.X_OK) else ''
def _remember(key:str,text:str)->bytes:
    return (json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'atex_remember','arguments':{'key':key,'text':text}}})+'\n').encode()
class SharedKB(unittest.TestCase):
    def setUp(self):
        self.dir=Path(tempfile.mkdtemp())/'kb'
        self.env=dict(os.environ,PYTHONPATH=str(ROOT))
    def tearDown(self):shutil.rmtree(self.dir.parent,ignore_errors=True)
    def _py_writer(self,key:str,text:str):
        return subprocess.Popen([sys.executable,'-c',WRITER,str(self.dir),key,text],env=self.env)
    def test_parallel_python_writers_all_survive(self):
        KnowledgeBase(self.dir)
        procs=[self._py_writer(f'k{i}',f'text {i}') for i in range(8)]
        for p in procs:self.assertEqual(p.wait(timeout=60),0)
        kb=KnowledgeBase(self.dir)
        for i in range(8):self.assertEqual(kb.lookup(f'k{i}'),f'text {i}')
        self.assertFalse((self.dir/'write.lock').exists())
    def test_stale_instance_appends_after_other_writer(self):
        first=KnowledgeBase(self.dir)
        second=KnowledgeBase(self.dir)
        first.add('a','alpha')
        second.add('b','bravo')
        fresh=KnowledgeBase(self.dir)
        self.assertEqual(fresh.lookup('a'),'alpha')
        self.assertEqual(fresh.lookup('b'),'bravo')
    def test_reader_sees_other_writer_after_refresh(self):
        reader=KnowledgeBase(self.dir)
        KnowledgeBase(self.dir).add('a','alpha')
        self.assertIsNone(reader.lookup('a'))
        self.assertTrue(reader.refresh())
        self.assertEqual(reader.lookup('a'),'alpha')
    def test_crashed_holder_is_recovered(self):
        kb=KnowledgeBase(self.dir)
        lock=self.dir/'write.lock'
        lock.mkdir()
        (lock/'owner').write_text('atex')
        old=time.time()-120
        os.utime(lock/'owner',(old,old))
        kb.add('a','alpha')
        self.assertEqual(kb.lookup('a'),'alpha')
        self.assertFalse(lock.exists())
    def test_live_holder_blocks_and_write_fails_loudly(self):
        kb=KnowledgeBase(self.dir)
        lock=self.dir/'write.lock'
        lock.mkdir()
        (lock/'owner').write_text('atex')
        with mock.patch.object(kb_module,'_LOCK_WAIT',0.05):
            with self.assertRaises(KnowledgeBaseError):kb.add('a','alpha')
        self.assertTrue(lock.exists())
        self.assertIsNone(kb.lookup('a'))
    def test_python_and_native_share_one_kb(self):
        native=_native()
        if not native:self.skipTest('atex-helium is not available')
        KnowledgeBase(self.dir)
        procs=[self._py_writer(f'manual::py{i}',f'py text {i}') for i in range(7)]
        natives=[subprocess.Popen([native,'serve','--atex-dir',str(self.dir)],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for _ in range(7)]
        for i,p in enumerate(natives):
            p.stdin.write(_remember(f'nat{i}',f'native text {i}'))
            p.stdin.close()
        for p in procs+natives:self.assertEqual(p.wait(timeout=60),0)
        kb=KnowledgeBase(self.dir)
        for i in range(7):
            self.assertEqual(kb.lookup(f'manual::py{i}'),f'py text {i}')
            self.assertEqual(kb.lookup(f'manual::nat{i}'),f'native text {i}')
    def test_native_selftest_passes_and_reports_failure_by_exit_code(self):
        native=_native()
        if not native:self.skipTest('atex-helium is not available')
        self.assertEqual(subprocess.run([native,'--selftest'],capture_output=True,timeout=60).returncode,0)
        self.dir.mkdir()
        (self.dir/'index.json').write_text('not json')
        self.assertNotEqual(subprocess.run([native,'stats','--atex-dir',str(self.dir)],capture_output=True,timeout=60).returncode,0)
class SearchAfterOverwrite(unittest.TestCase):
    def setUp(self):self.dir=Path(tempfile.mkdtemp())/'kb'
    def tearDown(self):shutil.rmtree(self.dir.parent,ignore_errors=True)
    def test_tex_retriever_forgets_replaced_text(self):
        r=TexRetriever(str(self.dir))
        r.add('a','needle one')
        r.add('b','needle two')
        r.build()
        r.add('a','totally different')
        self.assertEqual([hit[0] for hit in r.retrieve('needle',k=3)],['b'])
    def test_grid_counts_an_entry_once_per_cell(self):
        g=TexGrid(1,1)
        g.insert(0,'k','alpha beta')
        self.assertEqual(g.query('alpha'),[(0,1)])
    def test_native_search_forgets_replaced_text(self):
        native=_native()
        if not native:self.skipTest('atex-helium is not available')
        calls=[{'name':'atex_remember','arguments':{'key':'foo','text':'first zebra fact'}},{'name':'atex_search','arguments':{'query':'zebra'}},{'name':'atex_remember','arguments':{'key':'foo','text':'replaced giraffe fact'}},{'name':'atex_search','arguments':{'query':'zebra'}}]
        body=''.join(json.dumps({'jsonrpc':'2.0','id':i,'method':'tools/call','params':c})+'\n' for i,c in enumerate(calls))
        out=subprocess.run([native,'serve','--atex-dir',str(self.dir)],input=body.encode(),capture_output=True,timeout=60).stdout.decode()
        self.assertNotIn('giraffe',json.loads(out.strip().splitlines()[-1])['result']['content'][0]['text'])
class PythonServer(unittest.TestCase):
    def setUp(self):
        self.dir=Path(tempfile.mkdtemp())/'kb'
        KnowledgeBase(self.dir)
    def tearDown(self):shutil.rmtree(self.dir.parent,ignore_errors=True)
    def _run(self,*calls):
        body=''.join(json.dumps({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':n,'arguments':a}})+'\n' for i,(n,a) in enumerate(calls))
        env=dict(os.environ,PYTHONPATH=str(ROOT))
        out=subprocess.run([sys.executable,'-m','atex.cli','serve','--atex-dir',str(self.dir)],input=body.encode(),capture_output=True,env=env,timeout=60).stdout.decode()
        return [json.loads(line) for line in out.splitlines() if line.startswith('{')]
    def test_remembered_fact_is_searchable_and_prefix_is_not_doubled(self):
        res=self._run(('atex_remember',{'key':'manual::foo','text':'zebra fact'}),('atex_search',{'query':'zebra'}))
        self.assertIn('remembered as manual::foo ',res[0]['result']['content'][0]['text'])
        self.assertIn('zebra fact',res[1]['result']['content'][0]['text'])
    def test_key_rules_and_schema_match_native(self):
        self.assertTrue(serve._KEY_RE.match("project::a(b),c'd—e"))
        tool=[t for t in serve._TOOLS if t['name']=='atex_list_keys'][0]
        self.assertNotIn('required',tool['inputSchema'])
class Versions(unittest.TestCase):
    def test_every_manifest_names_one_version(self):
        for name in ['gemini-extension.json','manifest.json','plugin.json','.claude-plugin/plugin.json','.grok-plugin/plugin.json','.codex-plugin/plugin.json','.cursor-plugin/plugin.json']:
            self.assertEqual(json.loads((ROOT/name).read_text(encoding='utf-8'))['version'],atex.__version__,name)
        self.assertIn(f'version = "{atex.__version__}"',(ROOT/'pyproject.toml').read_text(encoding='utf-8'))
        native=set(re.findall(r'atex (\d+\.\d+\.\d+)',(ROOT/'atex_serve.gold').read_text(encoding='utf-8')))
        self.assertEqual(native,{atex.__version__})
if __name__=='__main__':unittest.main()
