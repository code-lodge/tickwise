# ChronoLens

**Automatic time tracking for freelancers, powered by LLM classification.**

ChronoLens passively observes your screen, uses Claude or OpenAI to classify what you're working on, and generates billing reports and invoices — without you ever pressing a start/stop button.

It runs as a system tray app on Windows, macOS, and Linux. All data stays local. A configurable redaction engine strips sensitive content before anything leaves your machine.

---

## Why ChronoLens?

Manual time tracking is broken. You forget to start the timer, you forget to stop it, you forget which project you were on. At the end of the month you're guessing at hours and eating unbilled time.

ChronoLens fixes this by watching what's on your screen — your IDE, browser, terminal, email — and letting an LLM figure out which project and task category each window belongs to. You get accurate, granular time data without changing how you work.

**It's not a keylogger.** ChronoLens captures screenshots for OCR text extraction (never saved to disk), counts input events for idle detection (never records keystrokes), and redacts sensitive content before sending anything to the LLM API.

---

## Features

**Core Tracking**

- 1-second capture loop with perceptual hash change detection — OCR runs only when the screen actually changes (~2-4 times/minute instead of 60)
- Multi-monitor support — captures all screens, classifies the focused one, hash-tracks the rest for instant classification on focus switch
- Idle detection — automatically pauses when you step away, resumes when you're back

**LLM Classification**

- Bring your own API key (Claude or OpenAI)
- Automatic project + task classification with confidence scores
- Classification cache reduces API costs (~$1-5/month at typical usage)
- Monthly budget cap with notifications
- Graceful fallback — tracking continues even without an API key, sessions just lack project assignment

**Privacy & Redaction**

- 4 configurable privacy levels, from secrets-only (Level 1) to maximum redaction (Level 4)
- Level 1: API keys, passwords, private keys, JWTs, connection strings
- Level 2: Adds emails, phone numbers, IPs, IBANs, credit cards, file paths
- Level 3: Adds person/org names, monetary amounts, chat content, shell commands
- Level 4: Strips code blocks, all URLs, tabular data, quoted text — LLM sees structure only
- Custom redaction patterns for client-specific terms
- Redaction preview tool in the dashboard
- Screenshots are never stored — held in memory, discarded after OCR

**Dashboard**

- Live view with real-time current activity
- Timeline with day/week/month views — click to edit, split, merge sessions
- Project management with color coding, hourly rates, client assignment
- Reports: time summary, billing, activity breakdown, productivity
- Export to PDF, CSV, JSON

**Invoicing**

- Generate professional PDF invoices from tracked time
- Line items auto-grouped by task category
- Dutch tax support (BTW/KVK/IBAN) — easily adaptable to other jurisdictions
- Invoice lifecycle: draft → sent → paid → overdue
- Customizable HTML/CSS invoice template
- Freelancer profile with logo upload

**Pomodoro Timer**

- Integrated focus/break timer that tags tracked sessions
- Configurable durations and auto-start behavior
- Controls from tray menu, dashboard, browser extension, and mobile app
- OS-native notifications

**Calendar Sync**

- ICS feed for Tuta Calendar and any URL-subscribing calendar
- CalDAV sync (Radicale, Nextcloud, etc.)
- Google Calendar via OAuth2
- ICS file export

**Cloudflare Tunnel**

- Expose ICS feed and mobile API via stable custom domain (e.g. `time.yourdomain.com`)
- No firewall ports to open — uses Cloudflare's infrastructure
- 4-step setup wizard in the dashboard
- Ingress restricted to calendar feed and mobile API only

**Browser Extension**

- Chrome (Manifest V3) and Firefox
- Captures exact URL, page title, and content snippet for richer classification context
- Domain blocklist for banking, personal email, etc.
- Pomodoro controls in the popup
- Communicates only with localhost — never sends data externally

**Mobile Companion**

- Progressive Web App — works in mobile browser, installable to home screen
- View today's tracking, timeline, projects from your phone
- Start/stop Pomodoro remotely
- QR code pairing from the desktop dashboard
- Push notifications for Pomodoro timer events

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                   SYSTEM TRAY / MENU BAR                              │
│  Icon + Context Menu: Dashboard / Pause / Pomodoro / Settings / Quit  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND SERVICE                                  │
│                                                                        │
│  Capture Loop → Change Detection → OCR → Redaction → LLM → Sessions  │
│  (1s tick)       (phash + meta)    (CPU)  (4 levels)   (cloud)        │
│                                                                        │
│  + Pomodoro Timer (state machine, tags sessions)                      │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ writes
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         SQLite DATABASE                                │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ reads
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    LOCAL API SERVER (FastAPI)                           │
│                    127.0.0.1:19532                                     │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   Dashboard UI       Browser Extension     Mobile PWA
   (Angular 19+)      (Chrome/Firefox)      (via Cloudflare Tunnel)
