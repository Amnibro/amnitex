/* Windows build support for atex (mingw-w64).
 *
 * Helium emits C for a POSIX host. build.sh compiles that C for Windows with
 * this header forced in first (-include win/compat.h -Iwin/include), so the
 * POSIX calls in the Helium runtime land on Win32:
 *
 * - mmap, munmap, mprotect, madvise: Helium reserves up to 2 GiB of address
 *   space for each array and lets the OS back pages on first use. Windows does
 *   not overcommit, so space is reserved with MEM_RESERVE and a vectored
 *   exception handler commits pages the first time they are touched.
 * - open, read, write: files open in binary mode. A read into reserved memory
 *   is committed first, because ReadFile fails there instead of faulting.
 * - rename replaces an existing file, as POSIX rename does.
 * - system runs commands with Git Bash when it is installed (Claude Code on
 *   Windows needs Git for Windows), and with cmd.exe otherwise. ATEX_SH names
 *   the shell; it is set at start-up when one is found.
 * - HOME, TMPDIR and PWD are filled in from USERPROFILE, TEMP and the current
 *   folder, with forward slashes.
 */
#ifndef ATEX_WIN_COMPAT_H
#define ATEX_WIN_COMPAT_H
#ifdef _WIN32
#define _CRT_RAND_S
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <io.h>
#include <direct.h>
#include <process.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include <pthread.h>
#include <dirent.h>

#define PROT_NONE 0
#define PROT_READ 1
#define PROT_WRITE 2
#define PROT_EXEC 4
#define MAP_SHARED 1
#define MAP_PRIVATE 2
#define MAP_FIXED 0x10
#define MAP_ANONYMOUS 0x20
#define MAP_NORESERVE 0x4000
#define MAP_FAILED ((void *)-1)
#define MADV_DONTNEED 4
#define MADV_REMOVE 9

typedef struct { uintptr_t base, end, lim; } atexw_reg;
static atexw_reg *atexw_regs;
static size_t atexw_nreg, atexw_creg;
static SRWLOCK atexw_lk = SRWLOCK_INIT;

