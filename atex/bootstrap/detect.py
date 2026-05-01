"""atex.bootstrap.detect: locate config files for MCP-capable AI clients."""
import os,sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional,List
@dataclass
class ClientStatus:
    name:str
    label:str
    config_path:Optional[Path]
    auto_writable:bool
    notes:str=''
    @property
    def installed(self)->bool:return self.config_path is not None and self.config_path.exists()
def _home()->Path:return Path(os.path.expanduser('~'))
def _appdata()->Optional[Path]:
    if sys.platform=='win32':
        v=os.environ.get('APPDATA')
        return Path(v) if v else None
    return None
def _claude_desktop()->ClientStatus:
    if sys.platform=='darwin':
        p=_home()/'Library'/'Application Support'/'Claude'/'claude_desktop_config.json'
    elif sys.platform=='win32':
        ad=_appdata()
        p=(ad/'Claude'/'claude_desktop_config.json') if ad else None
    else:
        p=_home()/'.config'/'Claude'/'claude_desktop_config.json'
    return ClientStatus(name='claude_desktop',label='Claude Desktop',config_path=p,auto_writable=True,notes='Restart Claude Desktop after wiring.')
def _claude_code()->ClientStatus:
    p=_home()/'.claude.json'
    return ClientStatus(name='claude_code',label='Claude Code (Anthropic CLI)',config_path=p,auto_writable=True,notes='Restart claude after wiring.')
def _cursor()->ClientStatus:
    return ClientStatus(name='cursor',label='Cursor',config_path=None,auto_writable=False,notes='Add via Settings > MCP > Add Custom Server (config not auto-writable yet).')
def _cline()->ClientStatus:
    if sys.platform=='win32':
        ad=_appdata()
        p=(ad/'Code'/'User'/'globalStorage'/'saoudrizwan.claude-dev'/'settings'/'cline_mcp_settings.json') if ad else None
    elif sys.platform=='darwin':
        p=_home()/'Library'/'Application Support'/'Code'/'User'/'globalStorage'/'saoudrizwan.claude-dev'/'settings'/'cline_mcp_settings.json'
    else:
        p=_home()/'.config'/'Code'/'User'/'globalStorage'/'saoudrizwan.claude-dev'/'settings'/'cline_mcp_settings.json'
    return ClientStatus(name='cline',label='Cline (VS Code extension)',config_path=p,auto_writable=True,notes='Reload VS Code after wiring.')
def _continue_dev()->ClientStatus:
    p=_home()/'.continue'/'config.json'
    return ClientStatus(name='continue',label='Continue (VS Code / JetBrains)',config_path=p,auto_writable=True,notes='Reload Continue after wiring.')
def _zed()->ClientStatus:
    if sys.platform=='darwin':
        p=_home()/'.config'/'zed'/'settings.json'
    elif sys.platform=='win32':
        ad=_appdata()
        p=(ad/'Zed'/'settings.json') if ad else None
    else:
        p=_home()/'.config'/'zed'/'settings.json'
    return ClientStatus(name='zed',label='Zed',config_path=p,auto_writable=True,notes='Restart Zed after wiring.')
def detect_all()->List[ClientStatus]:
    return [_claude_desktop(),_claude_code(),_cursor(),_cline(),_continue_dev(),_zed()]
