import sqlite3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(_PROJECT_ROOT / "data" / "honeypot.db")
(_PROJECT_ROOT / "data").mkdir(exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id            TEXT PRIMARY KEY,
            client_ip     TEXT NOT NULL,
            client_port   INTEGER,
            country       TEXT,
            country_code  TEXT,
            city          TEXT,
            latitude      REAL,
            longitude     REAL,
            isp           TEXT,
            started_at    TEXT,
            ended_at      TEXT,
            duration_s    REAL,
            total_commands INTEGER DEFAULT 0,
            total_auth_attempts INTEGER DEFAULT 0,
            profile_json  TEXT
        );

        CREATE TABLE IF NOT EXISTS auth_attempts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            username    TEXT,
            password    TEXT,
            success     INTEGER,
            timestamp   TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS commands (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            command     TEXT,
            response    TEXT,
            offset_ms   INTEGER,
            timestamp   TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        """)
    print(f"[db] initialised at {DB_PATH}")


def insert_session(session_id: str, client_ip: str, client_port: int, geo: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO sessions
            (id, client_ip, client_port, country, country_code, city,
             latitude, longitude, isp, started_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            session_id, client_ip, client_port,
            geo.get("country"), geo.get("countryCode"), geo.get("city"),
            geo.get("lat"), geo.get("lon"), geo.get("isp"),
            datetime.now(timezone.utc).isoformat()
        ))


def insert_auth(session_id: str, username: str, password: str, success: bool, timestamp: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO auth_attempts (session_id, username, password, success, timestamp)
            VALUES (?,?,?,?,?)
        """, (session_id, username, password, int(success), timestamp))
        conn.execute("""
            UPDATE sessions SET total_auth_attempts = total_auth_attempts + 1
            WHERE id = ?
        """, (session_id,))


def insert_command(session_id: str, command: str, response: str, offset_ms: int, timestamp: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO commands (session_id, command, response, offset_ms, timestamp)
            VALUES (?,?,?,?,?)
        """, (session_id, command, response, offset_ms, timestamp))
        conn.execute("""
            UPDATE sessions SET total_commands = total_commands + 1
            WHERE id = ?
        """, (session_id,))


def close_session(session_id: str, ended_at: str, duration_s: float):
    with get_conn() as conn:
        conn.execute("""
            UPDATE sessions SET ended_at = ?, duration_s = ? WHERE id = ?
        """, (ended_at, duration_s, session_id))


def save_profile(session_id: str, profile: dict):
    with get_conn() as conn:
        conn.execute("""
            UPDATE sessions SET profile_json = ? WHERE id = ?
        """, (json.dumps(profile), session_id))


def get_all_sessions(limit: int = 100) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_session_detail(session_id: str) -> dict:
    with get_conn() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        auths = conn.execute(
            "SELECT * FROM auth_attempts WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        ).fetchall()
        cmds = conn.execute(
            "SELECT * FROM commands WHERE session_id = ? ORDER BY offset_ms",
            (session_id,)
        ).fetchall()
    return {
        "session": dict(session) if session else {},
        "auth_attempts": [dict(r) for r in auths],
        "commands": [dict(r) for r in cmds],
    }


def get_top_credentials(limit: int = 20) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT username, password, COUNT(*) as count
            FROM auth_attempts
            GROUP BY username, password
            ORDER BY count DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_top_commands(limit: int = 20) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT command, COUNT(*) as count
            FROM commands
            GROUP BY command
            ORDER BY count DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_sessions_by_country() -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT country, country_code, COUNT(*) as count
            FROM sessions
            WHERE country IS NOT NULL
            GROUP BY country
            ORDER BY count DESC
        """).fetchall()
    return [dict(r) for r in rows]