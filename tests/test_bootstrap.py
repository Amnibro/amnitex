"""test_bootstrap: detect_all() returns six clients; wire_client respects consent + backup; seed KB ingests."""
import json,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from atex.bootstrap.detect import detect_all,ClientStatus
from atex.bootstrap.configs import wire_client,_backup
from atex.kb import KnowledgeBase
_REPO=Path(__file__).resolve().parents[1]
class TestDetect(unittest.TestCase):
    def test_detect_all_returns_known_clients(self):
        statuses=detect_all()
        names=sorted(s.name for s in statuses)
        self.assertEqual(names,['claude_code','claude_desktop','cline','continue','cursor','zed'])
    def test_each_client_has_label_and_writability(self):
        for s in detect_all():
            self.assertIsInstance(s.label,str);self.assertGreater(len(s.label),0)
            self.assertIsInstance(s.auto_writable,bool)
class TestWireClient(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='atex_boot_'))
        self.cfg=self.tmp/'fake_client_config.json'
        self.atex_dir=self.tmp/'.atex'
        self.atex_dir.mkdir()
        self.client=ClientStatus(name='claude_desktop',label='Claude Desktop',config_path=self.cfg,auto_writable=True)
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def test_wire_creates_config_when_missing(self):
        ok,msg=wire_client(self.client,'C:/python/python.exe',self.atex_dir,consent=False)
        self.assertTrue(ok,msg);self.assertTrue(self.cfg.exists())
        data=json.loads(self.cfg.read_text(encoding='utf-8'))
        self.assertIn('mcpServers',data);self.assertIn('atex',data['mcpServers'])
        self.assertEqual(data['mcpServers']['atex']['command'],'C:/python/python.exe')
    def test_wire_backs_up_existing_config(self):
        prior={'mcpServers':{'somethingelse':{'command':'foo','args':[]}}}
        self.cfg.write_text(json.dumps(prior),encoding='utf-8')
        ok,msg=wire_client(self.client,'/usr/bin/python','/tmp/atex',consent=False)
        self.assertTrue(ok,msg)
        backups=list(self.tmp.glob('fake_client_config.json.atex-backup-*'))
        self.assertEqual(len(backups),1,'expected one backup file')
        self.assertEqual(json.loads(backups[0].read_text(encoding='utf-8')),prior)
        merged=json.loads(self.cfg.read_text(encoding='utf-8'))
        self.assertIn('somethingelse',merged['mcpServers'])
        self.assertIn('atex',merged['mcpServers'])
    def test_dry_run_does_not_write(self):
        ok,msg=wire_client(self.client,'/usr/bin/python','/tmp/atex',consent=False,dry_run=True)
        self.assertTrue(ok);self.assertIn('dry-run',msg.lower());self.assertFalse(self.cfg.exists())
    def test_zed_writes_context_servers_block(self):
        zed=ClientStatus(name='zed',label='Zed',config_path=self.cfg,auto_writable=True)
        ok,msg=wire_client(zed,'/usr/bin/python','/tmp/atex',consent=False)
        self.assertTrue(ok,msg)
        data=json.loads(self.cfg.read_text(encoding='utf-8'))
        self.assertIn('context_servers',data);self.assertIn('atex',data['context_servers'])
        self.assertIn('command',data['context_servers']['atex'])
class TestSeedKb(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='atex_seed_'))
    def tearDown(self):shutil.rmtree(self.tmp,ignore_errors=True)
    def test_demo_seeds_self_recall_kb(self):
        atex_dir=self.tmp/'.atex'
        env={**__import__('os').environ,'PYTHONPATH':str(_REPO),'PYTHONIOENCODING':'utf-8'}
        r=subprocess.run([sys.executable,'-m','atex.cli','demo','--atex-dir',str(atex_dir),'--no-consent','--dry-run','--client','claude_desktop'],capture_output=True,text=True,env=env,cwd=str(_REPO),timeout=20)
        self.assertEqual(r.returncode,0,f'demo failed:\nSTDOUT={r.stdout}\nSTDERR={r.stderr}')
        kb=KnowledgeBase(atex_dir)
        keys=kb.keys()
        self.assertIn('seed::atex_overview',keys);self.assertIn('seed::atex_faq',keys)
        self.assertIn('seed::install_guide',keys);self.assertIn('seed::clients',keys)
        overview=kb.lookup('seed::atex_overview')
        collapsed=' '.join(overview.split())
        self.assertIn('Model Context Protocol',collapsed);self.assertIn('atex_search',overview)
class TestSeedHasNoClosedParadigm(unittest.TestCase):
    def test_no_closed_terms_in_seed_content(self):
        forbidden=['Reffelt','GF(17)','GF17','AsimovLayer','PrismTex','ExperienceAtlas','Adam-1','Adam1','TMU lookup','texture-native','PTEX-encoded','Adam-Texture']
        offenders=[]
        seed=_REPO/'atex'/'seed'
        for f in list(seed.glob('*.txt'))+list(seed.glob('*.md')):
            text=f.read_text(encoding='utf-8',errors='replace')
            for term in forbidden:
                if term.lower() in text.lower():offenders.append(f'{f.name}: contains "{term}"')
        self.assertFalse(offenders,'seed content contains closed-paradigm terminology:\n'+'\n'.join(offenders))
if __name__=='__main__':unittest.main(verbosity=2)