```

Single process. Multiple threads. No containers, no cloud infrastructure, no accounts to create. Just a desktop app.

---

## Tech Stack

| Layer              | Technology                                                    |
| ------------------ | ------------------------------------------------------------- |
| Backend            | Python 3.12+, FastAPI, SQLite (WAL), PaddleOCR (CPU)          |
| Desktop            | pystray, mss, imagehash, Pillow                               |
| LLM                | httpx → Anthropic Messages API or OpenAI Chat Completions API |
| Dashboard          | Angular 19+ (standalone components, signals)                  |
| Browser Extension  | Chrome Manifest V3, Firefox WebExtensions                     |
| Mobile             | Angular PWA                                                   |
| Invoices & Reports | weasyprint (HTML/CSS → PDF)                                   |
| Calendar           | icalendar (RFC 5545), caldav (RFC 4791)                       |
| Tunnel             | Cloudflare Tunnel (cloudflared subprocess)                    |
| Packaging          | PyInstaller + NSIS (Win) / DMG (Mac) / AppImage (Linux)       |

---

## Quick Start (Development)

### Prerequisites

- Python 3.12+
- Node.js 20+ and npm
- Git

### Backend

```bash
git clone https://github.com/youruser/chronolens.git
cd chronolens

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

python -m chronolens
```

The system tray icon appears. The API starts on `http://localhost:19532`. On first run the database is created automatically.

### Dashboard

```bash
cd dashboard
npm install
ng serve --proxy-config proxy.conf.json
```

Open `http://localhost:4200`. The proxy forwards API calls to the backend.

### Browser Extension

```bash
cd browser-extension
```

Chrome: go to `chrome://extensions` → Enable developer mode → Load unpacked → select the `browser-extension/` folder.

Firefox: go to `about:debugging` → This Firefox → Load Temporary Add-on → select `manifest.firefox.json`.

### Mobile PWA

```bash
cd mobile
npm install
ng serve --port 4300
```

The PWA requires HTTPS for push notifications — enable the Cloudflare Tunnel for mobile access over the internet.

---

## Configuration

### LLM Setup

1. Open the dashboard → Privacy & LLM
2. Select provider (Claude or OpenAI)
3. Enter your API key
4. Click "Test" to verify
5. Optionally set a monthly budget cap

ChronoLens works without an LLM key — it will track your time but mark sessions as "unclassified" until you configure one.

### Privacy Levels

| Level                  | What's Redacted                                    | Classification Accuracy |
| ---------------------- | -------------------------------------------------- | ----------------------- |
| 1 — Minimal            | Secrets only (API keys, passwords, private keys)   | Highest                 |
| 2 — Standard (default) | + PII (emails, phones, IPs, credit cards, paths)   | High                    |
| 3 — Aggressive         | + Names, orgs, amounts, chat content, commands     | Medium                  |
| 4 — Maximum            | + Code blocks, all URLs, tabular data, quoted text | Lower                   |

You can add custom redaction patterns for client-specific terms (e.g. client names, project codenames, internal domains).

### Calendar Sync (Tuta)

1. Enable ICS Feed in the dashboard
2. Set up Cloudflare Tunnel for a stable URL
3. Copy the feed URL: `https://time.yourdomain.com/api/calendar/feed/{token}.ics`
4. In Tuta Calendar → "+" → "from URL" → paste

---

## Project Documentation

This project is built from a four-document specification:

| Document                                                         | Description                                                                                       |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| [`docs/specification.md`](docs/specification.md)                 | Complete build specification — architecture, database schema, API endpoints, all features         |
| [`docs/implementation-phases.md`](docs/implementation-phases.md) | 12 implementation phases with dependencies, acceptance criteria, and QA matrix                    |
| [`AGENTS.md`](AGENTS.md)                                         | Engineering workflow for AI coding agents — testing, commits, quality standards, ontology mapping |
| [`docs/engineering-ontology.md`](docs/engineering-ontology.md)   | Global Software Engineering Standards Ontology v3.0 — canonical reference for all standards used  |

If you're contributing or using an AI coding agent to build this, start with `AGENTS.md`.

---

## Project Structure

