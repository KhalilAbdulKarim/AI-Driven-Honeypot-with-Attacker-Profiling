import logging
import threading
import sys

# ── silence ALL paramiko noise ────────────────────────────────────────────────

# 1. Python logging
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)

# 2. Thread excepthook — catches unhandled exceptions in daemon threads
def _thread_excepthook(args):
    module = getattr(args.exc_type, "__module__", "") or ""
    if "paramiko" in module:
        return
    if args.exc_type in (EOFError, ConnectionResetError, BrokenPipeError,
                          OSError, TimeoutError):
        return
    print(f"[thread error] {args.exc_type.__name__}: {args.exc_value}",
          file=sys.stderr)

threading.excepthook = _thread_excepthook

# 3. Monkey-patch paramiko Transport._log to suppress error-level noise
try:
    import paramiko.transport as _pt

    _original_log = _pt.Transport._log

    def _silent_log(self, level, msg, *args):
        import logging as _logging
        if level >= _logging.ERROR:
            return
        _original_log(self, level, msg, *args)

    _pt.Transport._log = _silent_log
except Exception:
    pass

# 4. Monkey-patch paramiko Transport.run to swallow all exceptions silently
try:
    import paramiko.transport as _pt2

    _original_run = _pt2.Transport.run

    def _silent_run(self):
        try:
            _original_run(self)
        except Exception:
            pass

    _pt2.Transport.run = _silent_run
except Exception:
    pass

# ── honeypot startup ──────────────────────────────────────────────────────────
from honeypot.db import init_db
from honeypot.worker import start as start_worker
from honeypot.ssh_server import start_server

if __name__ == "__main__":
    init_db()
    start_worker()
    start_server(host="0.0.0.0", port=2222)