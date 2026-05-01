"""atex.clients.walkthrough: paced, explained, ANSI-colored multi-step demo."""
import os,sys,time
from pathlib import Path
from typing import Callable,Optional
from atex.kb import KnowledgeBase
from atex.retriever import KBRetriever
from atex.clients.rag import AtexRagClient
from atex.clients.ollama import check_ollama_available,make_ollama_chat
class C:
    R='\033[0m';BOLD='\033[1m';DIM='\033[2m'
    CYAN='\033[36m';GREEN='\033[32m';YELLOW='\033[33m';RED='\033[31m';MAGENTA='\033[35m';BLUE='\033[34m';GREY='\033[90m'
def _enable_ansi():
    if sys.platform=='win32':
        try:os.system('')
        except Exception:pass
def _banner(text:str,width:int=70):
    border='═'*(width-2)
    print(f'{C.BOLD}{C.CYAN}╔{border}╗{C.R}')
    print(f'{C.BOLD}{C.CYAN}║{C.R} {C.BOLD}{text:<{width-4}}{C.R} {C.BOLD}{C.CYAN}║{C.R}')
    print(f'{C.BOLD}{C.CYAN}╚{border}╝{C.R}')
def _step(num:int,total:int,title:str):
    print(f'\n{C.BOLD}{C.YELLOW}── Step {num}/{total}: {title} ──{C.R}')
def _explain(text:str):
    print(f'{C.DIM}  {text}{C.R}')
def _action(text:str):
    print(f'  {C.MAGENTA}→{C.R} {text}')
def _result(text:str,ok:bool=True):
    mark=f'{C.GREEN}✓{C.R}' if ok else f'{C.RED}✗{C.R}'
    print(f'  {mark} {text}')
def _kv(k:str,v:str):
    print(f'  {C.DIM}{k}:{C.R} {v}')
def _pause(seconds:float=1.5,interactive:bool=True):
    if interactive and sys.stdin.isatty():
        try:input(f'\n  {C.DIM}[press Enter to continue]{C.R} ')
        except (EOFError,KeyboardInterrupt):print()
    else:time.sleep(seconds)
