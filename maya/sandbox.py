"""Run untrusted Python (model-written code) in a limited subprocess.

Linux only for the limits (the engine runs in the maya-engine container); on a
host without `resource` the code still runs isolated in a temp dir, just
without rlimits.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile

try:
    import resource
except ImportError:
    resource = None

NOBODY = 65534
MEM_BYTES = 1 << 30
FILE_BYTES = 8 << 20
NPROC = 8
NOFILE = 64
OUT_CHARS = 20000


def _limits(cpu_s):
    def apply():
        os.setsid()
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_BYTES, FILE_BYTES))
        resource.setrlimit(resource.RLIMIT_NOFILE, (NOFILE, NOFILE))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # The container runs as root, which RLIMIT_NPROC does not bind and which
        # could write anywhere in the mounted repo; drop to nobody first.
        if os.getuid() == 0:
            os.setgroups([])
            os.setgid(NOBODY)
            os.setuid(NOBODY)
        resource.setrlimit(resource.RLIMIT_NPROC, (NPROC, NPROC))
    return apply


# Docker's default seccomp profile refuses unshare(), so there is no mount or
# network namespace to drop into, and the repo bind mount (9p from Windows)
# ignores uid permissions: nobody can still write /app. This audit hook stops
# writes outside the work dir, new processes, sockets and ctypes symbol lookups
# (the route around the hook). It is a second layer, not a boundary.
GUARD = r'''
import os, sys
def _make_hook():
    # State lives in this closure: as globals of __main__ (this file), the child could
    # rebind them through sys.modules["__main__"].
    root = os.path.realpath(os.getcwd())
    realpath, fsdecode, sep = os.path.realpath, os.fsdecode, os.sep
    W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    # C modules that act with no audit event: _posixsubprocess.fork_exec starts
    # processes, _sqlite3 and the dbm modules write files, _ctypes calls libc. posix is
    # listed so a fresh copy cannot bring back mkfifo and mknod. Refused with
    # ImportError so numpy's "try: import ctypes" still works; scipy and sympy import
    # ctypes unguarded and so cannot load here.
    deny = frozenset(("_posixsubprocess", "_sqlite3", "_ctypes", "_dbm", "_gdbm", "posix"))
    def inside(p):
        if isinstance(p, int):
            return True
        p = realpath(fsdecode(p))
        return p == root or p.startswith(root + sep)
    def hook(event, args):
        if event == "open":
            path, mode, flags = args
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (flags or 0) & W
            if writing and not inside(path):
                raise PermissionError(f"sandbox: write outside the work dir: {path}")
        elif event in ("os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.link",
                       "os.symlink", "os.truncate", "os.utime", "os.setxattr", "os.removexattr",
                       "shutil.rmtree", "shutil.copyfile"):
            if args and not inside(args[0]):
                raise PermissionError(f"sandbox: {event} outside the work dir")
        elif event in ("os.rename", "os.replace"):
            if not (inside(args[0]) and inside(args[1])):
                raise PermissionError(f"sandbox: {event} outside the work dir")
        elif event in ("os.system", "os.exec", "os.posix_spawn", "os.spawn", "subprocess.Popen",
                       "os.fork", "os.forkpty", "pty.spawn", "socket.connect", "socket.bind",
                       "socket.sendto", "socket.getaddrinfo", "ctypes.dlsym", "ctypes.dlsym/handle",
                       "sqlite3.connect", "gc.get_objects", "gc.get_referrers", "gc.get_referents"):
            # gc would hand back this hook's closure.
            raise PermissionError(f"sandbox: {event} is not allowed")
        elif event == "ctypes.dlopen" and args and args[0] is not None:
            raise PermissionError("sandbox: ctypes.dlopen is not allowed")
        # Also raised by _imp.create_dynamic, so a loader called directly is covered.
        elif event == "import" and isinstance(args[0], str) and args[0].split(".")[0] in deny:
            raise ImportError(f"sandbox: import of {args[0]} is not allowed")
    return hook
# Python 3.11 has no audit event for mkfifo or mknod.
import posix
def _no_node(*a, **k):
    raise PermissionError("sandbox: mkfifo and mknod are not allowed")
for _m in (os, posix):
    _m.mkfifo = _m.mknod = _no_node
# asyncio imports subprocess at load time, so it stays importable with its
# process launcher swapped out; the hook refuses any fresh copy of _posixsubprocess.
import subprocess, _posixsubprocess
def _no_fork_exec(*a, **k):
    raise PermissionError("sandbox: fork_exec is not allowed")
_posixsubprocess.fork_exec = subprocess._fork_exec = _no_fork_exec
del posix, _m, subprocess, _posixsubprocess
sys.addaudithook(_make_hook())
del _make_hook
with open("main.py", encoding="utf-8") as _f:
    _src = _f.read()
exec(compile(_src, "main.py", "exec"), {"__name__": "__main__", "__builtins__": __builtins__})
'''


def run_python(source, timeout_s=10):
    """Return (ok, stdout, stderr). ok is exit code 0 within timeout_s."""
    work = tempfile.mkdtemp(prefix="maya_sb_")
    try:
        os.chmod(work, 0o777)
        main = os.path.join(work, "main.py")
        with open(main, "w", encoding="utf-8") as f:
            f.write(source)
        runner = os.path.join(work, "_run.py")
        with open(runner, "w", encoding="utf-8") as f:
            f.write(GUARD)
        for p in (main, runner):
            os.chmod(p, 0o644)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": work, "TMPDIR": work,
               "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8",
               # numpy/BLAS would start one thread per core and hit NPROC.
               "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        # Output goes to files so RLIMIT_FSIZE caps it; a pipe would let a
        # print loop fill the parent's memory.
        out_p, err_p = os.path.join(work, "stdout"), os.path.join(work, "stderr")
        with open(out_p, "wb") as out, open(err_p, "wb") as err:
            kw = {"preexec_fn": _limits(int(timeout_s) + 1)} if resource else {}
            proc = subprocess.Popen([sys.executable, "-I", "-B", runner], cwd=work, env=env,
                                    stdin=subprocess.DEVNULL, stdout=out, stderr=err, **kw)
            try:
                code = proc.wait(timeout=timeout_s)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (AttributeError, ProcessLookupError, PermissionError):
                    proc.kill()
                proc.wait()
                code = -9
        with open(out_p, encoding="utf-8", errors="replace") as f:
            stdout = f.read()[-OUT_CHARS:]
        with open(err_p, encoding="utf-8", errors="replace") as f:
            stderr = f.read()[-OUT_CHARS:]
        if timed_out:
            stderr += f"\nTimeoutError: no result within {timeout_s} s"
        return code == 0 and not timed_out, stdout, stderr
    finally:
        shutil.rmtree(work, ignore_errors=True)
