import csv
import io
from flask import Flask, jsonify, send_from_directory, request, Response
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0,str(PROJECT_ROOT))

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from db import (
    get_all_sessions,
    get_session_detail,
    get_top_commands,
    get_top_credentials,
    get_sessions_by_country,
    init_db,
)

# ── app setup ────────────────────────────────────────────────────────────────
REACT_DIST = Path(__file__).parent / "react-ui" / "dist"

app = Flask(__name__, static_folder=None)
CORS(app)  # allow React dev server on :3000 to call Flask on :5002


# ── helpers ──────────────────────────────────────────────────────────────────
def _parse_profile(session: dict) -> dict | None:
    raw = session.get("profile_json")
    if not raw:
        return None
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None


def _format_session(s: dict) -> dict:
    profile = _parse_profile(s)
    return {
        "id":                   s["id"],
        "ip":                   s["client_ip"],
        "country":              s.get("country") or "Unknown",
        "country_code":         s.get("country_code") or "",
        "city":                 s.get("city") or "",
        "isp":                  s.get("isp") or "",
        "lat":                  s.get("latitude"),
        "lon":                  s.get("longitude"),
        "started_at":           s.get("started_at"),
        "ended_at":             s.get("ended_at"),
        "duration_s":           s.get("duration_s"),
        "total_commands":       s.get("total_commands", 0),
        "total_auth_attempts":  s.get("total_auth_attempts", 0),
        # profile fields — None when not yet profiled
        "skill_level":          profile.get("skill_level")        if profile else None,
        "intent":               profile.get("probable_intent")    if profile else None,
        "detected_tools":       profile.get("detected_tools", []) if profile else [],
        "ioc":                  profile.get("ioc", [])            if profile else [],
        "defensive_action":     profile.get("defensive_action")   if profile else None,
        "summary":              profile.get("summary")            if profile else None,
        "confidence":           profile.get("confidence")         if profile else None,
        "profiled":             profile is not None,
    }


# ── API routes ────────────────────────────────────────────────────────────────
@app.route("/api/sessions")
def api_sessions():
    limit = min(int(request.args.get("limit", 200)), 500)
    sessions = get_all_sessions(limit=limit)
    return jsonify([_format_session(s) for s in sessions])


@app.route("/api/sessions/<session_id>")
def api_session_detail(session_id: str):
    detail = get_session_detail(session_id)
    if not detail["session"]:
        return jsonify({"error": "Session not found"}), 404

    s       = detail["session"]
    profile = _parse_profile(s)

    return jsonify({
        "session": {
            **_format_session(s),
            # include raw profile for the modal
            "profile": profile,
        },
        "commands":      detail["commands"],
        "auth_attempts": detail["auth_attempts"],
    })


@app.route("/api/stats")
def api_stats():
    sessions = get_all_sessions(limit=500)
    profiled = [s for s in sessions if s.get("profile_json")]

    skill_counts  = {"script_kiddie": 0, "intermediate": 0, "advanced": 0}
    intent_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    total_tokens_in  = 0
    total_tokens_out = 0
    estimated_cost   = 0.0

    for s in profiled:
        p = _parse_profile(s)
        if not p:
            continue

        sk = p.get("skill_level", "unknown")
        it = p.get("probable_intent", "unknown")
        ac = p.get("defensive_action", "unknown")

        if sk in skill_counts:
            skill_counts[sk] += 1

        intent_counts[it] = intent_counts.get(it, 0) + 1
        action_counts[ac] = action_counts.get(ac, 0) + 1

        tokens = p.get("_tokens", {})
        ti = tokens.get("in", 0)
        to = tokens.get("out", 0)
        total_tokens_in  += ti
        total_tokens_out += to
        estimated_cost   += (ti * 0.80 + to * 4.0) / 1_000_000

    # aggregate totals
    total_commands = sum(s.get("total_commands", 0) for s in sessions)
    total_auths    = sum(s.get("total_auth_attempts", 0) for s in sessions)

    return jsonify({
        "total_sessions":   len(sessions),
        "profiled":         len(profiled),
        "total_commands":   total_commands,
        "total_auth_attempts": total_auths,
        "skill_counts":     skill_counts,
        "intent_counts":    intent_counts,
        "action_counts":    action_counts,
        "top_credentials":  get_top_credentials(10),
        "top_commands":     get_top_commands(10),
        "by_country":       get_sessions_by_country(),
        "token_usage": {
            "input":          total_tokens_in,
            "output":         total_tokens_out,
            "estimated_usd":  round(estimated_cost, 5),
        },
    })


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})

@app.route("/api/export/csv")
def api_export_csv():
    sessions = get_all_sessions(limit=10000)
    output   = io.StringIO()
    writer   = csv.writer(output)

    writer.writerow([
        "session_id", "ip", "country", "city", "isp",
        "started_at", "duration_s", "total_commands",
        "total_auth_attempts", "skill_level", "probable_intent",
        "defensive_action", "confidence", "summary", "mitre_techniques",
    ])

    for s in sessions:
        profile = _parse_profile(s)
        mitre   = "|".join(
            m.get("technique_id", "")
            for m in (profile.get("mitre", []) if profile else [])
        )
        writer.writerow([
            s["id"],
            s["client_ip"],
            s.get("country", ""),
            s.get("city", ""),
            s.get("isp", ""),
            s.get("started_at", ""),
            s.get("duration_s", ""),
            s.get("total_commands", 0),
            s.get("total_auth_attempts", 0),
            profile.get("skill_level", "")      if profile else "",
            profile.get("probable_intent", "")  if profile else "",
            profile.get("defensive_action", "") if profile else "",
            profile.get("confidence", "")       if profile else "",
            profile.get("summary", "")          if profile else "",
            mitre,
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment;filename=honeypot_sessions.csv"
        },
    )


# ── serve React build (production) ───────────────────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path: str):
    # never intercept API routes
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    if not REACT_DIST.exists():
        return jsonify({"error": "React build not found"}), 404

    target = REACT_DIST / path
    if path and target.exists():
        return send_from_directory(REACT_DIST, path)

    return send_from_directory(REACT_DIST, "index.html")

# ── entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.getenv("DASHBOARD_PORT", 5002))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"[dashboard] running on http://0.0.0.0:{port}")
    print(f"[dashboard] React dist: {'found' if REACT_DIST.exists() else 'not built yet — run npm run build'}")
    app.run(host="0.0.0.0", port=port, debug=debug)