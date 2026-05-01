"""atex.bootstrap.demo: end-to-end first-run flow — detect clients, seed self-recall KB, wire configs with consent. Or with --model, run a local-model RAG validation loop."""
import argparse,os,sys
from pathlib import Path
from atex.bootstrap.detect import detect_all
from atex.bootstrap.configs import wire_client
from atex.kb import KnowledgeBase
def _run_model_validation(args)->int:
    from atex.clients.rag import AtexRagClient
    from atex.clients.ollama import check_ollama_available,list_ollama_models,make_ollama_chat
    from atex.clients.validate import run_validation_loop
    atex_dir=Path(args.atex_dir).resolve();atex_dir.mkdir(parents=True,exist_ok=True)
    n_seeded=_seed_kb(atex_dir,verbose=True)
    print(f'\n[atex demo --model {args.model}] checking ollama at {args.ollama_url}...')
    if not check_ollama_available(args.ollama_url):
        print(f'[atex demo] ollama not reachable at {args.ollama_url}.',file=sys.stderr)
        print('[atex demo] install ollama from https://ollama.com and run: ollama serve',file=sys.stderr)
        print(f'[atex demo] then: ollama pull {args.model}',file=sys.stderr)
        return 3
    models=list_ollama_models(args.ollama_url)
    print(f'[atex demo] ollama is up; available models: {models if models else "(none pulled yet)"}')
    if args.model not in models:
        bare=args.model.split(':')[0]
        if not any(m.split(':')[0]==bare for m in models):
            print(f'[atex demo] WARNING: "{args.model}" not in ollama-loaded models. Run: ollama pull {args.model}',file=sys.stderr)
    chat=make_ollama_chat(model=args.model,base_url=args.ollama_url)
    client=AtexRagClient(atex_dir,chat_fn=chat)
    print(f'[atex demo] running 4-step validation loop with model={args.model}...')
    res=run_validation_loop(client,model_label=args.model)
    print('\n'+res.summary())
    print(f'\n[atex demo] {n_seeded} seed entries available in {atex_dir}')
    return 0 if res.passed else 4
def _seed_dir()->Path:return Path(__file__).resolve().parent.parent/'seed'
def _seed_kb(atex_dir:Path,verbose:bool=True)->int:
    kb=KnowledgeBase(atex_dir);n=0
    for f in sorted(_seed_dir().glob('*.txt'))+sorted(_seed_dir().glob('*.md')):
        key=f'seed::{f.stem}'
        if key in kb:continue
        kb.add(key,f.read_text(encoding='utf-8'),meta={'kind':'seed','filename':f.name},allow_overwrite=False)
        n+=1
    kb.flush()
    if verbose:print(f'[atex demo] seeded KB with {n} entry/entries from {_seed_dir()}')
    return n
def _print_sample_prompts(server_name:str):
    print('')
    print('Sample prompts to try in your AI client (after restart):')
    print(f'  • "Use {server_name} to search for: what is atex?"')
    print(f'  • "Call {server_name}_stats and tell me the KB size"')
    print(f'  • "Remember via {server_name}: my project deploys via GitHub Actions"')
    print('')
def run_demo(argv=None)->int:
    ap=argparse.ArgumentParser(prog='atex demo',description='auto-detect MCP clients and wire atex into their configs (or run a local-model RAG validation with --model)')
    ap.add_argument('--atex-dir',default=os.path.expanduser('~/.atex-demo/.atex'),help='where the demo KB lives (default: ~/.atex-demo/.atex)')
    ap.add_argument('--python',default=sys.executable,help='Python interpreter the client should launch (default: current sys.executable)')
    ap.add_argument('--server-name',default='atex',help='MCP server name to register (default: atex)')
    ap.add_argument('--no-consent',action='store_true',help='write configs without [y/N] prompt (CI / scripted use)')
    ap.add_argument('--dry-run',action='store_true',help='do not write any files, just report what would happen')
    ap.add_argument('--client',default=None,help='wire only this client (claude_desktop|claude_code|cline|continue|zed); default: prompt for each detected')
    ap.add_argument('--model',default=None,help='instead of wiring clients, run a local-model RAG validation loop using this ollama model name (e.g. qwen2.5:0.5b-instruct, llama3.2:1b)')
    ap.add_argument('--ollama-url',default='http://localhost:11434',help='ollama server URL (default: http://localhost:11434)')
    ap.add_argument('--walkthrough',action='store_true',help='paced + colored multi-step demo with explanations between each step')
    ap.add_argument('--scenario',default=None,choices=['long-context'],help='run a built-in demonstration scenario (long-context: 5-turn conversation over a fake 15-file project)')
    ap.add_argument('--non-interactive',action='store_true',help='do not pause for keypresses between walkthrough/scenario steps (use a fixed sleep instead)')
    args=ap.parse_args(argv)
    if args.scenario=='long-context':
        from atex.clients.scenarios.long_context import run_long_context
        return run_long_context(Path(args.atex_dir).resolve(),model=args.model,interactive=not args.non_interactive,ollama_url=args.ollama_url)
    if args.walkthrough:
        from atex.clients.walkthrough import run_walkthrough
        return run_walkthrough(Path(args.atex_dir).resolve(),model=args.model,interactive=not args.non_interactive,ollama_url=args.ollama_url)
    if args.model:return _run_model_validation(args)
    atex_dir=Path(args.atex_dir).resolve()
    print(f'[atex demo] target KB: {atex_dir}')
    atex_dir.mkdir(parents=True,exist_ok=True)
    n_seeded=_seed_kb(atex_dir,verbose=True)
    detected=detect_all()
    print('\n[atex demo] MCP clients on this machine:')
    for c in detected:
        installed='installed' if c.installed else 'not detected'
        writable='auto-writable' if c.auto_writable else 'manual config only'
        path_str=str(c.config_path) if c.config_path else '(no path)'
        print(f'  - {c.label:32s} [{installed:13s}] [{writable:18s}] {path_str}')
    print('')
    targets=[c for c in detected if c.installed and c.auto_writable]
    if args.client:
        targets=[c for c in detected if c.name==args.client]
        if not targets:print(f'[atex demo] client "{args.client}" not in detected list',file=sys.stderr);return 2
    if not targets:
        print('[atex demo] no auto-wirable clients detected.')
        print('[atex demo] add this MCP server entry manually in your client:')
        print(f'  command: {args.python}')
        print(f'  args: ["-m","atex.cli","serve","--atex-dir","{atex_dir.as_posix()}"]')
        _print_sample_prompts(args.server_name)
        return 0
    consent=not args.no_consent
    n_wired=0;n_skipped=0
    for c in targets:
        ok,msg=wire_client(c,args.python,atex_dir,server_name=args.server_name,consent=consent,dry_run=args.dry_run)
        print(f'  {msg}')
        if ok:n_wired+=1
        else:n_skipped+=1
    print(f'\n[atex demo] {n_wired} wired, {n_skipped} skipped, {n_seeded} seed entries available')
    if n_wired>0:_print_sample_prompts(args.server_name)
    return 0
if __name__=='__main__':sys.exit(run_demo())
