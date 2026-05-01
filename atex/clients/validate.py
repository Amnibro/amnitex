"""atex.clients.validate: 3-step end-to-end validation loop — search miss, remember, recall, search hit. Reports metrics for paper / launch GIF."""
import time
from dataclasses import dataclass,field
from typing import Callable,Dict,List
from atex.clients.rag import AtexRagClient,ChatFn
@dataclass
class ValidationResult:
    model_label:str
    n_steps:int=0
    n_pass:int=0
    n_fail:int=0
    steps:List[Dict]=field(default_factory=list)
    total_wall_s:float=0.0
    @property
    def passed(self)->bool:return self.n_fail==0 and self.n_steps>0
    def summary(self)->str:
        lines=[f'[atex-validate] model={self.model_label} steps={self.n_steps} pass={self.n_pass} fail={self.n_fail} wall={self.total_wall_s:.2f}s']
        for s in self.steps:lines.append(f"  {'✓' if s['ok'] else '✗'} {s['name']}: {s['detail']}")
        return '\n'.join(lines)
def run_validation_loop(client:AtexRagClient,model_label:str='unknown',probe_key:str='atex-validation-probe',probe_fact:str='The atex validation loop ran on '+time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())+'. The validation cookie value is azure-marmot-7421.')->ValidationResult:
    res=ValidationResult(model_label=model_label)
    t0=time.time()
    full_key=f'manual::{probe_key}'
    if full_key in client.kb:
        client.kb.add(full_key,'(cleared)',meta={'kind':'cleared'},allow_overwrite=True)
    pre=client.recall(probe_key)
    pre_ok=pre is None or pre=='(cleared)'
    res.steps.append({'name':'pre-clear','ok':pre_ok,'detail':f'probe key cleared: {pre_ok}'})
    res.n_steps+=1;res.n_pass+=int(pre_ok);res.n_fail+=int(not pre_ok)
    full_key=client.remember(probe_key,probe_fact)
    rem_ok=full_key==f'manual::{probe_key}' and client.recall(probe_key)==probe_fact
    res.steps.append({'name':'remember-then-recall','ok':rem_ok,'detail':f'wrote {len(probe_fact)} bytes; round-trip exact-match={rem_ok}'})
    res.n_steps+=1;res.n_pass+=int(rem_ok);res.n_fail+=int(not rem_ok)
    rec=client.ask(f'What is the validation cookie value? Quote it exactly.')
    cookie_in_top=any('validation' in (k or '').lower() for k in rec['top_keys'])
    res.steps.append({'name':'rag-search-finds-fact','ok':cookie_in_top,'detail':f"top_keys={rec['top_keys']} (retrieval={rec['retrieval_ms']}ms)"})
    res.n_steps+=1;res.n_pass+=int(cookie_in_top);res.n_fail+=int(not cookie_in_top)
    cookie_in_answer='azure-marmot-7421' in (rec['answer'] or '').lower()
    res.steps.append({'name':'rag-answer-quotes-fact','ok':cookie_in_answer,'detail':f"answer={(rec['answer'] or '')[:120]!r} (chat={rec['chat_ms']}ms)"})
    res.n_steps+=1;res.n_pass+=int(cookie_in_answer);res.n_fail+=int(not cookie_in_answer)
    res.total_wall_s=round(time.time()-t0,2)
    return res
def make_synthetic_chat(answer_template:str='Based on the references, the answer is: {hint}')->ChatFn:
    def chat(prompt:str)->str:
        hint=''
        if 'azure-marmot-7421' in prompt.lower():hint='azure-marmot-7421'
        return answer_template.format(hint=hint or '[no hint]')
    return chat
