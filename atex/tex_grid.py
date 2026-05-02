"""atex.tex_grid: a texture-shaped inverted index for O(num_query_tokens) lookup. Public-safe, CPU-only, no external deps.
Each token hashes to a 2D grid cell; the cell's 4 slots hold up to 4 entry-ids inline; overflow spills to a per-cell list.
Query cost is independent of corpus size (it scales with the query length, not the KB size).
"""
import hashlib,re,struct
from typing import Dict,List,Optional,Tuple
_TOK_RE=re.compile(r"[a-zA-Z][a-zA-Z0-9_\-\.]*")
_STOP=frozenset({'the','a','an','and','or','of','to','in','for','is','are','what','how','do','i','my','this','that','with','on','at','by','as','it','be','can','use','using','from','some','any','have','has','will','would','should','could','make','get','set','put','show','give','tell','please','help'})
def _tokenize(text:str)->List[str]:
    return [t.lower() for t in _TOK_RE.findall(text or '') if t.lower() not in _STOP and len(t)>=2]
def _hash_xy(token:str,w:int,h:int)->Tuple[int,int]:
    digest=hashlib.blake2b(token.encode('utf-8'),digest_size=8).digest()
    n=struct.unpack('<Q',digest)[0]
    return (n%w),((n//w)%h)
def auto_grid_dim(n_entries_estimate:int,target_load:float=0.5)->int:
    if n_entries_estimate<=0:return 256
    target_cells=max(256,int(n_entries_estimate*8/target_load))
    side=1
    while side*side<target_cells:side*=2
    return min(side,4096)
class TexGrid:
    def __init__(self,grid_w:int=256,grid_h:int=256,inline_slots:int=4):
        self.grid_w=grid_w
        self.grid_h=grid_h
        self.inline_slots=inline_slots
        try:
            import numpy as np
            self._np=np
            self._grid=np.zeros((grid_h,grid_w,inline_slots),dtype=np.int32)
            self._next_slot=np.zeros((grid_h,grid_w),dtype=np.uint8)
        except ImportError:
            self._np=None
            self._grid=[[[0]*inline_slots for _ in range(grid_w)] for _ in range(grid_h)]
            self._next_slot=[[0]*grid_w for _ in range(grid_h)]
        self._overflow:Dict[Tuple[int,int],List[int]]={}
        self._n_entries=0
        self._n_tokens_indexed=0
    def insert(self,entry_id:int,key:str,text:str):
        tokens=set(_tokenize(key))|set(_tokenize(text))
        eid=entry_id+1
        for tok in tokens:
            x,y=_hash_xy(tok,self.grid_w,self.grid_h)
            if self._np is not None:
                slot=int(self._next_slot[y,x])
                if slot<self.inline_slots:
                    self._grid[y,x,slot]=eid
                    self._next_slot[y,x]=slot+1
                else:self._overflow.setdefault((x,y),[]).append(eid)
            else:
                slot=self._next_slot[y][x]
                if slot<self.inline_slots:
                    self._grid[y][x][slot]=eid
                    self._next_slot[y][x]=slot+1
                else:self._overflow.setdefault((x,y),[]).append(eid)
            self._n_tokens_indexed+=1
        self._n_entries=max(self._n_entries,entry_id+1)
    def query(self,q:str,k:int=5)->List[Tuple[int,int]]:
        q_tokens=_tokenize(q)
        if not q_tokens:return []
        scores:Dict[int,int]={}
        for tok in q_tokens:
            x,y=_hash_xy(tok,self.grid_w,self.grid_h)
            if self._np is not None:
                row=self._grid[y,x]
                for slot in range(int(self._next_slot[y,x])):
                    eid=int(row[slot])
                    if eid:scores[eid-1]=scores.get(eid-1,0)+1
            else:
                row=self._grid[y][x]
                for slot in range(self._next_slot[y][x]):
                    eid=row[slot]
                    if eid:scores[eid-1]=scores.get(eid-1,0)+1
            if (x,y) in self._overflow:
                for eid in self._overflow[(x,y)]:scores[eid-1]=scores.get(eid-1,0)+1
        ranked=sorted(scores.items(),key=lambda kv:(-kv[1],kv[0]))
        return ranked[:k]
    def stats(self)->Dict:
        n_used=0;total_overflow=0
        if self._np is not None:n_used=int((self._next_slot>0).sum())
        else:
            for row in self._next_slot:
                for v in row:
                    if v>0:n_used+=1
        for v in self._overflow.values():total_overflow+=len(v)
        capacity=self.grid_w*self.grid_h*self.inline_slots
        return {'grid_w':self.grid_w,'grid_h':self.grid_h,'inline_slots':self.inline_slots,'n_entries':self._n_entries,'n_tokens_indexed':self._n_tokens_indexed,'cells_used':n_used,'cells_total':self.grid_w*self.grid_h,'overflow_cells':len(self._overflow),'overflow_slots':total_overflow,'inline_capacity':capacity,'utilization':self._n_tokens_indexed/capacity if capacity else 0,'numpy_backend':self._np is not None}
def build_from_kb(kb,grid_w:Optional[int]=None,grid_h:Optional[int]=None,inline_slots:int=4)->Tuple['TexGrid',List[str]]:
    keys=kb.keys()
    if grid_w is None or grid_h is None:
        side=auto_grid_dim(len(keys))
        grid_w=grid_w or side
        grid_h=grid_h or side
    grid=TexGrid(grid_w,grid_h,inline_slots)
    for i,k in enumerate(keys):
        text=kb.lookup(k) or ''
        grid.insert(i,k,text)
    return grid,keys