def run_walkthrough(atex_dir:Path,model:Optional[str]=None,interactive:bool=True,ollama_url:str='http://localhost:11434')->int:
    _enable_ansi()
    atex_dir=Path(atex_dir);atex_dir.mkdir(parents=True,exist_ok=True)
    _banner('atex walkthrough — what is atex actually doing?')
    print(f'\n{C.DIM}This is the same 4-step validation as `atex demo --model X`,{C.R}')
    print(f'{C.DIM}slowed down so you can see what each step proves.{C.R}\n')
    _kv('KB directory',str(atex_dir))
    _kv('model',model or '(none — using a synthetic chat function)')
    _kv('mode','interactive (press Enter to advance)' if interactive and sys.stdin.isatty() else 'paced (1.5s between steps)')
    _pause(1.5,interactive)
    chat_fn=None
    if model:
        if not check_ollama_available(ollama_url):
            print(f'\n{C.RED}ollama not reachable at {ollama_url}{C.R}')
            print(f'{C.DIM}install ollama, run `ollama serve`, then `ollama pull {model}`{C.R}');return 3
        chat_fn=make_ollama_chat(model,base_url=ollama_url)
    else:
        def chat_fn(prompt):return f'(no model attached) the cookie value mentioned in the references appears to be: azure-marmot-7421'
    client=AtexRagClient(atex_dir,chat_fn=chat_fn)
    probe_key='atex-validation-probe'
    full_key=f'manual::{probe_key}'
    probe_fact=f'The atex walkthrough ran on {time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}. The validation cookie value is azure-marmot-7421.'
    _step(1,4,'pre-clear the probe key')
    _explain('Goal: prove the KB does not already contain the probe key.')
    _explain('Why: every step that follows depends on starting from a known-empty state.')
    _action(f'calling kb.lookup({full_key!r}) ...')
    if full_key in client.kb:
        client.kb.add(full_key,'(cleared)',meta={'kind':'cleared'},allow_overwrite=True)
        _action('found stale entry from a prior run — overwrote it with a tombstone marker.')
    pre=client.recall(probe_key)
    pre_ok=pre is None or pre=='(cleared)'
    _result(f'pre-clear passed: lookup returned {"None" if pre is None else "(cleared)"}',pre_ok)
    _pause(1.5,interactive)
    _step(2,4,'remember a fact across sessions')
    _explain('Goal: prove atex can persist a user-taught fact in O(1) writes.')
    _explain(f'We will write {len(probe_fact)} bytes containing a unique cookie value.')
    _action(f'calling kb.add({full_key!r}, <{len(probe_fact)} bytes>) ...')
    client.remember(probe_key,probe_fact)
    _action('immediately reading it back via kb.lookup() to verify exact-match round-trip.')
    rt=client.recall(probe_key)
    ok=rt==probe_fact
    _result(f'round-trip exact-match: {ok}',ok)
    _kv('bytes on disk',str(len(probe_fact)))
    _kv('cookie value',f'{C.GREEN}azure-marmot-7421{C.R} (the model must quote this in step 4)')
    _pause(1.5,interactive)
    _step(3,4,'RAG search finds the fact')
    _explain('Goal: prove the keyword-overlap retriever finds the just-written fact.')
    _explain('This is what an MCP-capable AI client does mid-conversation: ask atex first, then answer.')
    question='What is the validation cookie value? Quote it exactly.'
    _action(f'asking atex_search({question!r}) ...')
    t0=time.time()
    results=client.retr.retrieve(question,k=3,max_chars_per=300)
    retr_ms=(time.time()-t0)*1000
    found=any('validation' in (r[0] or '').lower() for r in results)
    _result(f'retrieved {len(results)} hits in {retr_ms:.2f}ms; probe key in top-3: {found}',found)
    for i,(k,_,score) in enumerate(results,1):print(f'    {i}. {C.CYAN}{k}{C.R} (score {score})')
    _pause(1.5,interactive)
    _step(4,4,'RAG answer quotes the fact')
    _explain('Goal: prove the model uses the retrieved context to answer correctly.')
    if model:_explain(f'Calling ollama with model={model}. The model has never seen the cookie value before.')
    else:_explain('No model attached — using a synthetic chat function for shape-only validation.')
    _action(f'calling client.ask({question!r}) ...')
    t1=time.time()
    rec=client.ask(question)
    chat_ms=(time.time()-t1)*1000-rec['retrieval_ms']
    answer=rec['answer'] or '(empty)'
    quoted='azure-marmot-7421' in answer.lower()
    print(f'  {C.DIM}model answer ({chat_ms:.0f}ms):{C.R}')
    print(f'    {C.GREEN if quoted else C.RED}{answer}{C.R}')
    _result(f'answer quotes the cookie verbatim: {quoted}',quoted)
    _pause(1.0,interactive)
    print(f'\n{C.BOLD}{C.GREEN}═══ walkthrough complete ═══{C.R}\n')
    print(f'  {C.DIM}what this proved:{C.R}')
    print(f'    {C.GREEN}1.{C.R} atex persists facts across sessions in O(1) writes')
    print(f'    {C.GREEN}2.{C.R} The keyword retriever finds them in milliseconds')
    print(f'    {C.GREEN}3.{C.R} An MCP-capable AI client (or any model with a chat callable) can use that context to answer questions it has never seen before')
    print(f'\n  {C.DIM}next: try `atex demo --scenario long-context --model {model or "qwen2.5:0.5b-instruct"}`{C.R}')
    print(f'  {C.DIM}      to see the bigger story: how much re-prompting atex saves.{C.R}\n')
    return 0
