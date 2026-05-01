"""atex.bench.corpus: a fixed, self-contained corpus of code-doc snippets + ground-truth query→key map."""
DOCS={
    'project::pathlib_read_text':'Path.read_text(encoding=None,errors=None) reads the entire file as a string. The encoding defaults to the locale.',
    'project::pathlib_write_text':'Path.write_text(data,encoding=None,errors=None) writes a string to a file, returning the number of characters written.',
    'project::pathlib_glob':'Path.glob(pattern) yields all matching paths. Use rglob for recursive matching. Patterns support shell-style wildcards.',
    'project::json_loads':'json.loads(s) deserializes a JSON-formatted string into a Python object. Raises json.JSONDecodeError on invalid input.',
    'project::json_dumps':'json.dumps(obj,indent=None,sort_keys=False) serializes a Python object to a JSON-formatted string.',
    'project::subprocess_run':'subprocess.run(args,capture_output=False,text=False,timeout=None,check=False) runs a command and returns a CompletedProcess.',
    'project::http_get':'requests.get(url,params=None,headers=None,timeout=None) sends an HTTP GET request and returns a Response object.',
    'project::regex_findall':'re.findall(pattern,string) returns all non-overlapping matches of the pattern as a list of strings.',
    'project::regex_compile':'re.compile(pattern,flags=0) compiles a pattern into a Pattern object for efficient repeated matching.',
    'project::dict_setdefault':'dict.setdefault(key,default=None) returns the value of the key if present, else inserts default and returns it.',
    'project::list_sort':'list.sort(key=None,reverse=False) sorts the list in place. Use sorted(seq) to return a new sorted list.',
    'project::asyncio_run':'asyncio.run(coro) runs an async coroutine to completion in a new event loop.',
    'project::asyncio_gather':'asyncio.gather(*coros,return_exceptions=False) runs coroutines concurrently and returns their results as a list.',
    'project::os_environ':'os.environ is a mapping of process environment variables. Use os.environ.get(key,default) for safe access.',
    'project::os_path_join':'os.path.join(*parts) joins path components using the platform separator. Use pathlib.Path for new code.',
    'project::tempfile_mkdtemp':'tempfile.mkdtemp(prefix=None) creates a unique temporary directory and returns its path. The caller must clean it up.',
    'project::hashlib_sha256':'hashlib.sha256(data) returns a hash object. Call .hexdigest() for a 64-char hex string.',
    'project::hmac_compare':'hmac.compare_digest(a,b) compares two strings or byte sequences in constant time to prevent timing attacks.',
    'project::dataclass_field':'dataclasses.field(default=MISSING,default_factory=MISSING,init=True) customizes a dataclass field. Use default_factory for mutable defaults.',
    'project::typing_optional':'typing.Optional[T] is equivalent to Union[T,None]. Use it for parameters that may be None.',
}
QUERY_ANSWERS=[
    ('how do I read a file as a string in Python','project::pathlib_read_text'),
    ('write text to file using pathlib','project::pathlib_write_text'),
    ('recursive glob pattern matching','project::pathlib_glob'),
    ('parse JSON string into Python object','project::json_loads'),
    ('serialize dict to JSON','project::json_dumps'),
    ('run a shell command and capture output','project::subprocess_run'),
    ('send an HTTP GET request','project::http_get'),
    ('find all regex matches in a string','project::regex_findall'),
    ('compile a regex pattern for reuse','project::regex_compile'),
    ('get default value if dict key missing','project::dict_setdefault'),
    ('sort a list in place','project::list_sort'),
    ('run an async coroutine','project::asyncio_run'),
    ('run multiple coroutines concurrently','project::asyncio_gather'),
    ('access environment variables','project::os_environ'),
    ('join path components portably','project::os_path_join'),
    ('create a temporary directory','project::tempfile_mkdtemp'),
    ('compute sha256 hash','project::hashlib_sha256'),
    ('constant-time string comparison for security','project::hmac_compare'),
    ('mutable default field for dataclass','project::dataclass_field'),
    ('typing for optional parameter','project::typing_optional'),
]
def build_corpus(kb):
    n=0
    for k,v in DOCS.items():
        kb.add(k,v,meta={'kind':'bench_corpus'},allow_overwrite=True)
        n+=1
    kb.flush()
    return n
