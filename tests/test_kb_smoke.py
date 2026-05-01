"""test_kb_smoke: KnowledgeBase round-trip and edge cases."""
import json,shutil,tempfile,unittest
from pathlib import Path
from atex.kb import KnowledgeBase,KnowledgeBaseError
class TestKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir=Path(tempfile.mkdtemp(prefix='atex_kb_'))
        self.root=self.tmpdir/'kb'
    def tearDown(self):
        shutil.rmtree(self.tmpdir,ignore_errors=True)
    def test_init_creates_layout(self):
        kb=KnowledgeBase(self.root)
        self.assertTrue((self.root/'index.json').exists())
        self.assertTrue((self.root/'pages').is_dir())
        idx=json.loads((self.root/'index.json').read_text(encoding='utf-8'))
        self.assertEqual(idx['magic'],'ATEXKB01')
        self.assertEqual(idx['n_entries'],0)
    def test_add_lookup_round_trip(self):
        kb=KnowledgeBase(self.root)
        kb.add('hello','rao oui!')
        self.assertEqual(kb.lookup('hello'),'rao oui!')
        self.assertEqual(len(kb),1)
        self.assertIn('hello',kb)
    def test_unicode_round_trip(self):
        kb=KnowledgeBase(self.root)
        text='emoji ✨ and al-bhed Fryd\'s ib! and 中文 mixed'
        kb.add('mixed::content',text)
        self.assertEqual(kb.lookup('mixed::content'),text)
    def test_lookup_prefix(self):
        kb=KnowledgeBase(self.root)
        kb.add('project::a.py','aa')
        kb.add('project::b.py','bb')
        kb.add('manual::topic','mm')
        results=dict(kb.lookup_prefix('project::'))
        self.assertEqual(len(results),2)
        self.assertEqual(results['project::a.py'],'aa')
    def test_overwrite_protection(self):
        kb=KnowledgeBase(self.root)
        kb.add('k','v1')
        kb.add('k','v2',allow_overwrite=True)
        self.assertEqual(kb.lookup('k'),'v2')
        with self.assertRaises(KnowledgeBaseError):
            kb.add('k','v3',allow_overwrite=False)
    def test_empty_key_rejected(self):
        kb=KnowledgeBase(self.root)
        with self.assertRaises(KnowledgeBaseError):kb.add('','v')
    def test_oversize_rejected(self):
        kb=KnowledgeBase(self.root,page_w=8,page_h=8)
        big='x'*(8*8*4+1)
        with self.assertRaises(KnowledgeBaseError):kb.add('big',big)
    def test_persistence_across_instances(self):
        kb1=KnowledgeBase(self.root)
        kb1.add('persistent','data')
        kb1.flush();kb1.close()
        kb2=KnowledgeBase(self.root)
        self.assertEqual(kb2.lookup('persistent'),'data')
    def test_stats_reports_geometry(self):
        kb=KnowledgeBase(self.root,page_w=1024,page_h=64)
        kb.add('k','v')
        s=kb.stats()
        self.assertEqual(s['page_w'],1024);self.assertEqual(s['page_h'],64)
        self.assertEqual(s['page_bytes'],1024*64*4)
        self.assertEqual(s['n_entries'],1)
if __name__=='__main__':unittest.main(verbosity=2)
