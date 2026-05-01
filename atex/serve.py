"""atex.serve: MCP server exposing a local atex KB as tools to any MCP-compatible AI client."""
import argparse,json,re,sys,traceback
from pathlib import Path
try:sys.stdout.reconfigure(encoding='utf-8')
except Exception:pass
try:sys.stderr.reconfigure(encoding='utf-8')
except Exception:pass
from atex.kb import KnowledgeBase,KnowledgeBaseError
from atex.retriever import KBRetriever
_PROTOCOL_VERSION='2024-11-05'
_SERVER_NAME='atex'
_SERVER_VERSION='0.1.0'
_KEY_RE=re.compile(r'^[a-zA-Z0-9_\-./:]{1,256}$')
_MAX_REMEMBER_BYTES=int(__import__('os').environ.get('ATEX_MAX_REMEMBER_BYTES','1048576'))
_TOOLS=[{'name':'atex_search','description':'Search the local atex knowledge base for entries matching a natural-language query. Returns top-k entries by keyword overlap. Use this BEFORE asking the user to re-explain project context, conventions, or where things are defined.','inputSchema':{'type':'object','properties':{'query':{'type':'string','description':'Natural language query, e.g. "how does authentication work in this codebase"'},'k':{'type':'integer','description':'Number of results (default 5)','default':5}},'required':['query']}},{'name':'atex_recall','description':'Exact-key lookup in the atex knowledge base. Returns the stored text or null if the key does not exist. Useful when you have a specific path or identifier to look up (e.g. project::src/auth.ts).','inputSchema':{'type':'object','properties':{'key':{'type':'string','description':'Exact key (often "project::<rel-path>" or "manual::<topic>")'}},'required':['key']}},{'name':'atex_remember','description':'Persist a user-taught fact to the atex knowledge base under namespace "manual::". Use this when the user explicitly teaches you something they want remembered across sessions ("remember that X works like Y").','inputSchema':{'type':'object','properties':{'key':{'type':'string','description':'Short topic key, will be prefixed with "manual::". E.g. "auth-flow" becomes "manual::auth-flow".'},'text':{'type':'string','description':'The fact/explanation/snippet to remember.'}},'required':['key','text']}},{'name':'atex_list_keys','description':'List all keys in the atex KB matching a prefix. Use to discover what is known about a part of the project (e.g. prefix="project::src/auth").','inputSchema':{'type':'object','properties':{'prefix':{'type':'string','description':'Key prefix to filter by (use empty string for all keys).','default':''},'max':{'type':'integer','description':'Max keys to return (default 50)','default':50}},'required':['prefix']}},{'name':'atex_stats','description':'Get atex KB statistics: number of entries, pages on disk, MB used, etc.','inputSchema':{'type':'object','properties':{}}}]
def _send(msg):
    sys.stdout.write(json.dumps(msg)+'\n')
    sys.stdout.flush()
def _err(req_id,code,message,data=None):
    e={'code':code,'message':message}
    if data is not None:e['data']=data
    return {'jsonrpc':'2.0','id':req_id,'error':e}
def _ok(req_id,result):return {'jsonrpc':'2.0','id':req_id,'result':result}
def _validate_key(key:str)->str:
    if not isinstance(key,str) or not key:raise KnowledgeBaseError('key must be a non-empty string')
    if '..' in key:raise KnowledgeBaseError('key may not contain ".."')
    if not _KEY_RE.match(key):raise KnowledgeBaseError('key must match ^[a-zA-Z0-9_\\-./:]{1,256}$')
    return key
def _handle_initialize(req,kb):
    return _ok(req.get('id'),{'protocolVersion':_PROTOCOL_VERSION,'capabilities':{'tools':{}},'serverInfo':{'name':_SERVER_NAME,'version':_SERVER_VERSION}})
