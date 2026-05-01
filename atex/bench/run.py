"""atex.bench.run: head-to-head benchmark for atex (and optionally mem0 / basic-memory if installed)."""
import argparse,json,shutil,sys,tempfile,time
from dataclasses import dataclass,field,asdict
from pathlib import Path
from typing import Dict,List,Optional
from atex.kb import KnowledgeBase
from atex.retriever import KBRetriever
from atex.bench.corpus import build_corpus,QUERY_ANSWERS,DOCS
@dataclass
class BenchResult:
    name:str
    ingest_n:int=0
    ingest_wall_s:float=0.0
    ingest_throughput_entries_per_s:float=0.0
    recall_at_1:float=0.0
    recall_at_3:float=0.0
    recall_at_5:float=0.0
    avg_query_ms:float=0.0
    p50_query_ms:float=0.0
    p99_query_ms:float=0.0
    cold_start_ms:float=0.0
    n_queries:int=0
    errors:List[str]=field(default_factory=list)
def _percentile(values:List[float],pct:float)->float:
    if not values:return 0.0
    s=sorted(values);idx=min(int(pct/100.0*len(s)),len(s)-1);return s[idx]
def run_atex_bench(verbose:bool=True)->BenchResult:
    res=BenchResult(name='atex')
    tmp=Path(tempfile.mkdtemp(prefix='atex_bench_'))
    try:
        cold_t0=time.time()
        kb=KnowledgeBase(tmp/'kb')
        retr=KBRetriever.__new__(KBRetriever);retr.kb=kb
        cold_ms=(time.time()-cold_t0)*1000
        res.cold_start_ms=round(cold_ms,2)
        ing_t0=time.time()
        n=build_corpus(kb)
        ing_wall=time.time()-ing_t0
        res.ingest_n=n;res.ingest_wall_s=round(ing_wall,4)
        res.ingest_throughput_entries_per_s=round(n/ing_wall if ing_wall>0 else 0,1)
        if verbose:print(f'  [atex] ingest: {n} entries in {ing_wall*1000:.1f}ms ({res.ingest_throughput_entries_per_s} entries/s)')
        hits_at_1=hits_at_3=hits_at_5=0;query_times=[]
        for q,expected_key in QUERY_ANSWERS:
            qt0=time.time()
            results=retr.retrieve(q,k=5,max_chars_per=200)
            qt=(time.time()-qt0)*1000
            query_times.append(qt)
            keys=[r[0] for r in results]
            if keys and keys[0]==expected_key:hits_at_1+=1
            if expected_key in keys[:3]:hits_at_3+=1
            if expected_key in keys[:5]:hits_at_5+=1
        res.n_queries=len(QUERY_ANSWERS)
        res.recall_at_1=round(hits_at_1/res.n_queries,4) if res.n_queries else 0.0
        res.recall_at_3=round(hits_at_3/res.n_queries,4) if res.n_queries else 0.0
        res.recall_at_5=round(hits_at_5/res.n_queries,4) if res.n_queries else 0.0
        res.avg_query_ms=round(sum(query_times)/len(query_times),3) if query_times else 0.0
        res.p50_query_ms=round(_percentile(query_times,50),3)
        res.p99_query_ms=round(_percentile(query_times,99),3)
        if verbose:print(f'  [atex] recall@1={res.recall_at_1:.0%} recall@3={res.recall_at_3:.0%} recall@5={res.recall_at_5:.0%} avg_query={res.avg_query_ms}ms p99={res.p99_query_ms}ms')
    except Exception as e:res.errors.append(f'{type(e).__name__}: {e}')
    finally:shutil.rmtree(tmp,ignore_errors=True)
    return res
def run_baseline_substring()->BenchResult:
    res=BenchResult(name='naive-substring-scan')
    ing_t0=time.time()
    docs=dict(DOCS)
    res.ingest_wall_s=round(time.time()-ing_t0,6);res.ingest_n=len(docs)
    res.ingest_throughput_entries_per_s=round(res.ingest_n/res.ingest_wall_s if res.ingest_wall_s>0 else 1e9,1)
    hits_at_1=hits_at_3=hits_at_5=0;qt=[]
    for q,expected_key in QUERY_ANSWERS:
        t0=time.time()
        ql=q.lower()
        scored=[]
        for k,v in docs.items():
            score=sum(1 for tok in ql.split() if len(tok)>2 and (tok in k.lower() or tok in v.lower()))
            if score>0:scored.append((score,k))
        scored.sort(reverse=True)
        keys=[k for _,k in scored[:5]]
        qt.append((time.time()-t0)*1000)
        if keys and keys[0]==expected_key:hits_at_1+=1
        if expected_key in keys[:3]:hits_at_3+=1
        if expected_key in keys[:5]:hits_at_5+=1
    res.n_queries=len(QUERY_ANSWERS)
    res.recall_at_1=round(hits_at_1/res.n_queries,4)
    res.recall_at_3=round(hits_at_3/res.n_queries,4)
    res.recall_at_5=round(hits_at_5/res.n_queries,4)
    res.avg_query_ms=round(sum(qt)/len(qt),3) if qt else 0.0
    res.p50_query_ms=round(_percentile(qt,50),3)
    res.p99_query_ms=round(_percentile(qt,99),3)
    return res
def format_results_md(results:List[BenchResult])->str:
    lines=['| backend | ingest_n | ingest_ms | throughput (entries/s) | recall@1 | recall@3 | recall@5 | avg query (ms) | p99 (ms) | cold-start (ms) |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results:
        lines.append(f"| {r.name} | {r.ingest_n} | {r.ingest_wall_s*1000:.1f} | {r.ingest_throughput_entries_per_s:.0f} | {r.recall_at_1:.0%} | {r.recall_at_3:.0%} | {r.recall_at_5:.0%} | {r.avg_query_ms} | {r.p99_query_ms} | {r.cold_start_ms} |")
    return '\n'.join(lines)
def run_main(argv=None)->int:
    ap=argparse.ArgumentParser(prog='atex bench',description='head-to-head benchmark vs other memory layers')
    ap.add_argument('--out',default=None,help='write JSON results to this path')
    ap.add_argument('--md',default=None,help='write markdown table to this path')
    ap.add_argument('--quiet',action='store_true')
    args=ap.parse_args(argv)
    print('[atex bench] running atex backend...')
    a=run_atex_bench(verbose=not args.quiet)
    print('\n[atex bench] running naive substring-scan baseline...')
    b=run_baseline_substring()
    print('')
    md=format_results_md([a,b])
    print(md)
    if args.out:Path(args.out).write_text(json.dumps([asdict(a),asdict(b)],indent=2),encoding='utf-8');print(f'\n[atex bench] JSON written to {args.out}')
    if args.md:Path(args.md).write_text(md+'\n',encoding='utf-8');print(f'[atex bench] markdown written to {args.md}')
    return 0
if __name__=='__main__':sys.exit(run_main())
