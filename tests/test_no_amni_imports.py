"""test_no_amni_imports: Sentinel rule 2 enforcement — public source must not reference amni.* internals."""
import unittest
from pathlib import Path
_REPO=Path(__file__).resolve().parents[1]
class TestNoAmniImports(unittest.TestCase):
    def test_no_amni_substring_in_published_source(self):
        offenders=[]
        for py in (_REPO/'atex').rglob('*.py'):
            text=py.read_text(encoding='utf-8',errors='replace')
            for i,line in enumerate(text.splitlines(),1):
                if 'amni.' in line or line.startswith('from amni') or line.startswith('import amni'):
                    offenders.append(f'{py.relative_to(_REPO)}:{i}: {line.strip()}')
        self.assertFalse(offenders,'public source contains amni.* references:\n'+'\n'.join(offenders))
    def test_no_closed_paradigm_terms_in_docstrings(self):
        forbidden=['GF(17)','GF17','AsimovLayer','PrismTex','ExperienceAtlas','Adam-1','Adam1','TMU lookup','texture-native','PTEX-encoded','Adam-Texture','adam-texture','Reffelt 4-tier','Reffelt decomposition','Reffelt nonces','Reffelt RGBA','Reffelt PTEX']
        offenders=[]
        for py in (_REPO/'atex').rglob('*.py'):
            text=py.read_text(encoding='utf-8',errors='replace')
            for term in forbidden:
                if term.lower() in text.lower():
                    offenders.append(f'{py.relative_to(_REPO)}: contains "{term}"')
        self.assertFalse(offenders,'public source contains closed-paradigm terminology:\n'+'\n'.join(offenders))
if __name__=='__main__':unittest.main(verbosity=2)
