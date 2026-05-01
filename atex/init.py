"""atex.init: walk a project root and ingest source files into a local .atex/ knowledge base."""
import argparse,json,sys,time
from pathlib import Path
from atex.kb import KnowledgeBase
_DEFAULT_EXTS=('.py','.js','.ts','.tsx','.jsx','.md','.html','.css','.json','.yml','.yaml','.toml','.txt','.sh','.go','.rs','.java','.cpp','.c','.h','.hpp','.kt','.rb','.php','.lua','.swift')
_DEFAULT_EXCLUDE=('node_modules','.git','__pycache__','.venv','venv','env','dist','build','.next','target','.pytest_cache','.mypy_cache','.atex','bakes','downloaded_models','logs','backups','archive')
_DEFAULT_GITIGNORE='\n# atex (local knowledge base) — regeneratable artifacts\n.atex/pages/\n.atex/index.json\n# but keep these (committed for team sharing):\n!.atex/manual/\n!.atex/config.json\n'
def _walk(root,include_ext,exclude_dir,max_size):
    skip_dirs=set(exclude_dir)
    n_total=0;n_kept=0;n_skipped_size=0;n_skipped_decode=0
    for p in root.rglob('*'):
        if not p.is_file():continue
        if any(part in skip_dirs for part in p.parts):continue
        if p.suffix.lower() not in include_ext:continue
        n_total+=1
        try:
            if p.stat().st_size>max_size:n_skipped_size+=1;continue
            content=p.read_text(encoding='utf-8',errors='strict')
        except (UnicodeDecodeError,OSError):n_skipped_decode+=1;continue
        n_kept+=1
        yield p.relative_to(root).as_posix(),content
    print(f'  walked {n_total} candidate files; kept {n_kept}, skipped_size {n_skipped_size}, skipped_decode {n_skipped_decode}')
def run(argv=None)->int:
    ap=argparse.ArgumentParser(prog='atex init',description='initialize local atex KB in current project')
    ap.add_argument('--root',default='.',help='project root (default: current dir)')
    ap.add_argument('--atex-dir',default='.atex',help='where to put the KB (default: .atex)')
    ap.add_argument('--include-ext',nargs='+',default=list(_DEFAULT_EXTS))
    ap.add_argument('--exclude-dir',nargs='+',default=list(_DEFAULT_EXCLUDE))
    ap.add_argument('--max-size-bytes',type=int,default=32000)
    ap.add_argument('--no-ingest',action='store_true',help='create .atex skeleton without ingesting files')
    ap.add_argument('--reingest',action='store_true',help='nuke and rebuild (removes .atex/pages and .atex/index.json)')
    ap.add_argument('--no-gitignore',action='store_true',help='skip auto-appending .atex rules to .gitignore')
    args=ap.parse_args(argv)
    root=Path(args.root).resolve()
    atex=root/args.atex_dir if not Path(args.atex_dir).is_absolute() else Path(args.atex_dir)
    if args.reingest and atex.exists():
        import shutil
        shutil.rmtree(atex/'pages',ignore_errors=True)
        (atex/'index.json').unlink(missing_ok=True)
        print(f'[atex init] nuked {atex}/pages and {atex}/index.json (manual/ and config.json kept)')
    atex.mkdir(parents=True,exist_ok=True)
    (atex/'manual').mkdir(exist_ok=True)
    cfg_path=atex/'config.json'
    cfg={'project_root':str(root),'include_ext':sorted(args.include_ext),'exclude_dir':sorted(args.exclude_dir),'max_size_bytes':args.max_size_bytes,'created':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    if not cfg_path.exists():cfg_path.write_text(json.dumps(cfg,indent=2),encoding='utf-8');print(f'[atex init] wrote {cfg_path}')
    if not args.no_gitignore:
        gi=root/'.gitignore'
        if gi.exists():
            existing=gi.read_text(encoding='utf-8',errors='replace')
            if '.atex/pages/' not in existing:gi.write_text(existing.rstrip()+_DEFAULT_GITIGNORE,encoding='utf-8');print(f'[atex init] appended atex rules to {gi}')
        else:gi.write_text(_DEFAULT_GITIGNORE.lstrip(),encoding='utf-8');print(f'[atex init] created {gi}')
    print(f'[atex init] KB at {atex}')
    if args.no_ingest:print('[atex init] --no-ingest set; skeleton ready');return 0
    print(f'[atex init] ingesting source files from {root}')
    kb=KnowledgeBase(atex)
    n_appended=0
    for rel,content in _walk(root,set(args.include_ext),args.exclude_dir,args.max_size_bytes):
        key=f'project::{rel}'
        kb.add(key,content,meta={'rel':rel,'kind':'source'},allow_overwrite=True)
        n_appended+=1
    kb.flush()
    s=kb.stats()
    print(f'\n[atex init] DONE: ingested {n_appended} files')
    print(f'  KB stats: {s["n_entries"]} entries, {s["n_pages"]} pages, {s["used_bytes"]/1e6:.2f} MB on disk')
    print('\nNext steps:')
    print(f'  1. Run the MCP server:  atex serve --atex-dir {atex}')
    print('  2. Configure your AI client (Claude Code / Cursor / Cline / Continue) to use the MCP server.')
    print(f'  3. Or just:  atex demo  (auto-detects + wires up your client)')
    print('  4. Re-run atex init periodically (or on file-watch) to refresh the KB.')
    return 0
if __name__=='__main__':sys.exit(run())
