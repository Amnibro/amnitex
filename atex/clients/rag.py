"""atex.clients.rag: minimal RAG client that wraps a KB + retriever + a chat callable. Model-agnostic."""
import time
from pathlib import Path
from typing import Callable,Dict,List,Optional
from atex.kb import KnowledgeBase
from atex.retriever import KBRetriever
ChatFn=Callable[[str],str]
class AtexRagClient:
    def __init__(self,atex_dir,chat_fn:ChatFn,k:int=3,max_chars_per:int=600):
        self.atex_dir=Path(atex_dir)
        self.kb=KnowledgeBase(self.atex_dir)
        self.retr=KBRetriever.__new__(KBRetriever)
        self.retr.kb=self.kb
        self.chat=chat_fn
        self.k=k
        self.max_chars_per=max_chars_per
        self._calls:List[Dict]=[]
    def _build_prompt(self,question:str,context:str)->str:
        if not context:return f'Question: {question}\nAnswer concisely:'
        return f'{context}\n\nUsing only the references above (and prior knowledge if they are silent), answer concisely.\n\nQuestion: {question}\nAnswer:'
    def ask(self,question:str,k:Optional[int]=None)->Dict:
        t0=time.perf_counter()
        results=self.retr.retrieve(question,k=k or self.k,max_chars_per=self.max_chars_per)
        retr_ms=(time.perf_counter()-t0)*1000
        ctx=self.retr.format_as_context(results) if results else ''
        prompt=self._build_prompt(question,ctx)
        t1=time.perf_counter()
        answer=self.chat(prompt)
        chat_ms=(time.perf_counter()-t1)*1000
        rec={'question':question,'n_hits':len(results),'top_keys':[r[0] for r in results],'retrieval_ms':round(retr_ms,2),'chat_ms':round(chat_ms,1),'total_ms':round(retr_ms+chat_ms,1),'answer':answer}
        self._calls.append(rec)
        return rec
    def remember(self,key:str,text:str)->str:
        full_key=key if key.startswith('manual::') else f'manual::{key}'
        self.kb.add(full_key,text,meta={'kind':'manual','source':'atex_rag_client'},allow_overwrite=True)
        self.kb.flush()
        return full_key
    def recall(self,key:str)->Optional[str]:
        full_key=key if '::' in key else f'manual::{key}'
        return self.kb.lookup(full_key)
    def stats(self)->Dict:
        s=self.kb.stats()
        n_calls=len(self._calls)
        avg_total=sum(c['total_ms'] for c in self._calls)/n_calls if n_calls else 0
        avg_retr=sum(c['retrieval_ms'] for c in self._calls)/n_calls if n_calls else 0
        avg_chat=sum(c['chat_ms'] for c in self._calls)/n_calls if n_calls else 0
        s['ask_calls']=n_calls
        s['avg_total_ms']=round(avg_total,2)
        s['avg_retrieval_ms']=round(avg_retr,2)
        s['avg_chat_ms']=round(avg_chat,1)
        return s
