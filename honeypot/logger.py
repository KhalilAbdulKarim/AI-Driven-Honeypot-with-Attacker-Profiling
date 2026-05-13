import json
import os
import time
from datetime import datetime, timezone

from honeypot import db
from honeypot import geo

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


class SessionLogger:
    def __init__(self, session_id: str, client_ip: str, client_port: int):
        self.session_id = session_id
        self.client_ip = client_ip
        self.client_port = client_port
        self.start_time = time.time()
        self.geo_data = geo.lookup(client_ip)

        self.data = {
            "session_id": session_id,
            "client_ip": client_ip,
            "client_port": client_port,
            "geo": self.geo_data,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "duration_s": None,
            "auth_attempts": [],
            "commands": [],
        }

        db.insert_session(session_id, client_ip, client_port, self.geo_data)
        print(f"[geo] {client_ip} → {self.geo_data.get('city')}, "
              f"{self.geo_data.get('country')} ({self.geo_data.get('isp')})")

    def log_auth(self, username: str, password: str, success: bool = True):
        ts = datetime.now(timezone.utc).isoformat()
        self.data["auth_attempts"].append({
            "username": username,
            "password": password,
            "success": success,
            "timestamp": ts,
        })
        db.insert_auth(self.session_id, username, password, success, ts)
        self._save()

    def log_command(self, command: str, response: str):
        ts = datetime.now(timezone.utc).isoformat()
        offset = round((time.time() - self.start_time) * 1000)
        self.data["commands"].append({
            "command": command.strip(),
            "response": response.strip(),
            "timestamp": ts,
            "offset_ms": offset,
        })
        db.insert_command(self.session_id, command.strip(), response.strip(), offset, ts)
        self._save()

    def close(self):
        ended_at = datetime.now(timezone.utc).isoformat()
        duration = round(time.time() - self.start_time, 2)
        self.data["ended_at"] = ended_at
        self.data["duration_s"] = duration
        db.close_session(self.session_id, ended_at, duration)
        self._save()
        print(f"[session closed] {self.session_id} — "
            f"{len(self.data['commands'])} commands, {duration}s")

        # automatically enqueue for LLM profiling
        from honeypot.worker import enqueue
        enqueue(self.session_id)

    def _save(self):
        path = os.path.join(LOG_DIR, f"{self.session_id}.json")
        with open(path, "w") as f:
            json.dump(self.data, f, indent=2)

            