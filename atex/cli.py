"""atex CLI entry point. Subcommands: init, serve, stats, demo, bench."""
import argparse,sys
try:sys.stdout.reconfigure(encoding='utf-8')
except Exception:pass
try:sys.stderr.reconfigure(encoding='utf-8')
except Exception:pass
def _stats(argv=None)->int:
    from atex.kb import KnowledgeBase,KnowledgeBaseError
    ap=argparse.ArgumentParser(prog='atex stats')
    ap.add_argument('--atex-dir',default='.atex')
    args=ap.parse_args(argv)
    try:
        kb=KnowledgeBase(args.atex_dir)
    except KnowledgeBaseError as exc:
        print(f'[atex stats] {exc}',file=sys.stderr)
        return 2
    s=kb.stats()
    print(f'entries: {s["n_entries"]}')
    print(f'pages: {s["n_pages"]}')
    print(f'used: {s["used_bytes"]/1e6:.2f} MB')
    print(f'capacity: {s["capacity_bytes"]/1e6:.2f} MB')
    print(f'utilization: {s["utilization"]*100:.1f}%')
    print(f'page geometry: {s["page_w"]}x{s["page_h"]} ({s["page_bytes"]/1024:.0f} KB per page)')
    return 0
def _demo(argv=None)->int:
    from atex.bootstrap.demo import run_demo
    return run_demo(argv)
def _bench(argv=None)->int:
    from atex.bench.run import run_main
    return run_main(argv)
def main(argv=None)->int:
    argv=sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ('-h','--help'):
        print('usage: atex <command> [args...]')
        print('')
        print('commands:')
        print('  init     initialize a local atex KB in the current project')
        print('  serve    run the MCP server against an existing .atex/ dir')
        print('  stats    print KB stats (entries, pages, disk usage)')
        print('  demo     auto-detect and wire up an MCP-capable AI client (planned)')
        print('  bench    run head-to-head benchmarks vs other memory layers (planned)')
        print('  hook     save a transcript or print the restored state card')
        print('  install  wire Cursor and Grok on this machine')
        print('')
        print('try: atex init --help')
        return 0
    cmd=argv[0]
    rest=argv[1:]
    if cmd=='init':
        from atex.init import run as init_run
        return init_run(rest)
    if cmd=='serve':
        from atex.serve import run as serve_run
        return serve_run(rest)
    if cmd=='stats':return _stats(rest)
    if cmd=='demo':return _demo(rest)
    if cmd=='bench':return _bench(rest)
    if cmd=='hook':return _hook(rest)
    if cmd=='install':return _install(rest)
    print(f'atex: unknown command "{cmd}". Try: atex --help',file=sys.stderr)
    return 2
def _hook(argv)->int:
    ap=argparse.ArgumentParser(prog='atex hook')
    ap.add_argument('kind',nargs='?',default='stop')
    ap.add_argument('--atex-dir',default=None)
    args=ap.parse_args(argv)
    from atex.kb import KnowledgeBaseError
    from atex.session import cwd_from,default_atex_dir,hook_output,ingest_transcript,load_transcript_path,open_kb,project_slug,read_stdin_payload,transcript_path_from
    payload=read_stdin_payload(sys.stdin.read())
    kind=args.kind.replace('_','-')
    source=str(payload.get('source') or '')
    if kind in ('start','session-start','sessionstart') and source=='startup':
        return 0
    atex_dir=args.atex_dir or default_atex_dir()
    try:
        kb=open_kb(atex_dir)
    except KnowledgeBaseError as exc:
        print(f'[atex hook] {exc}',file=sys.stderr)
        return 2
    cwd=cwd_from(payload)
    card=''
    if kind in ('stop','pre-compact','precompact'):
        path=transcript_path_from(payload)
        if path:
            card=ingest_transcript(kb,load_transcript_path(path),cwd)
        else:
            card=kb.lookup(f'conv::{project_slug(cwd)}::latest_state') or ''
    elif kind in ('start','session-start','sessionstart'):
        card=kb.lookup(f'conv::{project_slug(cwd)}::latest_state') or ''
    else:
        print(f'[atex hook] unknown kind "{args.kind}"',file=sys.stderr)
        return 2
    out=hook_output(kind,card or '')
    if out:
        sys.stdout.write(out)
    return 0
def _install(argv)->int:
    from atex.wire import install
    ap=argparse.ArgumentParser(prog='atex install')
    ap.add_argument('--home',default=None)
    ap.add_argument('--atex-dir',default=None)
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(argv)
    notes=install(home=args.home,atex_dir=args.atex_dir,dry_run=args.dry_run)
    for note in notes:
        print(note)
    return 0
if __name__=='__main__':sys.exit(main())
