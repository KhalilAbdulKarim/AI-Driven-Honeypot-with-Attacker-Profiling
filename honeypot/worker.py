import queue
import threading
import time

from honeypot.profiler import profile_session

_queue:    queue.Queue      = queue.Queue()
_started:  bool             = False
_semaphore = threading.Semaphore(5)  # max 5 concurrent Claude calls


def enqueue(session_id: str):
    _queue.put(session_id)


def _profile_with_sem(session_id: str):
    with _semaphore:
        try:
            profile_session(session_id)
        except Exception as e:
            print(f"[worker] profile error for {session_id}: {e}")


def _worker_loop():
    print("[worker] profiler queue started")
    while True:
        try:
            session_id = _queue.get(timeout=5)
            time.sleep(2)   # let DB writes settle
            t = threading.Thread(
                target=_profile_with_sem,
                args=(session_id,),
                daemon=True,
            )
            t.start()
            _queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[worker] queue error: {e}")


def start():
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()