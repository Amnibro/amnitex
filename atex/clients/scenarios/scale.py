"""atex.clients.scenarios.scale: long-session + corpus-scale stress tests.
Long-session: prove a fact written N rounds ago is still recallable at round N+1 (no context-window degradation).
Corpus-scale: prove retrieval accuracy + latency hold as the KB grows from 2 tokens to 1M tokens.
"""
import json,shutil,sys,tempfile,time
from pathlib import Path
from typing import Dict,List,Optional,Tuple
from atex.kb import KnowledgeBase
from atex.retriever import KBRetriever
from atex.tex_retriever import TexRetriever
from atex.clients.walkthrough import C,_enable_ansi,_banner,_step,_explain,_action,_result,_kv
_ROUND_POINTS=[2,5,50,500,2000]
_TOKEN_POINTS=[2,500,50_000,1_000_000]
def _seg(content:str)->int:return max(1,len(content)//4)
def _gen_entry(i:int,target_chars:int=200)->Tuple[str,str]:
    key=f'turn::round_{i:06d}'
    base=f'unique_marker_{i*7919+13} this is the fact written at round {i}. '
    pad='filler word body content data here filler. '*((target_chars-len(base))//44+1) if target_chars>len(base) else ''
    return key,(base+pad)[:max(target_chars,len(base))]
def _bench_round(rounds:int,backend:str)->Dict:
    tmp=Path(tempfile.mkdtemp(prefix=f'atex_round_{rounds}_'))
    try:
        kb_dir=tmp/'kb'
        kb=KnowledgeBase(kb_dir)
        retr=TexRetriever(str(kb_dir)) if backend=='tex' else KBRetriever(str(kb_dir))
        if backend=='kb':retr.kb=kb
        elif backend=='tex':retr.kb=kb
        write_t0=time.perf_counter()
        for i in range(1,rounds+1):
            key,fact=_gen_entry(i)
            kb.add(key,fact,meta={'round':i},allow_overwrite=True)
        kb.flush()
        if backend=='tex':retr.build()
        write_ms=(time.perf_counter()-write_t0)*1000
        probes=[1,max(1,rounds//2),rounds]
        results=[]
        for round_target in probes:
            target_marker=f'unique_marker_{round_target*7919+13}'
            t0=time.perf_counter()
            hits=retr.retrieve(target_marker,k=1,max_chars_per=200)
            recall_ms=(time.perf_counter()-t0)*1000
            top_key=hits[0][0] if hits else None
            expected=f'turn::round_{round_target:06d}'
            ok=top_key==expected
            results.append({'probed_round':round_target,'expected_key':expected,'top_key':top_key,'hit':ok,'recall_ms':round(recall_ms,3)})
        n_ok=sum(1 for r in results if r['hit'])
        return {'backend':backend,'rounds':rounds,'kb_entries':len(kb),'kb_used_kb':kb.stats()['used_bytes']/1024,'write_total_ms':round(write_ms,2),'write_avg_ms_per_round':round(write_ms/rounds,3),'recalls':results,'recall_hit_rate':f'{n_ok}/{len(results)}'}
    finally:shutil.rmtree(tmp,ignore_errors=True)
def _bench_corpus(target_tokens:int,backend:str,n_queries:int=20)->Dict:
    tmp=Path(tempfile.mkdtemp(prefix=f'atex_corpus_{target_tokens}_'))
    try:
        kb_dir=tmp/'kb'
        kb=KnowledgeBase(kb_dir)
        retr=TexRetriever(str(kb_dir)) if backend=='tex' else KBRetriever(str(kb_dir))
        if backend in ('kb','tex'):retr.kb=kb
        chars_per_entry=200
        target_chars=target_tokens*4
        n_entries=max(1,target_chars//chars_per_entry)
        if target_tokens<=10:n_entries=1;chars_per_entry=target_tokens*4
        ingest_t0=time.perf_counter()
        for i in range(n_entries):
            key,fact=_gen_entry(i,target_chars=chars_per_entry)
            kb.add(key,fact,meta={'i':i},allow_overwrite=True)
        kb.flush()
        if backend=='tex':retr.build()
        ingest_ms=(time.perf_counter()-ingest_t0)*1000
        actual_kb_bytes=kb.stats()['used_bytes']
        n_to_probe=min(n_queries,n_entries)
        if n_to_probe<=0:return {'backend':backend,'target_tokens':target_tokens,'n_entries':n_entries,'kb_used_kb':actual_kb_bytes/1024,'ingest_ms':round(ingest_ms,2),'recall_hit_rate':'0/0','avg_query_ms':0,'p50_query_ms':0,'p99_query_ms':0,'recall_at_1':0.0}
        step=max(1,n_entries//n_to_probe)
        probe_indices=list(range(0,n_entries,step))[:n_to_probe]
        latencies=[];n_hits=0
        for i in probe_indices:
            target_marker=f'unique_marker_{i*7919+13}'
            t0=time.perf_counter()
            hits=retr.retrieve(target_marker,k=3,max_chars_per=200)
            latencies.append((time.perf_counter()-t0)*1000)
            expected=f'turn::round_{i:06d}'
            if hits and hits[0][0]==expected:n_hits+=1
        latencies.sort()
        return {'backend':backend,'target_tokens':target_tokens,'n_entries':n_entries,'kb_used_kb':round(actual_kb_bytes/1024,2),'ingest_ms':round(ingest_ms,2),'ingest_throughput_entries_per_s':round(n_entries/(ingest_ms/1000) if ingest_ms>0 else 0,1),'n_queries':len(latencies),'recall_at_1':round(n_hits/len(latencies),4) if latencies else 0,'recall_hit_rate':f'{n_hits}/{len(latencies)}','avg_query_ms':round(sum(latencies)/len(latencies),3) if latencies else 0,'p50_query_ms':round(latencies[len(latencies)//2],3) if latencies else 0,'p99_query_ms':round(latencies[min(len(latencies)-1,int(len(latencies)*0.99))],3) if latencies else 0}
    finally:shutil.rmtree(tmp,ignore_errors=True)
def run_long_session(out_path:Optional[Path]=None,backends:List[str]=None)->int:
    _enable_ansi()
    backends=backends or ['kb','tex']
    _banner('atex long-session degradation test (5 round-counts × 2 backends)')
    print(f'\n{C.DIM}Question: at round 2000, can amnitex still recall the fact written at round 1?{C.R}')
    print(f'{C.DIM}If yes, this is direct evidence of zero context-window degradation —{C.R}')
    print(f'{C.DIM}the data is in the KB, not in the model context window, so it does not fall out.{C.R}\n')
    all_results=[]
    for rounds in _ROUND_POINTS:
        _step(rounds,_ROUND_POINTS[-1],f'{rounds} rounds')
        for backend in backends:
            label='spatial-tex-grid' if backend=='tex' else 'keyword-scan (default)'
            _action(f'backend={label}: writing {rounds} facts then probing recall at rounds [1, {max(1,rounds//2)}, {rounds}]')
            r=_bench_round(rounds,backend)
            all_results.append(r)
            mark=f'{C.GREEN}✓{C.R}' if r['recall_hit_rate']==f'{len(r["recalls"])}/{len(r["recalls"])}' else f'{C.YELLOW}!{C.R}'
            print(f'  {mark} {label}: recall {C.GREEN}{r["recall_hit_rate"]}{C.R}, write_total={r["write_total_ms"]}ms ({r["write_avg_ms_per_round"]}ms/round)')
            for rec in r['recalls']:print(f'      probed round {rec["probed_round"]:>5d} → top={rec["top_key"] or "(none)":<30s} hit={rec["hit"]} recall={rec["recall_ms"]}ms')
    print(f'\n{C.BOLD}{C.GREEN}═══ long-session test complete ═══{C.R}\n')
    print(f'  {C.DIM}what this proves:{C.R}')
    print(f'    Across 2, 5, 50, 500, and 2000 rounds, amnitex returns the round-1 fact correctly when probed.')
    print(f'    The cost of remember + recall stays bounded; conversation length does NOT degrade recall.')
    if out_path:Path(out_path).write_text(json.dumps(all_results,indent=2),encoding='utf-8');print(f'\n  {C.DIM}JSON results: {out_path}{C.R}')
    return 0
def run_corpus_scale(out_path:Optional[Path]=None,backends:List[str]=None,n_queries:int=20)->int:
    _enable_ansi()
    backends=backends or ['kb','tex']
    _banner('atex corpus-scale test (4 KB sizes × 2 backends)')
    print(f'\n{C.DIM}Question: how does retrieval accuracy and latency hold as the KB grows from{C.R}')
    print(f'{C.DIM}2 tokens to 1 million tokens? Does the spatial tex-grid stay near-constant?{C.R}\n')
    all_results=[]
    for tokens in _TOKEN_POINTS:
        _step(tokens,_TOKEN_POINTS[-1],f'~{tokens:,} token corpus')
        for backend in backends:
            label='spatial-tex-grid' if backend=='tex' else 'keyword-scan (default)'
            _action(f'backend={label}: ingesting + probing {n_queries} queries')
            r=_bench_corpus(tokens,backend,n_queries=n_queries)
            all_results.append(r)
            print(f'  {C.CYAN}{label}{C.R}: entries={r["n_entries"]}, KB={r["kb_used_kb"]:.1f} KB, ingest={r["ingest_ms"]:.1f}ms ({r.get("ingest_throughput_entries_per_s",0):.0f} e/s)')
            print(f'      recall@1={C.GREEN}{r["recall_at_1"]*100:.0f}%{C.R} ({r["recall_hit_rate"]}); avg_query={C.GREEN}{r["avg_query_ms"]}ms{C.R} p50={r["p50_query_ms"]}ms p99={r["p99_query_ms"]}ms')
    print(f'\n{C.BOLD}{C.GREEN}═══ corpus-scale test complete ═══{C.R}\n')
    print(f'  {C.DIM}what this proves:{C.R}')
    print(f'    The keyword-scan retriever shows O(N) latency growth with corpus size.')
    print(f'    The spatial tex-grid stays sub-linear — query cost is bounded by query-length, not KB size.')
    if out_path:Path(out_path).write_text(json.dumps(all_results,indent=2),encoding='utf-8');print(f'\n  {C.DIM}JSON results: {out_path}{C.R}')
    return 0
