"""KnowledgeBase: lossless byte-page key-value store with mmap reads and a JSON address index.
Append cost is O(1). Keyed lookup is O(1) via mmap. Substring/prefix scans are O(n).
Storage layout (per page):
    pages/page_<idx:06d>.kb.page    raw byte stream, default 4096*64*4 = 1 MiB per page
Index (JSON, root-level):
    {
        "schema_version": 1,
        "pages": [{"filename": "page_000000.kb.page", "used_bytes": N}, ...],
        "entries": {
            "<key>": {"page_idx": 0, "offset": 12345, "length": 678, "meta": {...}}
        },
        "n_entries": <count>,
        "page_w": <int>, "page_h": <int>,
        "created": <iso8601>,
        "tokenizer": "utf-8_bytes"
    }
Encoding: byte-level UTF-8 (no tokenization). Faster + smaller than embedding-based stores for exact-recall workloads.
Usage:
    kb = KnowledgeBase('.atex')
    kb.add('project::src/auth.py', '<file contents>')
    kb.lookup('project::src/auth.py')
    kb.lookup_prefix('project::src/')
    kb.stats()
"""
import json,time,mmap,os,atexit
from pathlib import Path
from typing import Dict,List,Optional,Tuple
_DEFAULT_PAGE_W=int(os.environ.get('ATEX_PAGE_W','4096'))
_DEFAULT_PAGE_H=int(os.environ.get('ATEX_PAGE_H','64'))
_MAGIC=b'ATEXKB01'
_AUTOSAVE_EVERY=int(os.environ.get('ATEX_AUTOSAVE_EVERY','100'))
_REPLACE_RETRIES=int(os.environ.get('ATEX_REPLACE_RETRIES','12'))
_REPLACE_BACKOFF=float(os.environ.get('ATEX_REPLACE_BACKOFF','0.05'))
class KnowledgeBaseError(Exception):pass
class KnowledgeBase:
    def __init__(self,root_dir,page_w:Optional[int]=None,page_h:Optional[int]=None):
        self.root=Path(root_dir)
        self.root.mkdir(parents=True,exist_ok=True)
        self.pages_dir=self.root/'pages'
        self.pages_dir.mkdir(exist_ok=True)
        self.index_path=self.root/'index.json'
        self._dirty=False
        self._adds_since_save=0
        if self.index_path.exists():
            self.index=json.loads(self.index_path.read_text(encoding='utf-8'))
            self.page_w=int(self.index.get('page_w',_DEFAULT_PAGE_W))
            self.page_h=int(self.index.get('page_h',_DEFAULT_PAGE_H))
        else:
            self.page_w=page_w or _DEFAULT_PAGE_W
            self.page_h=page_h or _DEFAULT_PAGE_H
            self.index={'schema_version':1,'magic':_MAGIC.decode(),'page_w':self.page_w,'page_h':self.page_h,'pages':[],'entries':{},'n_entries':0,'tokenizer':'utf-8_bytes','created':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
            self._save_index()
        self._page_bytes=self.page_w*self.page_h*4
        self._mmaps={}
        atexit.register(self._atexit_flush)
    @property
    def page_bytes(self)->int:return self._page_bytes
    def _save_index(self):
        tmp=self.index_path.with_suffix('.tmp')
        payload=json.dumps(self.index,indent=2)
        last_err=None
        for i in range(_REPLACE_RETRIES):
            try:
                tmp.write_text(payload,encoding='utf-8')
                tmp.replace(self.index_path)
                self._dirty=False
                self._adds_since_save=0
                return
            except PermissionError as e:
                last_err=e
                time.sleep(_REPLACE_BACKOFF*(2**min(i,6)))
        raise KnowledgeBaseError(f'index save failed after {_REPLACE_RETRIES} retries: {last_err}')
    def flush(self):
        if self._dirty:self._save_index()
    def _atexit_flush(self):
        try:self.flush()
        except Exception:pass
    def _maybe_save(self):
        self._dirty=True
        self._adds_since_save+=1
        if self._adds_since_save>=_AUTOSAVE_EVERY:self._save_index()
    def _new_page(self):
        idx=len(self.index['pages'])
        fname=f'page_{idx:06d}.kb.page'
        path=self.pages_dir/fname
        with open(path,'wb') as f:f.truncate(self._page_bytes)
        meta={'filename':fname,'idx':idx,'used_bytes':0,'created':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        self.index['pages'].append(meta)
        self._save_index()
        return idx,path,meta
    def __enter__(self):return self
    def __exit__(self,*a):self.flush()
    def _current_page(self):
        if not self.index['pages']:return self._new_page()
        meta=self.index['pages'][-1]
        return meta['idx'],self.pages_dir/meta['filename'],meta
    def _ensure_capacity(self,n_bytes):
        idx,path,meta=self._current_page()
        if meta['used_bytes']+n_bytes>self._page_bytes:return self._new_page()
        return idx,path,meta
    def add(self,key:str,text:str,meta:Optional[Dict]=None,allow_overwrite:bool=True)->str:
        if not key:raise KnowledgeBaseError('empty key')
        if key in self.index['entries']:
            if not allow_overwrite:raise KnowledgeBaseError(f'key exists: {key}')
            self._mmaps.clear()
        data=text.encode('utf-8') if isinstance(text,str) else bytes(text)
        if len(data)>self._page_bytes:raise KnowledgeBaseError(f'entry too large for one page: {len(data)} > {self._page_bytes}')
        idx,path,page_meta=self._ensure_capacity(len(data))
        with open(path,'r+b') as f:
            f.seek(page_meta['used_bytes'])
            f.write(data)
        offset=page_meta['used_bytes']
        page_meta['used_bytes']+=len(data)
        self.index['entries'][key]={'page_idx':idx,'offset':offset,'length':len(data),'meta':meta or {}}
        self.index['n_entries']=len(self.index['entries'])
        self._maybe_save()
        return key
    def add_batch(self,items)->int:
        n=0
        for it in items:
            self.add(it['key'],it['text'],meta=it.get('meta'))
            n+=1
        self.flush()
        return n
    def _mmap_page(self,page_idx:int):
        if page_idx in self._mmaps:return self._mmaps[page_idx]
        path=self.pages_dir/self.index['pages'][page_idx]['filename']
        with open(path,'rb') as f:
            mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
        self._mmaps[page_idx]=mm
        return mm
    def lookup(self,key:str)->Optional[str]:
        e=self.index['entries'].get(key)
        if e is None:return None
        mm=self._mmap_page(int(e['page_idx']))
        data=mm[int(e['offset']):int(e['offset'])+int(e['length'])]
        try:return data.decode('utf-8')
        except UnicodeDecodeError:return data.decode('utf-8',errors='replace')
    def lookup_prefix(self,prefix:str)->List[Tuple[str,str]]:
        out=[]
        for k in self.index['entries']:
            if k.startswith(prefix):
                v=self.lookup(k)
                if v is not None:out.append((k,v))
        return out
    def lookup_substring(self,needle:str,case_insensitive:bool=True,max_results:int=20)->List[Tuple[str,str]]:
        needle_l=needle.lower() if case_insensitive else needle
        out=[]
        for k in self.index['entries']:
            v=self.lookup(k) or ''
            hit=(needle_l in k.lower() or needle_l in v.lower()) if case_insensitive else (needle in k or needle in v)
            if hit:
                out.append((k,v))
                if len(out)>=max_results:break
        return out
    def keys(self)->List[str]:return list(self.index['entries'].keys())
    def __len__(self)->int:return int(self.index['n_entries'])
    def __contains__(self,key)->bool:return key in self.index['entries']
    def stats(self)->Dict:
        n_pages=len(self.index['pages'])
        used=sum(int(p['used_bytes']) for p in self.index['pages'])
        capacity=n_pages*self._page_bytes
        return {'n_entries':len(self),'n_pages':n_pages,'used_bytes':used,'capacity_bytes':capacity,'utilization':used/capacity if capacity else 0,'avg_bytes_per_entry':used/len(self) if len(self) else 0,'page_w':self.page_w,'page_h':self.page_h,'page_bytes':self._page_bytes}
    def close(self):
        self.flush()
        for mm in self._mmaps.values():
            try:mm.close()
            except Exception:pass
        self._mmaps.clear()
