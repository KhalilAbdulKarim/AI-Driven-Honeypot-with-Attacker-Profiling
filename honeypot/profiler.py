import hashlib
import json
import os
import threading
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from honeypot.db import get_session_detail, save_profile, get_fingerprint, save_fingerprint

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── in-process dedup cache (L1) — backed by SQLite (L2) ──────────────────────
_seen_fingerprints: dict[str, str] = {}
_dedup_lock = threading.Lock()

# ── constants ─────────────────────────────────────────────────────────────────
MAX_COMMANDS   = 20
MAX_RESP_CHARS = 80
MAX_CREDS      = 10
MAX_OUT_TOKENS = 1024
MAX_RETRY_TOKENS = 1500 
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You are a senior threat intelligence analyst at a SOC. "
    "Analyze the SSH honeypot session and return ONLY a JSON object — "
    "no prose, no markdown fences, no explanation.\n\n"
    "Schema:\n"
    "{\n"
    '  "skill_level": "script_kiddie|intermediate|advanced",\n'
    '  "probable_intent": "credential_harvesting|cryptomining|ransomware|reconnaissance|data_theft|botnet_recruitment|unknown",\n'
    '  "detected_tools": ["tool or technique name"],\n'
    '  "ioc": ["suspicious IPs, domains, filenames, hashes"],\n'
    '  "mitre": [\n'
    '    {\n'
    '      "tactic": "tactic name e.g. Initial Access",\n'
    '      "technique_id": "e.g. T1110.001",\n'
    '      "technique_name": "e.g. Brute Force: Password Guessing",\n'
    '      "evidence": "exact command or behavior that triggered this"\n'
    '    }\n'
    '  ],\n'
    '  "kill_chain_phase": "reconnaissance|weaponization|delivery|exploitation|installation|command_and_control|actions_on_objectives",\n'
    '  "defensive_action": "block_ip|rate_limit|monitor|alert_soc|ignore",\n'
    '  "defensive_recommendations": ["specific actionable recommendation"],\n'
    '  "summary": "2 sentences max — attacker profile and likely goal",\n'
    '  "confidence": 0.0\n'
    "}\n\n"
    "MITRE mapping rules — map ALL that apply, minimum 1 technique per session:\n"
    "- ANY auth attempt → T1110.001 Brute Force: Password Guessing (TA0006) — ALWAYS include\n"
    "- ANY SSH connection → T1133 External Remote Services (TA0001 Initial Access)\n"
    "- Repeated connections same IP → T1110 Brute Force (TA0006)\n"
    "- cat /etc/passwd or /etc/shadow → T1003.008 OS Credential Dumping (TA0006)\n"
    "- wget/curl to external URL → T1105 Ingress Tool Transfer (TA0011)\n"
    "- crontab -e or /etc/cron → T1053.005 Scheduled Task/Job: Cron (TA0003)\n"
    "- useradd or passwd → T1136.001 Create Account: Local Account (TA0003)\n"
    "- whoami/id/uname → T1033 System Owner/User Discovery (TA0007)\n"
    "- ifconfig/ip addr/netstat → T1016 System Network Configuration Discovery (TA0007)\n"
    "- ps/top → T1057 Process Discovery (TA0007)\n"
    "- ls/find/locate → T1083 File and Directory Discovery (TA0007)\n"
    "- base64 decode → T1140 Deobfuscate/Decode Files (TA0005)\n"
    "- iptables -F → T1562.004 Disable Firewall (TA0005)\n"
    "- chmod +x on downloaded file → T1222 File Permissions Modification (TA0005)\n"
    "- authorized_keys or ssh-keygen → T1098.004 SSH Authorized Keys (TA0003)\n"
    "- /proc/cpuinfo or mining keywords → T1496 Resource Hijacking (TA0040)\n"
    "- Any shell execution → T1059.004 Command and Scripting: Unix Shell (TA0002)\n"
    "- curl/wget 169.254.169.254 → T1552.005 Cloud Instance Metadata API (TA0006)\n"
    "Evidence must quote the actual credential or command seen. "
    "mitre array must NEVER be empty."
)


