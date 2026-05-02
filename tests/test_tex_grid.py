"""test_tex_grid: spatial token index correctness + scale invariance."""
import shutil,tempfile,unittest
from pathlib import Path
from atex.kb import KnowledgeBase
from atex.tex_grid import TexGrid,build_from_kb
from atex.tex_retriever import TexRetriever
class TestTexGrid(unittest.TestCase):
    def test_query_returns_inserted_entry(self):
        g=TexGrid(grid_w=64,grid_h=64)
        g.insert(0,'project::auth.py','HMAC-SHA256 cookie issuance')
        g.insert(1,'project::db.py','connection pool size eight')
        results=g.query('HMAC cookie',k=3)
        self.assertGreater(len(results),0)
        self.assertEqual(results[0][0],0)
    def test_query_scales_sublinearly_with_corpus_size(self):
        small=TexGrid(grid_w=256,grid_h=256)
        for i in range(10):small.insert(i,f'k_{i}',f'unique_word_{i*7+3} content body filler text data here')
        large=TexGrid(grid_w=256,grid_h=256)
        for i in range(2000):large.insert(i,f'k_{i}',f'unique_word_{i*7+3} content body filler text data here')
        import time
        t0=time.perf_counter()
        for i in range(100):small.query(f'unique_word_{i*7+3}',k=5)
        small_ms=(time.perf_counter()-t0)*1000/100
        t0=time.perf_counter()
        for i in range(100):large.query(f'unique_word_{i*7+3}',k=5)
        large_ms=(time.perf_counter()-t0)*1000/100
        ratio=large_ms/max(small_ms,0.001)
        n_ratio=2000/10
        self.assertLess(ratio,n_ratio/10,f'large.query={large_ms}ms vs small.query={small_ms}ms (ratio {ratio:.1f}× for {n_ratio:.0f}× more entries — should be much sub-linear)')
    def test_overflow_handled(self):
        g=TexGrid(grid_w=4,grid_h=4,inline_slots=2)
        for i in range(50):g.insert(i,f'k_{i}','common common common')
        s=g.stats()
        self.assertGreater(s['overflow_slots'],0,'expected overflow with 50 entries × 1 token in 16 cells × 2 slots')
        results=g.query('common',k=10)
        self.assertGreaterEqual(len(results),10)
class TestTexRetriever(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='atex_tex_'))
        self.root=self.tmp/'kb'
        kb=KnowledgeBase(self.root)
        kb.add('project::auth.py','HMAC-SHA256 cookie issuance and verify')
        kb.add('project::db.py','connection pool size eight')
        kb.add('project::routes.py','HTTP routes for the web app')
        kb.flush();kb.close()
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def test_retriever_finds_auth(self):
        r=TexRetriever(str(self.root))
        r.build()
        results=r.retrieve('HMAC cookie verify',k=2)
        self.assertGreater(len(results),0)
        self.assertEqual(results[0][0],'project::auth.py')
    def test_retriever_lazy_build(self):
        r=TexRetriever(str(self.root))
        results=r.retrieve('connection pool',k=1)
        self.assertEqual(results[0][0],'project::db.py')
    def test_add_after_build_updates_index(self):
        r=TexRetriever(str(self.root))
        r.build()
        r.add('project::cache.py','LRU cache implementation')
        results=r.retrieve('LRU cache',k=1)
        self.assertEqual(results[0][0],'project::cache.py')
if __name__=='__main__':unittest.main(verbosity=2)
