import queue
import threading
import time
from honeypot.profiler import profile_session

_queue: queue.Queue = queue.Queue()
_started = False


def enqueue(session_id: str):
    """Call this when a session closes — adds it to the profiling queue."""
    _queue.put(session_id)


def _worker_loop():
    print("[worker] profiler queue started")
    while True:
        try:
            session_id = _queue.get(timeout=5)
            # small delay — let DB writes settle before querying
            time.sleep(2)
            profile_session(session_id)
            _queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[worker] error: {e}")


def start():
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()