```
chronolens/
├── chronolens/              # Python backend
│   ├── capture/             # Screen capture, window info, idle detection, change detection
│   ├── ocr/                 # PaddleOCR wrapper
│   ├── redaction/           # 4-level privacy redaction engine
│   ├── classification/      # LLM clients (Claude, OpenAI), cache, cost tracking
│   ├── sessions/            # Session aggregation and tracking
│   ├── pomodoro/            # Pomodoro state machine
│   ├── calendar/            # CalDAV, ICS feed, Google Calendar sync
│   ├── cloudflare/          # Tunnel setup, management, binary download
│   ├── invoices/            # Invoice generation, PDF rendering, templates
│   ├── reports/             # Report aggregation, PDF/CSV export
│   ├── api/                 # FastAPI routes, WebSocket, auth
│   ├── db/                  # SQLite connection, schema, migrations
│   ├── crypto/              # Platform keyring integration
│   └── platform/            # Cross-platform autostart, notifications, paths
├── dashboard/               # Angular 19+ dashboard
├── browser-extension/       # Chrome MV3 + Firefox extension
├── mobile/                  # Angular PWA companion app
├── tests/                   # pytest: unit, integration, e2e
├── docs/                    # Specification, phases, ontology
├── assets/                  # Tray icons
├── installer/               # NSIS, DMG, AppImage build scripts
├── AGENTS.md                # AI agent engineering workflow
├── CHANGELOG.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md                # You are here
```

---

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=chronolens --cov-report=term-missing

# Unit tests only
pytest tests/unit/

# Specific area
pytest -k "redaction"
```

### Code Quality

```bash
# Format
black chronolens/ tests/

# Lint
ruff check chronolens/ tests/ --fix

# Type check
mypy chronolens/

# All of the above must pass before every commit
```

### Commit Convention

This project uses [conventional commits](https://www.conventionalcommits.org/):

```
feat(redaction): add Level 3 person name detection heuristic
fix(classification): handle empty OCR text without API call
test(invoices): add VAT calculation edge cases
docs(api): add OpenAPI descriptions to calendar endpoints
```

See `AGENTS.md` §3 for full commit discipline.

---

## Building for Release

### Windows

```bash
cd dashboard && ng build --configuration=production --output-path=../chronolens/static
cd ..
pyinstaller --onedir --noconsole --name ChronoLens chronolens/__main__.py
# Then run NSIS installer script
```

### macOS

```bash
# Same dashboard build, then:
pyinstaller --onedir --noconsole --name ChronoLens chronolens/__main__.py
# Package as .app → .dmg
```

### Linux

```bash
# Same dashboard build, then:
pyinstaller --onedir --noconsole --name ChronoLens chronolens/__main__.py
# Package as AppImage
```

---

## Performance

| Metric            | Target                              |
| ----------------- | ----------------------------------- |
| CPU (idle screen) | < 1%                                |
| CPU (active use)  | < 5%                                |
| RAM               | < 200 MB                            |
| VRAM              | 0 (everything CPU-only)             |
| LLM calls         | ~2-4/min (change detection + cache) |
| LLM monthly cost  | ~$1-5 (with caching)                |
| Dashboard load    | < 2 seconds                         |
| DB growth         | ~5-10 MB/month                      |

---

## Privacy & Security

- **All data stays local.** SQLite database on your machine. No cloud sync, no accounts, no telemetry.
- **Screenshots are never stored.** Captured in memory, OCR'd, then discarded.
- **No keylogging.** Input events are counted for idle detection only — keystrokes are never recorded.
- **Redaction before transmission.** OCR text is stripped of sensitive content before it reaches any LLM API.
- **API server is local-only.** FastAPI binds to `127.0.0.1` — nothing is accessible from the network.
- **Tunnel is scoped.** Cloudflare Tunnel exposes only the calendar feed and mobile API endpoints. The dashboard and main API are never exposed.
- **Credentials in OS keyring.** API keys stored via Windows DPAPI / macOS Keychain / Linux Secret Service — not in the database.

---

## Roadmap

Currently in development. See [`docs/implementation-phases.md`](docs/implementation-phases.md) for the full 12-phase plan.

**v1.0 scope is locked.** The following are explicitly out of scope for v1:

- Team/multi-user mode
- AI-powered auto-learning from corrections
- Tuta direct API integration
- Desktop widgets
- Project management tool integrations (Jira, Linear, Asana)
- Git commit correlation
- Screenshot archival
- Local LLM fallback (Ollama)

---

## Contributing

ChronoLens is built specification-first. Before contributing:

1. Read [`AGENTS.md`](AGENTS.md) for development practices
2. Read the relevant section of [`docs/specification.md`](docs/specification.md)
3. Check [`docs/implementation-phases.md`](docs/implementation-phases.md) for current phase status
4. Follow the commit convention and testing requirements

All contributions must include tests and pass `black`, `ruff`, `mypy`, and `pytest` before merge.

---

## License

[MIT](LICENSE)

---

## Acknowledgements

Built with [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), [FastAPI](https://fastapi.tiangolo.com/), [Angular](https://angular.dev/), and the [Anthropic](https://www.anthropic.com/) / [OpenAI](https://openai.com/) APIs.

Standards compliance guided by the [Global Software Engineering Standards Ontology](docs/engineering-ontology.md).