def _handle_tools_list(req,kb):return _ok(req.get('id'),{'tools':_TOOLS})
def _handle_tools_call(req,kb,retriever):
    p=req.get('params') or {}
    name=p.get('name','')
    args=p.get('arguments') or {}
    try:
        if name=='atex_search':
            results=retriever.retrieve(args.get('query',''),k=int(args.get('k',5)),max_chars_per=2000)
            content=[{'type':'text','text':retriever.format_as_context(results) if results else '(no results)'}]
            return _ok(req.get('id'),{'content':content,'isError':False})
        if name=='atex_recall':
            key=_validate_key(args.get('key',''))
            v=kb.lookup(key)
            content=[{'type':'text','text':v if v is not None else '(not found)'}]
            return _ok(req.get('id'),{'content':content,'isError':v is None})
        if name=='atex_remember':
            short_key=_validate_key(args.get('key',''))
            text=args.get('text','')
            if not isinstance(text,str):raise KnowledgeBaseError('text must be a string')
            if len(text.encode('utf-8'))>_MAX_REMEMBER_BYTES:raise KnowledgeBaseError(f'text exceeds {_MAX_REMEMBER_BYTES} bytes')
            full_key=f'manual::{short_key}'
            kb.add(full_key,text,meta={'kind':'manual','source':'atex_remember'},allow_overwrite=True)
            kb.flush()
            content=[{'type':'text','text':f'remembered as {full_key} ({len(text)} bytes)'}]
            return _ok(req.get('id'),{'content':content,'isError':False})
        if name=='atex_list_keys':
            prefix=args.get('prefix','')
            mx=int(args.get('max',50))
            keys=[k for k in kb.keys() if k.startswith(prefix)][:mx]
            content=[{'type':'text','text':'\n'.join(keys) if keys else '(no matches)'}]
            return _ok(req.get('id'),{'content':content,'isError':False})
        if name=='atex_stats':
            s=kb.stats()
            text=f'entries={s["n_entries"]} pages={s["n_pages"]} used={s["used_bytes"]/1e6:.2f}MB capacity={s["capacity_bytes"]/1e6:.2f}MB fill={s["utilization"]*100:.1f}%'
            return _ok(req.get('id'),{'content':[{'type':'text','text':text}],'isError':False})
        return _err(req.get('id'),-32601,f'unknown tool: {name}')
    except KnowledgeBaseError as e:
        return _err(req.get('id'),-32602,f'tool {name} invalid input: {e}')
    except Exception as e:
        return _err(req.get('id'),-32603,f'tool {name} failed: {type(e).__name__}: {e}',data={'traceback':traceback.format_exc()[:2000]})
def run(argv=None)->int:
    ap=argparse.ArgumentParser(prog='atex serve',description='MCP server exposing atex KB as tools')
    ap.add_argument('--atex-dir',required=True,help='path to .atex/ KB directory (created by atex init)')
    ap.add_argument('--log-file',default=None,help='write protocol log to this file (stderr default)')
    args=ap.parse_args(argv)
    atex=Path(args.atex_dir)
    if not (atex/'index.json').exists():print(f'[atex serve] ERROR: no index.json at {atex}; run "atex init" first',file=sys.stderr);return 2
    kb=KnowledgeBase(atex)
    retriever=KBRetriever(str(atex))
    log=open(args.log_file,'a',encoding='utf-8') if args.log_file else sys.stderr
    print(f'[atex serve] ready; {len(kb)} entries; tools: {[t["name"] for t in _TOOLS]}',file=log,flush=True)
    for line in sys.stdin:
        line=line.strip()
        if not line:continue
        try:req=json.loads(line)
        except json.JSONDecodeError as e:_send(_err(None,-32700,f'parse error: {e}'));continue
        method=req.get('method','')
        try:
            if method=='initialize':resp=_handle_initialize(req,kb)
            elif method=='initialized' or method=='notifications/initialized':continue
            elif method=='tools/list':resp=_handle_tools_list(req,kb)
            elif method=='tools/call':resp=_handle_tools_call(req,kb,retriever)
            elif method=='ping':resp=_ok(req.get('id'),{})
            elif method=='shutdown':resp=_ok(req.get('id'),None);_send(resp);break
            else:resp=_err(req.get('id'),-32601,f'unknown method: {method}')
        except Exception as e:resp=_err(req.get('id'),-32603,f'internal error: {e}',data={'traceback':traceback.format_exc()[:2000]})
        if 'id' in req:_send(resp)
    print('[atex serve] shutdown',file=log,flush=True)
    return 0
if __name__=='__main__':sys.exit(run())
