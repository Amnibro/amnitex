"""test_retriever_smoke: KBRetriever scoring and format."""
import shutil,tempfile,unittest
from pathlib import Path
from atex.kb import KnowledgeBase
from atex.retriever import KBRetriever,_tokenize
class TestRetriever(unittest.TestCase):
    def setUp(self):
        self.tmpdir=Path(tempfile.mkdtemp(prefix='atex_retr_'))
        self.root=self.tmpdir/'kb'
        kb=KnowledgeBase(self.root)
        kb.add('project::auth.py','HMAC-SHA256 cookie issuance and verify')
        kb.add('project::db.py','connection pool size eight')
        kb.add('project::routes.py','HTTP routes for the web app')
        kb.flush();kb.close()
    def tearDown(self):shutil.rmtree(self.tmpdir,ignore_errors=True)
    def test_retrieve_returns_top_k(self):
        r=KBRetriever(str(self.root))
        results=r.retrieve('how does authentication HMAC work',k=2)
        self.assertGreaterEqual(len(results),1)
        self.assertEqual(results[0][0],'project::auth.py')
    def test_retrieve_no_match(self):
        r=KBRetriever(str(self.root))
        self.assertEqual(r.retrieve('xyzzy nonexistent term'),[])
    def test_format_as_context(self):
        r=KBRetriever(str(self.root))
        results=r.retrieve('connection pool',k=1)
        ctx=r.format_as_context(results)
        self.assertIn('Reference docs',ctx)
        self.assertIn('project::db.py',ctx)
    def test_tokenize_drops_stopwords(self):
        toks=_tokenize('how do I use this for the auth flow')
        self.assertNotIn('how',toks);self.assertNotIn('the',toks)
        self.assertIn('auth',toks);self.assertIn('flow',toks)
if __name__=='__main__':unittest.main(verbosity=2)
