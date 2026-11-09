"""Directory and intrafile lookup, kept current with the files on disk."""
import json,os,shutil,subprocess,tempfile,time,unittest
from pathlib import Path
from tests.test_concurrency import _native
class Tiers(unittest.TestCase):
    def setUp(self):
        self.native=_native()
        if not self.native:self.skipTest('atex-helium is not available')
        self.root=Path(tempfile.mkdtemp())
        self.src=self.root/'src'
        (self.src/'pkg').mkdir(parents=True)
        (self.src/'pkg'/'auth.py').write_text('import os\ndef verify_token(t):\n    return TOKEN_LIMIT > 7\n',encoding='utf-8')
        (self.src/'pkg'/'db.py').write_text('POOL_SIZE = 8\ndef connect():\n    return POOL_SIZE\n',encoding='utf-8')
        (self.src/'README.md').write_text('# Project\n\nThe pool size is documented here for readers.\n',encoding='utf-8')
        self.kb=self.root/'kb'
        env=dict(os.environ,HOME=str(self.root/'home'))
        subprocess.run([self.native,'init',str(self.src),'--atex-dir',str(self.kb)],check=True,capture_output=True,env=env,timeout=60)
    def tearDown(self):
        if hasattr(self,'root'):shutil.rmtree(self.root,ignore_errors=True)
    def call(self,*calls):
        body=''.join(json.dumps({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':n,'arguments':a}})+'\n' for i,(n,a) in enumerate(calls))
        out=subprocess.run([self.native,'serve','--atex-dir',str(self.kb)],input=body.encode(),capture_output=True,timeout=60).stdout.decode()
        return [json.loads(line)['result']['content'][0]['text'] for line in out.splitlines()]
    def where(self,q,**kw):return self.call(('atex_where',dict(query=q,**kw)))[0]
    def test_where_names_files_lines_and_best_line_without_file_bodies(self):
        text=self.where('POOL_SIZE')
        self.assertIn('project::pkg/db.py 2:',text)
        self.assertIn('POOL_SIZE = 8',text)
        self.assertNotIn('verify_token',text)
    def test_where_filters_by_folder(self):
        self.assertIn('project::pkg/db.py',self.where('pool',path='pkg/'))
        self.assertNotIn('README',self.where('pool',path='pkg/'))
    def test_where_rolls_up_extra_files_by_folder(self):
        text=self.where('pool',k=1)
        self.assertIn('more files',text)
    def test_identifier_does_not_match_on_its_parts(self):
        self.assertNotIn('README',self.where('POOL_SIZE'))
    def test_missing_identifier_is_labeled_partial(self):
        self.assertIn('no exact match for POOL_LIMIT',self.where('POOL_LIMIT'))
    def test_recall_with_query_returns_only_matching_lines(self):
        text=self.call(('atex_recall',{'key':'project::pkg/auth.py','query':'TOKEN_LIMIT'}))[0]
        self.assertIn('TOKEN_LIMIT > 7',text)
        self.assertIn('L2-3',text)
    def test_recall_query_with_no_match_says_so(self):
        self.assertIn('has no matching lines',self.call(('atex_recall',{'key':'project::pkg/auth.py','query':'POOL_SIZE'}))[0])
    def test_edit_new_file_and_delete_are_seen_without_reindex(self):
        (self.src/'pkg'/'db.py').write_text('RENAMED_POOL = 8\n',encoding='utf-8')
        (self.src/'pkg'/'new.py').write_text('FRESH_SYMBOL = 1\n',encoding='utf-8')
        (self.src/'pkg'/'auth.py').unlink()
        self.assertIn('project::pkg/db.py',self.where('RENAMED_POOL'))
        self.assertIn('project::pkg/new.py',self.where('FRESH_SYMBOL'))
        self.assertIn('(not found)',self.call(('atex_recall',{'key':'project::pkg/auth.py'}))[0])
        self.assertNotIn('project::pkg/auth.py',self.call(('atex_list_keys',{'prefix':'project::'}))[0])
    def test_same_second_edit_of_equal_size_is_seen(self):
        path=self.src/'pkg'/'db.py'
        stamp=path.stat().st_mtime
        path.write_text('POOL_SIZE = 9\ndef connect():\n    return POOL_SIZE\n',encoding='utf-8')
        os.utime(path,(stamp,stamp))
        self.assertIn('POOL_SIZE = 9',self.call(('atex_recall',{'key':'project::pkg/db.py','query':'POOL_SIZE'}))[0])
    def test_concurrent_servers_index_a_change_once(self):
        size=len('CONCURRENT_EDIT = 1\n'*40)
        before=json.loads((self.kb/'index.json').read_text())['pages'][-1]['used_bytes']
        (self.src/'pkg'/'db.py').write_text('CONCURRENT_EDIT = 1\n'*40,encoding='utf-8')
        body=(json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'atex_where','arguments':{'query':'CONCURRENT_EDIT'}}})+'\n').encode()
        procs=[subprocess.Popen([self.native,'serve','--atex-dir',str(self.kb)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) for _ in range(7)]
        outs=[p.communicate(body,timeout=60)[0].decode() for p in procs]
        for out in outs:self.assertIn('project::pkg/db.py',out)
        after=json.loads((self.kb/'index.json').read_text())['pages'][-1]['used_bytes']
        self.assertEqual(after-before,size)
        self.assertFalse((self.kb/'write.lock').exists())
    def test_reinit_of_unchanged_tree_adds_nothing(self):
        before=json.loads((self.kb/'index.json').read_text())['pages'][-1]['used_bytes']
        time.sleep(3)
        env=dict(os.environ,HOME=str(self.root/'home'))
        subprocess.run([self.native,'init',str(self.src),'--atex-dir',str(self.kb)],check=True,capture_output=True,env=env,timeout=60)
        self.assertEqual(json.loads((self.kb/'index.json').read_text())['pages'][-1]['used_bytes'],before)
    def test_home_folder_is_not_registered(self):
        home=self.root/'homeroot'
        home.mkdir()
        kb=self.root/'kb2'
        subprocess.run([self.native,'init',str(home),'--atex-dir',str(kb)],check=True,capture_output=True,env=dict(os.environ,HOME=str(home)),timeout=60)
        self.assertEqual(json.loads((kb/'index.json').read_text()).get('roots'),[])
if __name__=='__main__':unittest.main()
