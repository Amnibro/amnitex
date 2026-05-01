"""KBRetriever: keyword-overlap retrieval over a KnowledgeBase. No model dep, pure mmap reads.
Scoring (v1): TF-style — count of query keyword occurrences in (key + text). Future: optional embedding sidecar.
Usage:
    retr = KBRetriever('.atex')
    results = retr.retrieve('how does authentication work', k=3, max_chars_per=600)
    context_block = retr.format_as_context(results)
"""
import re
from typing import List,Tuple
from atex.kb import KnowledgeBase
_TOK_RE=re.compile(r"[a-zA-Z][a-zA-Z0-9_\-\.]*")
_STOP={'the','a','an','and','or','of','to','in','for','is','are','what','how','do','i','my','this','that','with','on','at','by','as','it','be','can','use','using','from','some','any','have','has','will','would','should','could','make','get','set','put','show','give','tell','please','help'}
def _tokenize(text:str)->List[str]:
    return [t.lower() for t in _TOK_RE.findall(text or '') if t.lower() not in _STOP and len(t)>=2]
class KBRetriever:
    def __init__(self,kb_root:str):
        self.kb=KnowledgeBase(kb_root)
    def retrieve(self,query:str,k:int=3,max_chars_per:int=600,min_score:int=1)->List[Tuple[str,str,int]]:
        q_tokens=_tokenize(query)
        if not q_tokens:return []
        scored=[]
        keys=self.kb.keys()
        for key in keys:
            key_l=key.lower()
            txt=self.kb.lookup(key) or ''
            txt_l=txt.lower()
            key_score=sum(1 for t in q_tokens if t in key_l)
            txt_score=sum(1 for t in q_tokens if t in txt_l)
            score=key_score+txt_score
            if score<min_score:continue
            scored.append((score,key,txt))
        scored.sort(key=lambda x:(-x[0],x[1]))
        out=[]
        for score,key,txt in scored[:k]:
            if len(txt)>max_chars_per:txt=txt[:max_chars_per]+'...'
            out.append((key,txt,score))
        return out
    def format_as_context(self,results:List[Tuple[str,str,int]])->str:
        if not results:return ''
        lines=['Reference docs (retrieved from knowledge base):']
        for key,txt,score in results:
            lines.append(f'--- {key} (score={score})')
            lines.append(txt)
        return '\n'.join(lines)
    def stats(self):return self.kb.stats()
    def close(self):self.kb.close()
