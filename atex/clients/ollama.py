"""atex.clients.ollama: stdlib-only adapter to a local ollama server (default http://localhost:11434)."""
import json,urllib.request,urllib.error
from typing import Callable,Optional
def check_ollama_available(base_url:str='http://localhost:11434',timeout:float=2.0)->bool:
    try:
        with urllib.request.urlopen(f'{base_url}/api/tags',timeout=timeout) as r:return r.status==200
    except (urllib.error.URLError,urllib.error.HTTPError,ConnectionError,OSError):return False
def list_ollama_models(base_url:str='http://localhost:11434',timeout:float=2.0):
    try:
        with urllib.request.urlopen(f'{base_url}/api/tags',timeout=timeout) as r:
            data=json.loads(r.read())
            return [m.get('name','?') for m in data.get('models',[])]
    except Exception:return []
def make_ollama_chat(model:str,base_url:str='http://localhost:11434',timeout:float=120.0,system:Optional[str]=None,options:Optional[dict]=None)->Callable[[str],str]:
    def chat(prompt:str)->str:
        body={'model':model,'prompt':prompt,'stream':False}
        if system is not None:body['system']=system
        if options is not None:body['options']=options
        req=urllib.request.Request(f'{base_url}/api/generate',data=json.dumps(body).encode('utf-8'),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                payload=json.loads(r.read())
                return payload.get('response','') or f'[ollama:{model}: empty response]'
        except urllib.error.HTTPError as e:
            try:err=json.loads(e.read()).get('error',str(e))
            except Exception:err=str(e)
            return f'[ollama:{model}: HTTP {e.code} {err}]'
        except (urllib.error.URLError,ConnectionError,OSError,TimeoutError) as e:
            return f'[ollama:{model}: connection error {e}]'
    return chat
