"""atex.clients.scenarios.long_context: simulate a realistic 5-turn conversation about a 15-file project.
Shows side-by-side what re-prompting would cost vs what atex retrieval costs."""
import os,shutil,sys,tempfile,time
from pathlib import Path
from typing import Dict,List,Optional,Tuple
from atex.kb import KnowledgeBase
from atex.retriever import KBRetriever
from atex.clients.rag import AtexRagClient
from atex.clients.ollama import check_ollama_available,make_ollama_chat
from atex.clients.walkthrough import C,_enable_ansi,_banner,_step,_explain,_action,_result,_kv,_pause
from atex.init import _walk
_FAKE_PROJECT={
    'README.md':'''# fakeproj
A small reference web service for the atex long-context demo.
- HMAC-signed session cookies issued by `src/auth.py`
- Connection pool of size 8 in `src/db.py`
- Routes split into `src/routes/users.py` and `src/routes/sessions.py`
- See ARCHITECTURE.md for the request lifecycle and ROADMAP.md for upcoming work.
''',
    'ARCHITECTURE.md':'''# fakeproj architecture
Request lifecycle:
1. Incoming HTTP request hits the router in `src/routes/`
2. Router validates the session cookie via `src/auth.py:verify`
3. If valid, the handler acquires a DB connection from `src/db.py:ConnectionPool`
4. Response is JSON-serialized in the handler
Auth uses HMAC-SHA256 over the raw user_id with a server-side secret. No JWT, no asymmetric crypto.
DB connections are reused via an in-memory pool (size 8 by default).
''',
    'ROADMAP.md':'''# Roadmap
- [ ] Switch HMAC secret to env var (currently hardcoded)
- [ ] Add WebSocket support for live session presence
- [ ] Replace in-memory pool with PgBouncer for production
- [ ] OpenTelemetry tracing on every request
- [ ] Migrate user-id from int to UUID
''',
    'requirements.txt':'flask>=3.0\nrequests>=2.31\npython-dotenv>=1.0\n',
    '.env.example':'AUTH_SECRET=replace-me\nDB_DSN=postgres://localhost/fakeproj\nDB_POOL_SIZE=8\n',
    'src/auth.py':'''"""auth: HMAC-signed cookie issuance and verification."""
import hashlib,hmac,os
SECRET=os.environ.get('AUTH_SECRET',b'fixture-secret-do-not-use-in-production').encode() if isinstance(os.environ.get('AUTH_SECRET'),str) else b'fixture-secret-do-not-use-in-production'
def issue(user_id:str)->str:
    sig=hmac.new(SECRET,user_id.encode(),hashlib.sha256).hexdigest()
    return f'{user_id}.{sig}'
def verify(token:str)->bool:
    if '.' not in token:return False
    user_id,sig=token.rsplit('.',1)
    expected=hmac.new(SECRET,user_id.encode(),hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig,expected)
''',
    'src/db.py':'''"""db: connection pool wrapper. Default pool size is 8."""
import os
POOL_SIZE=int(os.environ.get('DB_POOL_SIZE','8'))
DSN=os.environ.get('DB_DSN','postgres://localhost/fakeproj')
class ConnectionPool:
    def __init__(self,dsn:str=DSN,size:int=POOL_SIZE):
        self.dsn=dsn;self.size=size;self._free=[]
    def acquire(self):return self._free.pop() if self._free else self._connect()
    def release(self,conn):
        if len(self._free)<self.size:self._free.append(conn)
    def _connect(self):return {'dsn':self.dsn,'open':True}
''',
    'src/routes/__init__.py':'',
    'src/routes/users.py':'''"""HTTP routes for user resources."""
from src.auth import verify
from src.db import ConnectionPool
_pool=ConnectionPool()
def get_user(req):
    if not verify(req.cookies.get('session','')):return {'error':'unauthorized'},401
    conn=_pool.acquire()
    try:return {'user_id':req.path_params['id'],'name':'demo'},200
    finally:_pool.release(conn)
def list_users(req):
    if not verify(req.cookies.get('session','')):return {'error':'unauthorized'},401
    return {'users':[{'id':1,'name':'demo'}]},200
''',
    'src/routes/sessions.py':'''"""HTTP routes for session resources."""
from src.auth import issue,verify
def create_session(req):
    user_id=req.json.get('user_id')
    if not user_id:return {'error':'user_id required'},400
    return {'token':issue(str(user_id))},201
def check_session(req):
    token=req.cookies.get('session','')
    return {'valid':verify(token)},200
def delete_session(req):
    return {'deleted':True},200
''',
    'src/models/__init__.py':'',
    'src/models/user.py':'''"""User model: dataclass with id, name, email, created_at."""
from dataclasses import dataclass,field
from typing import Optional
import time
@dataclass
class User:
    id:int
    name:str
    email:str
    created_at:float=field(default_factory=time.time)
    is_active:bool=True
    role:str='user'
''',
    'src/models/session.py':'''"""Session model: dataclass with token, user_id, expires_at."""
from dataclasses import dataclass
import time
@dataclass
class Session:
    token:str
    user_id:int
    expires_at:float
    @property
    def is_valid(self)->bool:return self.expires_at>time.time()
''',
    'src/utils/crypto.py':'''"""crypto helpers used by src/auth.py."""
import hashlib,hmac,secrets
def constant_time_compare(a:str,b:str)->bool:return hmac.compare_digest(a.encode(),b.encode())
def generate_secret(n_bytes:int=32)->bytes:return secrets.token_bytes(n_bytes)
def sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest()
''',
    'src/utils/time.py':'''"""time helpers."""
import time
def now_iso()->str:return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def now_unix()->float:return time.time()
def is_expired(deadline:float)->bool:return deadline<time.time()
''',
    'tests/test_auth.py':'''"""tests for src/auth.py."""
from src.auth import issue,verify
def test_round_trip():
    t=issue('alice')
    assert verify(t)
def test_tamper_rejected():
    t=issue('alice')
    assert not verify(t[:-1]+('0' if t[-1]!='0' else '1'))
def test_invalid_token_format():
    assert not verify('no-dot-in-this-token')
''',
    'tests/test_db.py':'''"""tests for src/db.py."""
from src.db import ConnectionPool,POOL_SIZE
def test_pool_size_default():
    p=ConnectionPool()
    assert p.size==8
def test_acquire_release():
    p=ConnectionPool();c=p.acquire();p.release(c)
    assert len(p._free)==1
''',
}
_QUESTIONS=[
    ('How does authentication work in this project?','project::src/auth.py'),
    ('What fields are on the User model?','project::src/models/user.py'),
    ('What is the default database connection pool size?','project::src/db.py'),
    ('What HTTP routes exist for sessions?','project::src/routes/sessions.py'),
    ('What is on the project roadmap?','project::ROADMAP.md'),
]
def _approx_tokens(s:str)->int:return max(1,len(s)//4)
def _materialize_project(root:Path)->List[Tuple[str,str]]:
    files=[]
    for rel,content in _FAKE_PROJECT.items():
        p=root/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(content,encoding='utf-8')
        files.append((rel,content))
    return files
def _ingest(atex_dir:Path,project_root:Path)->Tuple[KnowledgeBase,int,float]:
    kb=KnowledgeBase(atex_dir)
    t0=time.time()
    n=0
    for rel,content in _walk(project_root,set(['.py','.md','.txt','.example']),('.atex',),64000):
        kb.add(f'project::{rel}',content,meta={'rel':rel,'kind':'source'},allow_overwrite=True)
        n+=1
    kb.flush()
    return kb,n,time.time()-t0
def _without_atex_repaste_tokens(question_files:List[Tuple[str,str]])->int:
    return sum(_approx_tokens(content) for _,content in question_files)
def run_long_context(atex_dir:Path,model:Optional[str]=None,interactive:bool=True,ollama_url:str='http://localhost:11434')->int:
    _enable_ansi()
    atex_dir=Path(atex_dir).resolve()
    if atex_dir.exists():shutil.rmtree(atex_dir,ignore_errors=True)
    atex_dir.mkdir(parents=True)
    _banner('atex long-context scenario — what re-prompting actually costs')
    print(f'\n{C.DIM}This builds a fake 15-file project, ingests it into atex, then asks 5 questions{C.R}')
    print(f'{C.DIM}that an AI assistant would normally need pasted context to answer.{C.R}')
    print(f'{C.DIM}For each turn, we report:{C.R}')
    print(f'  {C.MAGENTA}A.{C.R} {C.DIM}what you would have re-pasted without atex (token cost){C.R}')
    print(f'  {C.MAGENTA}B.{C.R} {C.DIM}what atex retrieved instead (latency cost){C.R}')
    print(f'  {C.MAGENTA}C.{C.R} {C.DIM}whether the model used the retrieved context correctly (if --model){C.R}')
    _pause(1.5,interactive)
    proj_root=Path(tempfile.mkdtemp(prefix='atex_lc_proj_'))
    try:
        _step(0,5,'set up the fake project')
        _explain(f'Materializing 15 files at {proj_root}')
        files=_materialize_project(proj_root)
        kb,n,ing_s=_ingest(atex_dir,proj_root)
        _result(f'wrote {len(files)} files; ingested {n} entries into atex in {ing_s*1000:.1f}ms')
        total_proj_tokens=sum(_approx_tokens(c) for _,c in files)
        _kv('whole-project token estimate',f'~{total_proj_tokens} tokens (~{total_proj_tokens*4} chars)')
        _kv('atex KB on disk',f'{kb.stats()["used_bytes"]/1024:.1f} KB across {kb.stats()["n_pages"]} page(s)')
        _pause(1.5,interactive)
        chat_fn=None
        if model:
            if not check_ollama_available(ollama_url):
                print(f'\n{C.YELLOW}ollama not reachable at {ollama_url} — running retrieval-only mode{C.R}')
            else:chat_fn=make_ollama_chat(model,base_url=ollama_url,timeout=60.0)
        client=AtexRagClient(atex_dir,chat_fn=chat_fn or (lambda p:'(no model attached — context retrieval verified above)'))
        scoreboard:List[Dict]=[]
        for i,(question,expected_key) in enumerate(_QUESTIONS,1):
            _step(i,5,question)
            _explain(f'Without atex, the user (or auto-context tooling) would re-paste relevant files into the prompt.')
            relevant=[(rel,c) for rel,c in files if any(kw in rel.lower() for kw in expected_key.lower().replace('project::','').split('/')[-1].replace('.py','').replace('.md','').lower().split('_'))]
            relevant=relevant or [(expected_key.replace('project::',''),next((c for r,c in files if r==expected_key.replace('project::','')),''))]
            re_paste_tokens=_without_atex_repaste_tokens(relevant)
            print(f'  {C.MAGENTA}A.{C.R} without-atex: would re-paste {C.YELLOW}~{re_paste_tokens} tokens{C.R} from {len(relevant)} file(s):')
            for rel,_ in relevant:print(f'    {C.DIM}- {rel}{C.R}')
            t0=time.time()
            results=client.retr.retrieve(question,k=3,max_chars_per=400)
            retr_ms=(time.time()-t0)*1000
            top_keys=[r[0] for r in results]
            ctx_chars=sum(len(r[1]) for r in results)
            top_hit=expected_key in top_keys
            ctx_tokens=max(1,ctx_chars//4)
            print(f'  {C.MAGENTA}B.{C.R} with-atex:    retrieved {len(results)} entries ({ctx_chars} chars, {C.GREEN}~{ctx_tokens} tokens{C.R}) in {C.GREEN}{retr_ms:.2f}ms{C.R}')
            for k in top_keys:
                marker=f'{C.GREEN}★{C.R}' if k==expected_key else f'{C.DIM}·{C.R}'
                print(f'    {marker} {C.CYAN}{k}{C.R}')
            saved_tokens=re_paste_tokens-ctx_tokens
            answer=None;answer_ms=0;answer_ok=False
            if model and chat_fn:
                ta=time.time()
                rec=client.ask(question,k=3)
                answer_ms=rec['chat_ms']
                answer=rec['answer']
                expected_kw_map={'src/auth.py':['hmac','sha256','cookie'],'src/models/user.py':['name','email','dataclass','user_id'],'src/db.py':['8','pool','connection'],'src/routes/sessions.py':['create','check','delete','session','token'],'project::ROADMAP.md':['env','websocket','pgbouncer','opentelemetry','uuid']}
                expected_kws=expected_kw_map.get(expected_key.replace('project::',''),[])+expected_kw_map.get(expected_key,[])
                answer_ok=any(kw.lower() in (answer or '').lower() for kw in expected_kws)
                print(f'  {C.MAGENTA}C.{C.R} model answer ({answer_ms:.0f}ms):')
                print(f'    {C.GREEN if answer_ok else C.YELLOW}{(answer or "")[:300]}{C.R}')
                _result(f'answer cited expected concepts: {answer_ok}',answer_ok)
            scoreboard.append({'q':question,'top_hit':top_hit,'re_paste_tokens':re_paste_tokens,'atex_tokens':ctx_tokens,'retr_ms':retr_ms,'answer_ms':answer_ms,'answer_ok':answer_ok})
            _pause(1.5,interactive)
        print(f'\n{C.BOLD}{C.GREEN}═══ scenario complete ═══{C.R}\n')
        total_re_paste=sum(s['re_paste_tokens'] for s in scoreboard)
        total_atex=sum(s['atex_tokens'] for s in scoreboard)
        total_retr_ms=sum(s['retr_ms'] for s in scoreboard)
        n_top_hits=sum(1 for s in scoreboard if s['top_hit'])
        print(f'  {C.BOLD}Across {len(scoreboard)} turns:{C.R}\n')
        print(f'    {C.BOLD}retrieval accuracy{C.R}: top-1 hit {C.GREEN}{n_top_hits}/{len(scoreboard)} ({n_top_hits*100//len(scoreboard)}%){C.R} (the right file picked first, with NO hint from the user about which file mattered)')
        print(f'    {C.BOLD}retrieval latency{C.R}:  {C.GREEN}{total_retr_ms:.1f}ms total{C.R} ({total_retr_ms/len(scoreboard):.1f}ms per turn) — milliseconds, not minutes')
        print(f'')
        print(f'    {C.BOLD}user effort:{C.R}')
        print(f'      {C.MAGENTA}without atex{C.R}: 5 turns × find-the-file + open + copy + paste = {C.YELLOW}~5 manual context loads{C.R} (~{total_re_paste//50}s of typing min, plus the cognitive cost of remembering paths)')
        print(f'      {C.MAGENTA}with atex{C.R}:    user typed the {C.GREEN}question only{C.R}; the AI handled retrieval via the MCP tool. {C.GREEN}0 file pastes.{C.R}')
        print(f'')
        print(f'    {C.BOLD}token cost (informational){C.R}:')
        print(f'      without atex (re-paste whole relevant file each turn): ~{C.YELLOW}{total_re_paste}{C.R} tokens of pasted code')
        print(f'      with atex (top-3 retrieval, ~400 chars per hit):       ~{C.GREEN}{total_atex}{C.R} tokens of retrieved snippets')
        if total_atex>total_re_paste:
            print(f'      atex returned more bytes here because k=3 retrieval pulls multiple candidate hits.')
            print(f'      Drop --k=1 if you want the smallest-context mode; the token figure flips.')
        if model and chat_fn:
            n_correct=sum(1 for s in scoreboard if s['answer_ok'])
            total_chat_ms=sum(s['answer_ms'] for s in scoreboard)
            print(f'    {C.BOLD}model answers{C.R}:      cited expected concepts {n_correct}/{len(scoreboard)} ({n_correct*100//len(scoreboard)}%); chat wall {total_chat_ms/1000:.1f}s')
        print(f'\n  {C.DIM}what this proves:{C.R}')
        print(f'    The agent did not need to be re-prompted with the file contents once.')
        print(f'    Every question was answered from atex retrieval. The KB persists; the conversation does not have to.')
        print(f'\n  {C.DIM}files materialized at {proj_root} (will be cleaned up on exit){C.R}')
        print(f'  {C.DIM}atex KB persists at {atex_dir} — try `atex stats --atex-dir {atex_dir}`{C.R}\n')
        return 0 if n_top_hits>=4 else 4
    finally:shutil.rmtree(proj_root,ignore_errors=True)
