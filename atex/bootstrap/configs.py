"""atex.bootstrap.configs: write atex MCP server entry into client config files. Always backup-before-write with [y/N] consent."""
import json,sys,time
from pathlib import Path
from typing import Tuple,Optional,List
from atex.bootstrap.detect import ClientStatus,detect_all
def _server_block(python_exe:str,atex_dir:Path,server_name:str)->dict:
    return {server_name:{'command':python_exe,'args':['-m','atex.cli','serve','--atex-dir',atex_dir.as_posix()]}}
def _backup(p:Path)->Optional[Path]:
    if not p.exists():return None
    ts=int(time.time())
    bk=p.with_suffix(p.suffix+f'.atex-backup-{ts}')
    bk.write_bytes(p.read_bytes())
    return bk
def _confirm(prompt:str,default_no:bool=True)->bool:
    if not sys.stdin.isatty():return False
    suffix='[y/N]' if default_no else '[Y/n]'
    try:resp=input(f'{prompt} {suffix} ').strip().lower()
    except (EOFError,KeyboardInterrupt):print();return False
    if not resp:return not default_no
    return resp in ('y','yes')
def _merge_mcp_servers(existing:dict,new_block:dict,key:str='mcpServers')->dict:
    if key not in existing:existing[key]={}
    if not isinstance(existing[key],dict):existing[key]={}
    existing[key].update(new_block)
    return existing
def _merge_zed_context_servers(existing:dict,server_name:str,python_exe:str,atex_dir:Path)->dict:
    if 'context_servers' not in existing:existing['context_servers']={}
    existing['context_servers'][server_name]={'command':{'path':python_exe,'args':['-m','atex.cli','serve','--atex-dir',atex_dir.as_posix()]}}
    return existing
def wire_client(client:ClientStatus,python_exe:str,atex_dir,server_name:str='atex',consent:bool=True,dry_run:bool=False)->Tuple[bool,str]:
    atex_dir=Path(atex_dir) if not isinstance(atex_dir,Path) else atex_dir
    if not client.auto_writable:return (False,f'{client.label}: auto-write not supported. Add this manually:\n  command: {python_exe}\n  args: ["-m","atex.cli","serve","--atex-dir","{atex_dir.as_posix()}"]')
    if client.config_path is None:return (False,f'{client.label}: config path could not be determined on this OS')
    p=client.config_path
    if consent and not _confirm(f'Write atex MCP entry to {p}?'):return (False,f'{client.label}: skipped (no consent)')
    p.parent.mkdir(parents=True,exist_ok=True)
    existing={} if not p.exists() else (json.loads(p.read_text(encoding='utf-8')) if p.read_text(encoding='utf-8').strip() else {})
    if client.name=='zed':
        merged=_merge_zed_context_servers(existing,server_name,python_exe,atex_dir)
    else:
        block=_server_block(python_exe,atex_dir,server_name)
        merged=_merge_mcp_servers(existing,block)
    if dry_run:return (True,f'[dry-run] would write {client.label} -> {p} with {server_name} entry')
    bk=_backup(p)
    p.write_text(json.dumps(merged,indent=2),encoding='utf-8')
    bk_msg=f' (backed up to {bk.name})' if bk else ' (no prior config)'
    return (True,f'{client.label}: wrote {server_name} entry to {p}{bk_msg}. {client.notes}')
def wire_all(python_exe:str,atex_dir,server_name:str='atex',consent:bool=True,dry_run:bool=False)->List[Tuple[ClientStatus,bool,str]]:
    atex_dir=Path(atex_dir) if not isinstance(atex_dir,Path) else atex_dir
    results=[]
    for c in detect_all():
        if not c.auto_writable:results.append((c,False,c.notes));continue
        if c.config_path is None:results.append((c,False,'config path unknown on this OS'));continue
        ok,msg=wire_client(c,python_exe,atex_dir,server_name=server_name,consent=consent,dry_run=dry_run)
        results.append((c,ok,msg))
    return results
