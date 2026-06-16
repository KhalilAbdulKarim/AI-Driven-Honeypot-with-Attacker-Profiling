# AI-Driven Honeypot with Attacker Profiling

A production-grade SSH honeypot that lures real attackers, captures everything they do, and uses an LLM to automatically profile them classifying skill level, tools, intent, and MITRE ATT&CK techniques in real time.

---

## What it does

Deploys a fake Ubuntu SSH server on a public VPS. Real bots and attackers connect thinking they've found a vulnerable Linux machine. Every credential attempt, every command typed, and every behavioral pattern is silently captured. When a session ends, an LLM pipeline automatically analyzes it and produces a structured attacker profile including MITRE ATT&CK technique mapping, skill classification, and defensive recommendations.

**Within 24 hours of going live, the honeypot collected 200+ real attack sessions from multiple countries across Europe, Asia, and the Americas.**

---

## Architecture

```
Internet (attackers)
        │
        ▼
  Fake SSH server (Paramiko)
        │
        ▼
  Session capture
  IP · credentials · commands · timing
        │
        ├──────────────────────┐
        ▼                      ▼
  IP geolocation           SQLite DB
  (country, ISP)           sessions · commands
        │                      │
        └──────────┬───────────┘
                   ▼
           Background worker queue
           (async · dedup · rate-limited)
                   │
                   ▼
           Claude API
           skill · intent · MITRE ATT&CK
                   │
                   ▼
           Profile stored → Flask API → React dashboard
```

---

## Features

### Fake SSH server
- Accepts any username and password — the attacker thinks they broke in
- Emulates a realistic Ubuntu 22.04 environment with a full filesystem
- Supports 60+ Linux commands: `cat`, `ls`, `ps aux`, `netstat`, `wget`, `curl`, `base64`, `iptables`, `crontab`, `useradd`, `nmap`, and more
- Fake sensitive files: `/etc/shadow`, `/root/.ssh/id_rsa`, `/var/www/html/wp-config.php`, AWS metadata endpoint
- Dynamic MOTD with real date/time on every connection
- Captures keystroke timing (`offset_ms` per command) for behavioral fingerprinting

### Session capture
- Source IP, credentials tried, commands executed, responses, timing
- IP geolocation (country, city, ISP, coordinates) with persistent cache
- SQLite database: sessions, auth_attempts, commands, fingerprints tables
- JSON log file per session for raw replay

### LLM attacker profiler
Cost-optimized pipeline using Claude Haiku:

| Optimization | Effect |
|---|---|
| Persistent fingerprint deduplication | Identical bot waves profiled once only |
| Skip gate (no auth = no API call) | ~30% of sessions skipped |
| Payload trimmer (first 10 + last 10 commands) | ~60% fewer input tokens |
| Claude Haiku over Sonnet | ~10x cost reduction |
| Retry on JSON parse failure | Recovers from truncated responses |

**Profile output per session:**
```json
{
  "skill_level": "intermediate",
  "probable_intent": "cryptomining",
  "detected_tools": ["wget", "base64 decoder", "crontab persistence"],
  "ioc": ["malicious-domain.com/payload.sh"],
  "mitre": [
    {
      "tactic": "Initial Access",
      "technique_id": "T1110.001",
      "technique_name": "Brute Force: Password Guessing",
      "evidence": "root:123456, admin:admin"
    },
    {
      "tactic": "Persistence",
      "technique_id": "T1053.005",
      "technique_name": "Scheduled Task/Job: Cron",
      "evidence": "crontab -e"
    }
  ],
  "kill_chain_phase": "exploitation",
  "defensive_action": "block_ip",
  "defensive_recommendations": [
    "Block source IP at firewall",
    "Enable SSH rate limiting"
  ],
  "summary": "Intermediate attacker attempted credential stuffing then deployed a cryptominer via wget and established cron persistence.",
  "confidence": 0.82
}
```

### React dashboard
- **Dashboard tab**: stat cards, skill distribution chart, intent chart, top credentials heatmap, top commands, activity feed, cost tracker
- **Live Map tab**: world map with colored attack pins (red=advanced, amber=intermediate, blue=script kiddie), filter by skill level, session detail side panel
- **Session modal**: full connection info, AI profile with confidence bar, MITRE ATT&CK techniques with color-coded tactics and evidence, defensive recommendations, command timeline
- **Export**: CSV download of all sessions with MITRE technique IDs
- Auto-refreshes every 15 seconds

---

## Tech stack

| Layer | Technology |
|---|---|
| Fake SSH server | Python · Paramiko |
| Session storage | SQLite |
| IP geolocation | ip-api.com |
| LLM profiling | Anthropic Claude Haiku API |
| Backend API | Flask · Flask-CORS |
| Frontend | React · Vite · Recharts · Leaflet.js |
| Deployment | Linux VPS · Supervisor |

---

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/sessions` | All sessions |
| `GET /api/sessions/<id>` | Full session detail + AI profile |
| `GET /api/stats` | Aggregated stats and chart data |
| `GET /api/export/csv` | Download all sessions as CSV |
| `GET /api/health` | Health check |

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Anthropic API key

### Local development

```bash
git clone https://github.com/YOUR_USERNAME/honeypot
cd honeypot

# Python setup
python3 -m venv honeypot/.venv
source honeypot/.venv/bin/activate
pip install -r requirements.txt

# add your API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# terminal 1 — honeypot
python main.py

# terminal 2 — dashboard API
python dashboard/app.py

# terminal 3 — React UI
cd dashboard/react-ui
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Server deployment

```bash
git clone https://github.com/YOUR_USERNAME/honeypot
cd honeypot
echo "ANTHROPIC_API_KEY=your-key-here" > .env
bash deploy/install.sh
```

Recommended inbound firewall rules:

| Port | Source | Purpose |
|---|---|---|
| 22 | 0.0.0.0/0 | Honeypot — attracts bots |
| 5002 | Your IP | Dashboard API |

---

## MITRE ATT&CK coverage

Automatically detected and mapped from session behavior:

| Technique ID | Name | Tactic |
|---|---|---|
| T1110.001 | Brute Force: Password Guessing | Credential Access |
| T1133 | External Remote Services | Initial Access |
| T1003.008 | OS Credential Dumping | Credential Access |
| T1105 | Ingress Tool Transfer | Command and Control |
| T1053.005 | Scheduled Task/Job: Cron | Persistence |
| T1136.001 | Create Account: Local Account | Persistence |
| T1033 | System Owner/User Discovery | Discovery |
| T1016 | System Network Configuration Discovery | Discovery |
| T1057 | Process Discovery | Discovery |
| T1083 | File and Directory Discovery | Discovery |
| T1140 | Deobfuscate/Decode Files | Defense Evasion |
| T1562.004 | Impair Defenses: Disable Firewall | Defense Evasion |
| T1098.004 | SSH Authorized Keys | Persistence |
| T1496 | Resource Hijacking | Impact |
| T1059.004 | Unix Shell | Execution |
| T1552.005 | Cloud Instance Metadata API | Credential Access |

---

## License

MIT