static int atexw_find(uintptr_t a) {
	for (size_t i = 0; i < atexw_nreg; i++) if (a >= atexw_regs[i].base && a < atexw_regs[i].end) return (int)i;
	return -1;
}
/* Commit [a, a + n) where it lies inside a reservation and below its guard. */
static int atexw_commit(uintptr_t a, size_t n) {
	if (!n) return 1;
	AcquireSRWLockShared(&atexw_lk);
	int i = atexw_find(a);
	uintptr_t lo = 0, hi = 0;
	if (i >= 0) { lo = a & ~(uintptr_t)4095; hi = a + n; if (hi > atexw_regs[i].lim) hi = atexw_regs[i].lim; }
	ReleaseSRWLockShared(&atexw_lk);
	if (i < 0 || lo >= hi) return 0;
	return VirtualAlloc((void *)lo, hi - lo, MEM_COMMIT, PAGE_READWRITE) != NULL;
}
static LONG CALLBACK atexw_veh(PEXCEPTION_POINTERS ep) {
	PEXCEPTION_RECORD r = ep->ExceptionRecord;
	if (r->ExceptionCode != EXCEPTION_ACCESS_VIOLATION || r->NumberParameters < 2) return EXCEPTION_CONTINUE_SEARCH;
	uintptr_t a = (uintptr_t)r->ExceptionInformation[1], s = a & ~(uintptr_t)0xFFFF;
	AcquireSRWLockShared(&atexw_lk);
	int i = atexw_find(a), ok = i >= 0 && a < atexw_regs[i].lim;
	uintptr_t lim = ok ? atexw_regs[i].lim : 0;
	ReleaseSRWLockShared(&atexw_lk);
	if (!ok) return EXCEPTION_CONTINUE_SEARCH;
	uintptr_t e = s + 0x10000 < lim ? s + 0x10000 : lim;
	return VirtualAlloc((void *)s, e - s, MEM_COMMIT, PAGE_READWRITE) ? EXCEPTION_CONTINUE_EXECUTION : EXCEPTION_CONTINUE_SEARCH;
}
static void *mmap(void *addr, size_t len, int prot, int flags, int fd, long off) {
	(void)addr; (void)prot; (void)off;
	if (fd != -1 || !(flags & MAP_ANONYMOUS) || !len) { errno = EINVAL; return MAP_FAILED; }
	void *p = VirtualAlloc(NULL, len, MEM_RESERVE, PAGE_NOACCESS);
	if (!p) { errno = ENOMEM; return MAP_FAILED; }
	AcquireSRWLockExclusive(&atexw_lk);
	if (atexw_nreg == atexw_creg) {
		size_t c = atexw_creg ? atexw_creg * 2 : 64;
		atexw_reg *n = (atexw_reg *)realloc(atexw_regs, c * sizeof *n);
		if (!n) { ReleaseSRWLockExclusive(&atexw_lk); VirtualFree(p, 0, MEM_RELEASE); errno = ENOMEM; return MAP_FAILED; }
		atexw_regs = n; atexw_creg = c;
	}
	atexw_regs[atexw_nreg++] = (atexw_reg){ (uintptr_t)p, (uintptr_t)p + len, (uintptr_t)p + len };
	ReleaseSRWLockExclusive(&atexw_lk);
	return p;
}
static int munmap(void *addr, size_t len) {
	(void)len;
	AcquireSRWLockExclusive(&atexw_lk);
	int i = atexw_find((uintptr_t)addr);
	if (i >= 0) atexw_regs[i] = atexw_regs[--atexw_nreg];
	ReleaseSRWLockExclusive(&atexw_lk);
	return i >= 0 && VirtualFree(addr, 0, MEM_RELEASE) ? 0 : -1;
}
static int mprotect(void *addr, size_t len, int prot) {
	uintptr_t a = (uintptr_t)addr;
	if (prot != PROT_NONE) return atexw_commit(a, len) ? 0 : -1;
	AcquireSRWLockExclusive(&atexw_lk);
	int i = atexw_find(a);
	if (i >= 0 && a < atexw_regs[i].lim) atexw_regs[i].lim = a;
	ReleaseSRWLockExclusive(&atexw_lk);
	if (i >= 0) VirtualFree(addr, len, MEM_DECOMMIT);
	return i >= 0 ? 0 : -1;
}
static int madvise(void *addr, size_t len, int advice) {
	(void)advice;
	return VirtualFree(addr, len, MEM_DECOMMIT) ? 0 : -1;
}
static int atexw_urandom(void) {
	int p[2];
	unsigned int r[4];
	for (int i = 0; i < 4; i++) if (rand_s(&r[i])) r[i] = (unsigned int)GetTickCount() ^ (unsigned int)(i * 2654435761u);
	if (_pipe(p, 64, _O_BINARY)) return -1;
	_write(p[1], r, sizeof r);
	_close(p[1]);
	return p[0];
}
static int atexw_open(const char *path, int flags, ...) {
	int mode = 0;
	if (flags & _O_CREAT) { va_list ap; va_start(ap, flags); mode = va_arg(ap, int); va_end(ap); }
	if (!strcmp(path, "/dev/urandom")) return atexw_urandom();
	return _open(path, flags | _O_BINARY | _O_NOINHERIT, mode ? (_S_IREAD | _S_IWRITE) : 0);
}
static int atexw_read(int fd, void *buf, unsigned int n) { atexw_commit((uintptr_t)buf, n); return _read(fd, buf, n); }
static int atexw_write(int fd, const void *buf, unsigned int n) { atexw_commit((uintptr_t)buf, n); return _write(fd, buf, n); }
static int atexw_rename(const char *from, const char *to) {
	for (int i = 0; i < 100; i++) {
		if (MoveFileExA(from, to, MOVEFILE_REPLACE_EXISTING | MOVEFILE_COPY_ALLOWED)) return 0;
		DWORD e = GetLastError();
		if (e != ERROR_ACCESS_DENIED && e != ERROR_SHARING_VIOLATION && e != ERROR_LOCK_VIOLATION) break;
		Sleep(10);
	}
	errno = EACCES;
	return -1;
}
static int atexw_unlink(const char *path) {
	for (int i = 0; i < 50; i++) {
		if (!_unlink(path)) return 0;
		if (errno != EACCES) return -1;
		Sleep(10);
	}
	return -1;
}
static ssize_t atexw_readlink(const char *path, char *buf, size_t n) {
	if (strcmp(path, "/proc/self/exe") || n < 2) { errno = EINVAL; return -1; }
	DWORD k = GetModuleFileNameA(NULL, buf, (DWORD)n);
	if (!k || k >= n) return -1;
	for (DWORD i = 0; i < k; i++) if (buf[i] == '\\') buf[i] = '/';
	return (ssize_t)k;
}
#define _SC_NPROCESSORS_ONLN 84
static long atexw_sysconf(int name) {
	SYSTEM_INFO si;
	GetSystemInfo(&si);
	return name == _SC_NPROCESSORS_ONLN ? (long)si.dwNumberOfProcessors : -1;
}

static int atexw_exists(const char *p) {
	DWORD a = GetFileAttributesA(p);
	return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}
