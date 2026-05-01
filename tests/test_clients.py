"""test_clients: AtexRagClient + validation loop with synthetic chat (no ollama required)."""
import shutil,tempfile,unittest
from pathlib import Path
from atex.clients.rag import AtexRagClient
from atex.clients.validate import run_validation_loop,make_synthetic_chat,ValidationResult
from atex.clients.ollama import check_ollama_available,list_ollama_models
class TestAtexRagClient(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='atex_rag_'))
        self.atex=self.tmp/'.atex'
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def test_remember_then_recall(self):
        client=AtexRagClient(self.atex,chat_fn=make_synthetic_chat())
        client.remember('foo','bar')
        self.assertEqual(client.recall('foo'),'bar')
        self.assertEqual(client.recall('manual::foo'),'bar')
    def test_ask_includes_retrieval(self):
        client=AtexRagClient(self.atex,chat_fn=make_synthetic_chat())
        client.remember('cookie','azure-marmot-7421')
        rec=client.ask('What is the cookie?')
        self.assertGreaterEqual(rec['n_hits'],1)
        self.assertIn('manual::cookie',rec['top_keys'])
        self.assertGreater(rec['retrieval_ms'],0)
class TestValidationLoop(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='atex_val_'))
        self.atex=self.tmp/'.atex'
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def test_validation_loop_passes_with_synthetic_chat(self):
        client=AtexRagClient(self.atex,chat_fn=make_synthetic_chat())
        res=run_validation_loop(client,model_label='synthetic')
        self.assertEqual(res.n_steps,4)
        self.assertEqual(res.n_fail,0,res.summary())
        self.assertTrue(res.passed)
    def test_validation_loop_fails_with_silent_chat(self):
        def silent(prompt):return 'I do not know.'
        client=AtexRagClient(self.atex,chat_fn=silent)
        res=run_validation_loop(client,model_label='silent')
        self.assertGreaterEqual(res.n_fail,1)
        self.assertFalse(res.passed)
class TestOllamaProbe(unittest.TestCase):
    def test_check_ollama_does_not_crash(self):
        ok=check_ollama_available()
        self.assertIsInstance(ok,bool)
    def test_list_models_returns_list_even_when_unavailable(self):
        models=list_ollama_models(base_url='http://localhost:1')
        self.assertIsInstance(models,list)
if __name__=='__main__':unittest.main(verbosity=2)
