"""atex.tex_retriever: retriever backed by a TexGrid spatial index. O(num_query_tokens) regardless of KB size."""
from typing import List,Tuple
from atex.kb import KnowledgeBase
from atex.tex_grid import TexGrid,build_from_kb
class TexRetriever:
    def __init__(self,kb_root:str,grid_w:int=None,grid_h:int=None,inline_slots:int=4):
        self.kb=KnowledgeBase(kb_root)
        self.grid_w=grid_w;self.grid_h=grid_h;self.inline_slots=inline_slots
        self._grid:TexGrid=None
        self._keys:List[str]=[]
        self._dirty=True
    def build(self):
        self._grid,self._keys=build_from_kb(self.kb,self.grid_w,self.grid_h,self.inline_slots)
        self._dirty=False
    def add(self,key:str,text:str,**kw):
        result=self.kb.add(key,text,**kw)
        if self._grid is not None and not self._dirty:
            try:
                idx=self._keys.index(key)
            except ValueError:
                idx=len(self._keys)
                self._keys.append(key)
            self._grid.insert(idx,key,text)
        else:self._dirty=True
        return result
    def retrieve(self,query:str,k:int=3,max_chars_per:int=600)->List[Tuple[str,str,int]]:
        if self._grid is None or self._dirty:self.build()
        ranked=self._grid.query(query,k=k)
        out=[]
        for eid,score in ranked:
            if 0<=eid<len(self._keys):
                key=self._keys[eid]
                txt=self.kb.lookup(key) or ''
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
    def stats(self):
        s=self.kb.stats()
        if self._grid is not None:s['tex_grid']=self._grid.stats()
        return s
    def close(self):self.kb.close()
