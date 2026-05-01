"""atex CLI entry point. Subcommands: init, serve, stats, demo, bench."""
import argparse,sys
try:sys.stdout.reconfigure(encoding='utf-8')
except Exception:pass
try:sys.stderr.reconfigure(encoding='utf-8')
except Exception:pass
def _stats(argv=None)->int:
    from atex.kb import KnowledgeBase
    ap=argparse.ArgumentParser(prog='atex stats')
    ap.add_argument('--atex-dir',default='.atex')
    args=ap.parse_args(argv)
    kb=KnowledgeBase(args.atex_dir)
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
    print(f'atex: unknown command "{cmd}". Try: atex --help',file=sys.stderr)
    return 2
if __name__=='__main__':sys.exit(main())