def _fingerprint(detail: dict) -> str:
    cmds  = [c["command"] for c in detail["commands"]]
    creds = [f"{a['username']}:{a['password']}" for a in detail["auth_attempts"]]
    raw   = json.dumps({"c": sorted(creds), "k": cmds}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _should_skip(detail: dict) -> bool:
    return not detail["auth_attempts"] and not detail["commands"]


def _check_dedup(fp: str) -> str | None:
    """Check memory cache first, then SQLite — persistent across restarts."""
    with _dedup_lock:
        if fp in _seen_fingerprints:
            return _seen_fingerprints[fp]
    result = get_fingerprint(fp)
    if result:
        with _dedup_lock:
            _seen_fingerprints[fp] = result
    return result


def _mark_dedup(fp: str, session_id: str):
    """Save to both memory and SQLite."""
    with _dedup_lock:
        _seen_fingerprints[fp] = session_id
    save_fingerprint(fp, session_id)


def _trim_payload(detail: dict) -> dict:
    session = detail["session"]
    cmds    = detail["commands"]
    auths   = detail["auth_attempts"]

    if len(cmds) > MAX_COMMANDS:
        cmds = cmds[:10] + cmds[-10:]

    trimmed_cmds = [
        {
            "cmd":       c["command"],
            "offset_ms": c["offset_ms"],
            "resp":      (c["response"] or "")[:MAX_RESP_CHARS],
        }
        for c in cmds
    ]
    trimmed_creds = [
        f"{a['username']}:{a['password']}"
        for a in auths[:MAX_CREDS]
        if a.get("password") not in ("connection", "")
    ]

    return {
        "ip":      session.get("client_ip"),
        "country": session.get("country"),
        "isp":     session.get("isp"),
        "dur_s":   session.get("duration_s"),
        "n_cmds":  session.get("total_commands"),
        "creds":   trimmed_creds,
        "commands": trimmed_cmds,
    }


def _parse_profile(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def _call_claude(user_msg: str, max_tokens: int) -> dict | None:
    """Call Claude with retry on JSON parse failure."""
    for attempt in range(2):
        tokens = max_tokens if attempt == 0 else MAX_RETRY_TOKENS
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            usage = resp.usage
            cost  = (usage.input_tokens * 0.80 + usage.output_tokens * 4.0) / 1_000_000
            print(f"[profiler] tokens in={usage.input_tokens} "
                  f"out={usage.output_tokens} est=${cost:.5f}")
            raw     = resp.content[0].text
            profile = _parse_profile(raw)
            profile["_tokens"] = {
                "in": usage.input_tokens, "out": usage.output_tokens
            }
            return profile
        except json.JSONDecodeError as e:
            if attempt == 0:
                print(f"[profiler] JSON parse failed, retrying with {MAX_RETRY_TOKENS} tokens...")
                continue
            print(f"[profiler] JSON parse failed after retry: {e}")
            return None
        except Exception as e:
            print(f"[profiler] API error: {e}")
            return None
    return None


def profile_session(session_id: str) -> dict | None:
    detail = get_session_detail(session_id)

    if not detail["session"]:
        print(f"[profiler] {session_id} not found")
        return None

    if detail["session"].get("profile_json"):
        return json.loads(detail["session"]["profile_json"])

    if _should_skip(detail):
        print(f"[profiler] {session_id} skipped (no data)")
        return None

    fp          = _fingerprint(detail)
    original_id = _check_dedup(fp)

    if original_id and original_id != session_id:
        print(f"[profiler] {session_id} duplicate of {original_id} — reusing profile")
        original = get_session_detail(original_id)["session"]
        if original.get("profile_json"):
            profile = json.loads(original["profile_json"])
            profile["session_id"]   = session_id
            profile["_reused_from"] = original_id
            save_profile(session_id, profile)
            return profile

    _mark_dedup(fp, session_id)

    payload  = _trim_payload(detail)
    user_msg = f"Analyse this SSH honeypot session:\n{json.dumps(payload)}"
    n        = detail["session"].get("total_commands", 0)
    print(f"[profiler] calling {MODEL} for {session_id} ({n} cmds, fp={fp})...")

    profile = _call_claude(user_msg, MAX_OUT_TOKENS)
    if not profile:
        return None

    profile["session_id"] = session_id
    save_profile(session_id, profile)
    print(f"[profiler] ✓ {session_id} → {profile.get('skill_level')} / "
          f"{profile.get('probable_intent')} conf={profile.get('confidence')}")
    return profile


def profile_all_unprofiled() -> list[dict]:
    from honeypot.db import get_all_sessions
    sessions   = get_all_sessions(limit=5000)
    unprofiled = [s for s in sessions if not s.get("profile_json")]
    print(f"[profiler] {len(unprofiled)} sessions queued")
    return [p for s in unprofiled if (p := profile_session(s["id"]))]