/* Git Bash, never WSL's C:\Windows\System32\bash.exe, which runs Linux. */
static void atexw_find_sh(void) {
	char b[MAX_PATH * 2], *v;
	if ((v = getenv("ATEX_SH")) && *v) return;
	if ((v = getenv("CLAUDE_CODE_GIT_BASH_PATH")) && *v && atexw_exists(v)) { _putenv_s("ATEX_SH", v); return; }
	const char *roots[] = { "ProgramW6432", "ProgramFiles", "LOCALAPPDATA" };
	for (int i = 0; i < 3; i++) {
		if (!(v = getenv(roots[i])) || !*v) continue;
		snprintf(b, sizeof b, i == 2 ? "%s\\Programs\\Git\\bin\\bash.exe" : "%s\\Git\\bin\\bash.exe", v);
		if (atexw_exists(b)) { _putenv_s("ATEX_SH", b); return; }
	}
	char *f;
	DWORD k = SearchPathA(NULL, "git.exe", NULL, (DWORD)sizeof b, b, &f);
	if (k && k < sizeof b && f > b) {
		f[-1] = 0;
		char *s = strrchr(b, '\\');
		if (s && (!_stricmp(s + 1, "cmd") || !_stricmp(s + 1, "bin"))) {
			*s = 0;
			char c[MAX_PATH * 2];
			snprintf(c, sizeof c, "%s\\bin\\bash.exe", b);
			if (atexw_exists(c)) { _putenv_s("ATEX_SH", c); return; }
		}
	}
	k = SearchPathA(NULL, "sh.exe", NULL, (DWORD)sizeof b, b, &f);
	if (k && k < sizeof b) _putenv_s("ATEX_SH", b);
}
/* Run the command with the POSIX shell from a script file, so no quoting is
   lost on the Windows command line; with no shell, fall back to cmd.exe. */
static int atexw_system(const char *cmd) {
	const char *sh = getenv("ATEX_SH");
	if (!cmd) return 1;
	if (!sh || !*sh) return system(cmd);
	static volatile LONG seq;
	char tmp[MAX_PATH], path[MAX_PATH * 2], *line;
	const char *td = getenv("TMPDIR");
	if (!td || !*td) { GetTempPathA((DWORD)sizeof tmp, tmp); td = tmp; }
	snprintf(path, sizeof path, "%s/atex-sh-%lu-%ld.sh", td, (unsigned long)GetCurrentProcessId(), (long)InterlockedIncrement(&seq));
	int fd = _open(path, _O_WRONLY | _O_CREAT | _O_TRUNC | _O_BINARY | _O_NOINHERIT, _S_IREAD | _S_IWRITE);
	if (fd < 0) return -1;
	size_t n = strlen(cmd);
	int ok = _write(fd, cmd, (unsigned int)n) == (int)n && _write(fd, "\n", 1) == 1;
	_close(fd);
	if (!ok) { _unlink(path); return -1; }
	size_t cl = strlen(sh) + strlen(path) + 8;
	if (!(line = (char *)malloc(cl))) { _unlink(path); return -1; }
	snprintf(line, cl, "\"%s\" \"%s\"", sh, path);
	STARTUPINFOA si;
	PROCESS_INFORMATION pi;
	memset(&si, 0, sizeof si);
	si.cb = sizeof si;
	si.dwFlags = STARTF_USESTDHANDLES;
	si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
	si.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
	si.hStdError = GetStdHandle(STD_ERROR_HANDLE);
	fflush(NULL);
	DWORD code = (DWORD)-1;
	if (CreateProcessA(NULL, line, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
		WaitForSingleObject(pi.hProcess, INFINITE);
		if (!GetExitCodeProcess(pi.hProcess, &code)) code = (DWORD)-1;
		CloseHandle(pi.hThread);
		CloseHandle(pi.hProcess);
	}
	free(line);
	_unlink(path);
	return (int)code;
}

static void atexw_slashes(char *s) { for (; *s; s++) if (*s == '\\') *s = '/'; }
static void atexw_env_path(const char *name, const char *from, const char *alt) {
	char b[MAX_PATH * 2];
	const char *v = getenv(name);
	if (!v || !*v) v = getenv(from);
	if ((!v || !*v) && alt) v = getenv(alt);
	if (!v || !*v || strlen(v) >= sizeof b) return;
	strcpy(b, v);
	atexw_slashes(b);
	_putenv_s(name, b);
}
__attribute__((constructor)) static void atexw_init(void) {
	_setmode(0, _O_BINARY);
	_setmode(1, _O_BINARY);
	_setmode(2, _O_BINARY);
	AddVectoredExceptionHandler(1, atexw_veh);
	atexw_env_path("HOME", "USERPROFILE", NULL);
	atexw_env_path("TMPDIR", "TEMP", "TMP");
	char b[MAX_PATH * 2];
	if (_getcwd(b, (int)sizeof b)) { atexw_slashes(b); _putenv_s("PWD", b); }
	atexw_find_sh();
}

/* struct tm has no tm_gmtoff on Windows; localtime_r records it instead. */
static __thread long atexw_gmtoff;
static struct tm *atexw_localtime_r(const time_t *t, struct tm *r) {
	if (localtime_s(r, t)) return NULL;
	struct tm u = *r;
	atexw_gmtoff = (long)(_mkgmtime(&u) - *t);
	return r;
}
#define localtime_r atexw_localtime_r
#define tm_gmtoff tm_isdst * 0 + atexw_gmtoff

#undef mkdir
#define mkdir(p, m) _mkdir(p)
#define open atexw_open
#define read atexw_read
#define write atexw_write
#define rename atexw_rename
#define unlink atexw_unlink
#define readlink atexw_readlink
#define sysconf atexw_sysconf
#define system atexw_system
#endif
#endif
