import hashlib
import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv
from honeypot.db import get_session_detail, save_profile

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── in-process dedup cache (survives the run, not restarts) ──────────────────
_seen_fingerprints: dict[str, str] = {}  # fingerprint → session_id that was profiled

# ── constants ────────────────────────────────────────────────────────────────
MAX_COMMANDS    = 20    # trim long sessions — first 10 + last 10 most informative
MAX_RESP_CHARS  = 80    # response preview per command
MAX_CREDS       = 15    # credential pairs to include
MAX_OUT_TOKENS  = 1024  

# Haiku 3.5: $0.80/M input, $4/M output — ~10x cheaper than Sonnet for this task
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
    "- ANY auth attempt → T1110.001 Brute Force: Password Guessing (TA0006 Credential Access) — ALWAYS include this\n"
    "- ANY SSH connection from external IP → T1133 External Remote Services (TA0001 Initial Access)\n"
    "- Repeated connections same IP → T1110 Brute Force (TA0006 Credential Access)\n"
    "- cat /etc/passwd or /etc/shadow → T1003.008 OS Credential Dumping (TA0006)\n"
    "- wget/curl to external URL → T1105 Ingress Tool Transfer (TA0011 C2)\n"
    "- crontab -e or /etc/cron → T1053.005 Scheduled Task/Job: Cron (TA0003 Persistence)\n"
    "- useradd or passwd → T1136.001 Create Account: Local Account (TA0003 Persistence)\n"
    "- whoami/id/uname → T1033 System Owner/User Discovery (TA0007 Discovery)\n"
    "- ifconfig/ip addr/netstat → T1016 System Network Configuration Discovery (TA0007)\n"
    "- ps/top → T1057 Process Discovery (TA0007)\n"
    "- ls/find/locate → T1083 File and Directory Discovery (TA0007)\n"
    "- base64 decode → T1140 Deobfuscate/Decode Files (TA0005 Defense Evasion)\n"
    "- iptables -F → T1562.004 Disable Firewall (TA0005 Defense Evasion)\n"
    "- chmod +x on downloaded file → T1222 File Permissions Modification (TA0005)\n"
    "- ssh-keygen or authorized_keys → T1098.004 SSH Authorized Keys (TA0003 Persistence)\n"
    "- /proc/cpuinfo or mining keywords → T1496 Resource Hijacking (TA0040 Impact)\n"
    "- Any shell execution → T1059.004 Command and Scripting: Unix Shell (TA0002 Execution)\n"
    "- curl/wget 169.254.169.254 → T1552.005 Cloud Instance Metadata API (TA0006)\n"
    "Evidence must quote the actual credential or command seen. "
    "mitre array must NEVER be empty — every session has at least T1110.001 and T1133."
)


def _fingerprint(detail: dict) -> str:
    """Hash of credential pairs + command list — identical bot waves hash the same."""
    cmds  = [c["command"] for c in detail["commands"]]
    creds = [f"{a['username']}:{a['password']}" for a in detail["auth_attempts"]]
    raw   = json.dumps({"c": sorted(creds), "k": cmds}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _should_skip(detail: dict) -> bool:
    """Skip sessions with no commands and no auth attempts — likely noise."""
    return not detail["commands"] and not detail["auth_attempts"]



def _trim_payload(detail: dict) -> dict:
    """
    Keep only what the LLM actually needs.
    For long command lists: first 10 + last 10 (setup + payload delivery).
    Truncate response previews aggressively.
    """
    session = detail["session"]
    cmds    = detail["commands"]
    auths   = detail["auth_attempts"]

    # first 10 + last 10 for long sessions, no duplicates
    if len(cmds) > MAX_COMMANDS:
        head = cmds[:10]
        tail = cmds[-10:]
        cmds = head + tail

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
    ]

    return {
        "ip":       session.get("client_ip"),
        "country":  session.get("country"),
        "isp":      session.get("isp"),
        "dur_s":    session.get("duration_s"),
        "n_cmds":   session.get("total_commands"),  # true total even if trimmed
        "creds":    trimmed_creds,
        "commands": trimmed_cmds,
    }


def _parse_profile(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def profile_session(session_id: str) -> dict | None:
    detail = get_session_detail(session_id)

    if not detail["session"]:
        print(f"[profiler] {session_id} not found")
        return None

    # already profiled — return cached result, never call API again
    if detail["session"].get("profile_json"):
        return json.loads(detail["session"]["profile_json"])

    # lever 1: skip empty sessions
    if _should_skip(detail):
        print(f"[profiler] {session_id} skipped (no data)")
        return None

    # lever 2: dedup — identical attack patterns share one profile
    fp = _fingerprint(detail)
    if fp in _seen_fingerprints:
        original_id = _seen_fingerprints[fp]
        print(f"[profiler] {session_id} is duplicate of {original_id} — reusing profile")
        original = get_session_detail(original_id)["session"]
        if original.get("profile_json"):
            profile = json.loads(original["profile_json"])
            profile["session_id"]      = session_id
            profile["_reused_from"]    = original_id
            save_profile(session_id, profile)
            return profile

    _seen_fingerprints[fp] = session_id

    # lever 3: trim payload
    payload = _trim_payload(detail)
    user_msg = f"Analyse this SSH honeypot session:\n{json.dumps(payload)}"

    n = detail["session"].get("total_commands", 0)
    print(f"[profiler] calling {MODEL} for {session_id} ({n} cmds, fp={fp})...")

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_OUT_TOKENS,   # lever 4: cap output tokens
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        # log actual token usage so you can tune further
        usage = resp.usage
        cost_usd = (usage.input_tokens * 0.80 + usage.output_tokens * 4.0) / 1_000_000
        print(f"[profiler] tokens in={usage.input_tokens} out={usage.output_tokens} "
              f"est=${cost_usd:.5f}")

        raw     = resp.content[0].text
        profile = _parse_profile(raw)
        profile["session_id"] = session_id
        profile["_tokens"]    = {"in": usage.input_tokens, "out": usage.output_tokens}

        save_profile(session_id, profile)
        print(f"[profiler] ✓ {session_id} → {profile.get('skill_level')} / "
              f"{profile.get('probable_intent')} conf={profile.get('confidence')}")
        return profile

    except json.JSONDecodeError as e:
        print(f"[profiler] JSON parse failed for {session_id}: {e}")
        return None
    except Exception as e:
        print(f"[profiler] API error for {session_id}: {e}")
        return None


# def profile_all_unprofiled() -> list[dict]:
#     from honeypot.db import get_all_sessions
#     sessions   = get_all_sessions(limit=500)
#     unprofiled = [s for s in sessions if not s.get("profile_json")]
#     print(f"[profiler] {len(unprofiled)} sessions queued")
#     return [p for s in unprofiled if (p := profile_session(s["id"]))]

def profile_all_unprofiled() -> list[dict]:
    from honeypot.db import get_all_sessions
    sessions   = get_all_sessions(limit=500)
    unprofiled = [s for s in sessions if not s.get("profile_json")]
    print(f"[profiler] {len(unprofiled)} sessions queued")
    profiles = []
    for s in unprofiled:
        p = profile_session(s["id"])
        if p:
            profiles.append(p)
    return profiles
