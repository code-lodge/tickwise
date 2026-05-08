# ChronoLens — Implementation Phases

Companion document to `chronolens-build-spec-v3.md`. This breaks the full product into ordered implementation phases, each producing a testable, usable milestone. Phases are strictly sequential — later phases depend on earlier ones. Each phase lists exactly which spec sections it implements, which files it produces, its acceptance criteria, and estimated complexity.

**Primary development platform**: Build and test on your own OS first (Windows / Linux / macOS). Cross-platform abstraction layers are introduced in Phase 2, but full multi-platform validation happens in Phase 7.

---

## PHASE OVERVIEW

```
Phase 0 ─── Scaffolding & Foundation                 ██░░░░░░░░  ~1 week
Phase 1 ─── Core Tracking Loop (single monitor)      ████░░░░░░  ~2 weeks
Phase 2 ─── Cross-Platform Abstraction                █████░░░░░  ~1.5 weeks
Phase 3 ─── LLM Classification Pipeline              ██████░░░░  ~2 weeks
Phase 4 ─── Dashboard MVP                            ███████░░░  ~2.5 weeks
Phase 5 ─── Calendar, Tunnel & Reports                ████████░░  ~2 weeks
Phase 6 ─── Invoicing System                         ████████░░  ~1.5 weeks
Phase 7 ─── Pomodoro Timer                           █████████░  ~1 week
Phase 8 ─── Browser Extension                        █████████░  ~1.5 weeks
Phase 9 ─── Mobile Companion (PWA)                   █████████░  ~1.5 weeks
Phase 10 ── Multi-Monitor Support                    ██████████  ~1 week
Phase 11 ── Packaging, Polish & Release              ██████████  ~1.5 weeks
                                                                  ─────────
                                                     Total:      ~19 weeks
```

**Why this order?** The core tracking loop must exist before anything can classify it. Classification must exist before the dashboard has meaningful data to show. The dashboard must exist before calendar sync, reports, and invoices make sense (they need a way to review and correct data). Pomodoro, browser extension, and mobile are additive features that enhance the core but don't block it. Multi-monitor is a refinement of the capture loop that should be done after the single-monitor pipeline is proven solid. Packaging is last because it's mechanical and shouldn't happen until the product is feature-complete.

---

## PHASE 0 — SCAFFOLDING & FOUNDATION

**Goal**: Project skeleton, database layer, configuration system, and an API server that starts up and responds to health checks. Nothing captures yet, nothing classifies. This is the skeleton that everything attaches to.

### Spec Sections Implemented

| Section                  | Coverage                                                            |
| ------------------------ | ------------------------------------------------------------------- |
| §2 Architecture Overview | Process architecture, thread model (stubs only)                     |
| §6 Database              | Full schema creation, WAL mode, migrations framework                |
| §7 API Server            | FastAPI app init, uvicorn thread, `GET /api/status`                 |
| §12 System Tray          | Basic tray icon that launches, shows "Not tracking", Quit           |
| §16 Directory Structure  | Full directory scaffold (empty modules with docstrings)             |
| §17 Tech Stack           | `requirements.txt`, `pyproject.toml`                                |
| §18 Cross-Platform       | `platform/paths.py` — data directory resolution for current OS only |

### Files Produced

```
chronolens/
├── chronolens/
│   ├── __init__.py
│   ├── __main__.py                  # Entry point: init DB → start uvicorn → start tray
│   ├── app.py                       # FastAPI app with /api/status
│   ├── tray.py                      # pystray icon: "Not tracking" + Quit
│   ├── config.py                    # Platform paths, defaults, version string
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py            # get_db(), thread-local connections, WAL pragma
│   │   ├── schema.py                # CREATE TABLE statements from §6, migration versioning
│   │   └── models.py                # Pydantic models for all tables
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_settings.py       # GET/PUT /api/settings
│   │   └── websocket.py             # /ws/live stub (connect, no messages yet)
│   │
│   ├── platform/
│   │   └── paths.py                 # data_dir(), config_dir() for current OS
│   │
│   ├── capture/                     # empty __init__.py files as stubs
│   ├── ocr/
│   ├── redaction/
│   ├── classification/
│   ├── sessions/
│   ├── pomodoro/
│   ├── calendar/
│   ├── cloudflare/
│   ├── invoices/
│   ├── reports/
│   └── crypto/
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Acceptance Criteria

- [ ] `python -m chronolens` starts without errors
- [ ] System tray icon appears with "Quit" menu item
- [ ] SQLite database created at correct platform path with all tables from §6
- [ ] `GET http://localhost:19532/api/status` returns `{"status": "ok", "version": "0.1.0", "db_size_bytes": ...}`
- [ ] `GET /api/settings` returns the default settings from the settings table
- [ ] `PUT /api/settings/idle_split_threshold` with `{"value": "600"}` persists to database
- [ ] WebSocket connection to `ws://localhost:19532/ws/live` succeeds (no messages yet)
- [ ] Quitting from tray cleanly shuts down uvicorn and exits the process

### Technical Notes

- Use `threading.Thread(daemon=True)` for the uvicorn thread
- The tray icon thread is the main thread (pystray requirement on macOS)
- Database migrations: use a `schema_version` table with integer version. On startup, run any pending migrations in order. This is critical for later phases that add columns.

---

## PHASE 1 — CORE TRACKING LOOP (SINGLE MONITOR)

**Goal**: The capture loop runs, takes screenshots from the primary monitor, detects screen changes, extracts text via OCR, and stores raw activities in the database. No classification yet — activities are stored as `source = "pending_classification"`. The session tracker aggregates activities into sessions. The system tray shows live status.

### Spec Sections Implemented

| Section                   | Coverage                                              |
| ------------------------- | ----------------------------------------------------- |
| §3.1 Capture Loop         | Full implementation for primary monitor only          |
| §3.2 Change Detection     | Perceptual hash + window title/process diff           |
| §3.3 OCR Text Extraction  | PaddleOCR CPU-only integration                        |
| §3.4 Classification Queue | Queue infrastructure (producer side only)             |
| §12 System Tray           | Live status: tracking/paused/idle, today's total time |
| §19 Performance Budget    | Validate CPU < 5% during active screen changes        |

### Implementation Details

**Capture loop thread**: 1-second tick using `threading.Event.wait(1.0)`. Each tick:

1. Get active window title + process name (platform-specific, just implement for your current OS here — cross-platform comes in Phase 2)
2. Capture primary monitor screenshot via `mss`
3. Check idle duration — if above `idle_split_threshold`, pause capture
4. Run change detection:
   - Fast path: title or process changed → flag as changed
   - Slow path: compute dhash, compare hamming distance to threshold
5. If changed: run PaddleOCR on downscaled screenshot, push to classification queue
6. If unchanged: call `extend_current_session()`

**Session tracker thread**: consumes completed activities and merges them into sessions.

- Group consecutive activities with same (process, window_title) into sessions
- Respect `idle_merge_threshold` (default 120s) — gaps smaller than this are merged
- Respect `min_session_duration` (default 10s) — discard shorter sessions
- Write completed sessions to the `sessions` table

**Tray updates**:

- Replace "Not tracking" with live info: process name, duration counter
- Add "Pause Tracking" / "Resume Tracking" toggle
- Add today's total tracked time

### Files Produced

```
chronolens/capture/
├── loop.py                          # Main capture loop thread
├── screenshot.py                    # mss wrapper, primary monitor only
├── window_info.py                   # Dispatcher (imports current-platform module)
├── window_info_{platform}.py        # For your current OS only
├── idle_detector.py                 # Dispatcher
├── idle_detector_{platform}.py      # For your current OS only
├── change_detector.py               # dhash comparison

chronolens/ocr/
├── extractor.py                     # PaddleOCR wrapper with downscaling

chronolens/sessions/
├── tracker.py                       # Session aggregation logic

chronolens/api/
├── routes_sessions.py               # GET /api/sessions, GET /api/sessions/{id}
```

Updated files: `__main__.py` (launch capture + session threads), `tray.py` (live status), `app.py` (register session routes)

### Acceptance Criteria

- [ ] Capture loop runs at ~1 Hz, logs window title + process each tick
- [ ] Screenshot captured from primary monitor, held in memory only (verify no disk writes)
- [ ] PaddleOCR extracts text from screenshots, logs sample output
- [ ] Change detection skips OCR when screen is unchanged (verify via log output: "no change, skipping OCR")
- [ ] Activities table populates with `source = "pending_classification"`, `window_title`, `process_name`, `ocr_snippet`
- [ ] Sessions table populates with aggregated time blocks (start_time, end_time, duration_seconds)
- [ ] Idle detection works: after 5 minutes of no input, capture pauses; resumes on input
- [ ] `GET /api/sessions?from=2025-05-01&to=2025-05-08` returns session data
- [ ] Tray icon shows current process name and running duration
- [ ] CPU usage stays below 5% during normal use (verify with task manager / top)
- [ ] Pausing via tray menu stops the capture loop; resuming restarts it

---

## PHASE 2 — CROSS-PLATFORM ABSTRACTION

**Goal**: Implement platform-specific modules for all three OSes. After this phase, ChronoLens runs on Windows, macOS, and Linux (single-monitor).

### Spec Sections Implemented

| Section                     | Coverage                            |
| --------------------------- | ----------------------------------- |
| §18 Cross-Platform          | All platform abstraction tables     |
| §12 System Tray — Autostart | Per-platform autostart registration |
| §20 Security — Credentials  | Platform keyring integration        |

### Implementation Details

For each of these subsystems, create the platform-dispatched modules for the two OSes you haven't done yet:

1. **Window info**: `window_info_windows.py`, `window_info_macos.py`, `window_info_linux.py`
2. **Idle detection**: `idle_detector_windows.py`, `idle_detector_macos.py`, `idle_detector_linux.py`
3. **Autostart**: `autostart_windows.py` (registry), `autostart_macos.py` (LaunchAgent), `autostart_linux.py` (XDG .desktop)
4. **Credential storage**: `keyring_windows.py` (DPAPI), `keyring_macos.py` (Keychain), `keyring_linux.py` (Secret Service)
5. **Notifications**: `notifications.py` (cross-platform via `plyer`, with platform fallbacks)

Each module exposes the same interface — the dispatcher module does `platform.system()` detection and re-exports.

### Files Produced

```
chronolens/capture/
├── window_info_windows.py           # win32gui
├── window_info_macos.py             # NSWorkspace + Accessibility
├── window_info_linux.py             # xdotool / python-xlib / sway IPC

├── idle_detector_windows.py         # GetLastInputInfo
├── idle_detector_macos.py           # IOKit HID
├── idle_detector_linux.py           # XScreenSaver / D-Bus

chronolens/platform/
├── autostart.py                     # Dispatcher
├── autostart_windows.py             # Registry
├── autostart_macos.py               # LaunchAgent plist
├── autostart_linux.py               # XDG .desktop
├── notifications.py                 # Cross-platform (plyer + fallbacks)

chronolens/crypto/
├── keyring.py                       # Dispatcher + fallback to encrypted file
├── keyring_windows.py               # DPAPI
├── keyring_macos.py                 # macOS Keychain
├── keyring_linux.py                 # Secret Service D-Bus
```

### Acceptance Criteria

- [ ] Capture loop runs correctly on all three platforms (test with VM or CI)
- [ ] Window title + process name correctly detected on each platform
- [ ] Idle detection correctly pauses capture after threshold on each platform
- [ ] Autostart registers correctly on each platform (verify entry exists after enable)
- [ ] Credentials stored securely: `keyring.store("test_key", "test_value")` → `keyring.retrieve("test_key")` returns `"test_value"` on each platform
- [ ] Notification fires a visible OS notification on each platform

---

## PHASE 3 — LLM CLASSIFICATION PIPELINE

**Goal**: OCR text is redacted according to privacy level, sent to Claude or OpenAI API, and the response is parsed into project + task classifications. Activities move from `pending_classification` to `llm`. Classification cache prevents redundant API calls.

### Spec Sections Implemented

| Section                  | Coverage                                                                        |
| ------------------------ | ------------------------------------------------------------------------------- |
| §4 Text Redaction Engine | Full implementation — all 4 levels + custom rules                               |
| §5 LLM Classification    | Complete: Claude client, OpenAI client, prompts, cache, cost tracking, fallback |
| §7 API Server            | LLM config, redaction, and LLM usage endpoints                                  |

### Implementation Order (within this phase)

This phase has internal dependencies — build in this order:

**Step 3a — Redaction Engine**

```
chronolens/redaction/
├── engine.py                        # RedactionEngine class, orchestrates levels + custom
├── levels.py                        # Level 1-4 definitions: which categories apply at each level
├── patterns.py                      # All regex patterns by category, organized as dict
├── custom_rules.py                  # Load custom_redaction_rules from DB, apply
```

Build the `RedactionEngine` first because everything else depends on it. Test it in isolation with sample text strings before connecting it to the pipeline.

Test harness:

```python
engine = RedactionEngine(privacy_level=2, custom_rules=[])
result = engine.redact("My email is john@example.com and API key is sk-abc123456789abcdef")
assert "[EMAIL]" in result.redacted_text
assert "[API_KEY]" in result.redacted_text
assert "john@example.com" not in result.redacted_text
```

Write thorough unit tests for every category at every level. Edge cases: overlapping patterns, Unicode text, empty input, very long input (>10KB).

**Step 3b — LLM Clients**

```
chronolens/classification/
├── llm_client.py                    # Abstract base: classify(context) → ClassificationResult
├── claude_client.py                 # Anthropic Messages API via httpx
├── openai_client.py                 # OpenAI Chat Completions API via httpx
├── prompts.py                       # SYSTEM_PROMPT, build_user_prompt()
```

Implement the abstract client interface, then both providers. Test each with a real API key (use a sample context). Verify JSON response parsing, error handling for rate limits, timeouts, malformed responses.

**Step 3c — Classification Pipeline**

```
chronolens/classification/
├── pipeline.py                      # Orchestrator: queue consumer → redact → cache check → LLM → store
├── cache.py                         # Classification cache: SHA-256 key, TTL, hit tracking
├── cost_tracker.py                  # Token estimation, cost calculation, budget enforcement
```

Connect everything: the classification queue consumer thread pulls items, runs redaction, checks cache, calls LLM if miss, stores result.

**Step 3d — API Endpoints**

```
chronolens/api/
├── routes_llm.py                    # GET/PUT /api/llm/config, GET /api/llm/usage, POST /api/llm/test
├── routes_redaction.py              # GET/PUT /api/redaction/level, CRUD custom rules, POST preview
```

### Acceptance Criteria

- [ ] **Redaction Level 1**: API keys, passwords, private keys, JWTs, connection strings all replaced with placeholders
- [ ] **Redaction Level 2**: Adds emails, phone numbers, IPs, IBANs, credit cards, file paths, addresses
- [ ] **Redaction Level 3**: Adds person names (heuristic), org names, amounts, chat content, shell commands
- [ ] **Redaction Level 4**: Bulk code blocks, all URLs removed, long numbers, proper nouns, tabular data
- [ ] Custom rules apply regardless of level
- [ ] `POST /api/redaction/preview` with `{"text": "...", "level": 2}` returns correctly redacted output
- [ ] Claude API: sends redacted context, receives valid `{project, task, confidence, reasoning}` JSON
- [ ] OpenAI API: same behavior with GPT model
- [ ] Classification cache: second identical request returns cached result (verify `cache_hit = true` in usage log)
- [ ] Cost tracking: `llm_usage_log` records input/output tokens + estimated cost per call
- [ ] Budget enforcement: when `monthly_spent >= monthly_budget`, new activities marked as `pending_classification` instead of calling LLM, tray notification fires
- [ ] Fallback: API timeout or error → activity stored as `pending_classification`, no crash
- [ ] `POST /api/llm/test` runs a sample through the full pipeline and returns the classification result
- [ ] Activities in database now have `project_id`, `task_category`, `confidence`, `source = "llm"`

---

## PHASE 4 — DASHBOARD MVP

**Goal**: Angular dashboard served by FastAPI. The user can see live tracking, browse the timeline, manage projects, review and reclassify sessions, and configure privacy + LLM settings.

### Spec Sections Implemented

| Section             | Coverage                                                           |
| ------------------- | ------------------------------------------------------------------ |
| §7 API Server       | Projects CRUD, sessions edit/split/merge, status endpoint full     |
| §13.1 Live View     | Full page                                                          |
| §13.2 Timeline      | Full page                                                          |
| §13.3 Projects      | Full page                                                          |
| §13.9 Privacy & LLM | Full page                                                          |
| §13.10 Settings     | Full page (except multi-monitor and mobile pairing — later phases) |
| §12 System Tray     | "Open Dashboard" opens browser                                     |

### Implementation Order

**Step 4a — Angular scaffold + API service**

```bash
cd dashboard
ng new chronolens-dashboard --standalone --style=css --routing --skip-tests
```

Set up: `app.routes.ts` with lazy-loaded routes, `api.service.ts` with `HttpClient` base, `websocket.service.ts`, proxy config for development.

**Step 4b — Settings page** (`/settings`)

Start here because it's the simplest page and validates the full round-trip (Angular → API → DB → API → Angular). Implement tracking settings, OCR toggle, autostart, billing defaults.

**Step 4c — Privacy & LLM page** (`/privacy`)

Implements: privacy level selector, redaction preview tool, custom rules CRUD, LLM provider config, API key input, model selector, usage dashboard with Chart.js, monthly budget display.

**Step 4d — Projects page** (`/projects`)

Project list with color badges, hourly rate, client assignment, active toggle. Project detail with hours summary and session list. CRUD with soft delete.

**Step 4e — Live View** (`/`)

WebSocket connection for real-time updates. Current activity card, today's timeline bar, today's summary stats, unclassified sessions alert.

**Step 4f — Timeline page** (`/timeline`)

Day/week/month view. Clickable sessions with detail panel. Edit project assignment, task category, notes. Split and merge operations. Filter and bulk actions.

**Step 4g — Build integration**

`ng build --configuration=production --output-path=../chronolens/static` → FastAPI serves from `static/` directory. Update `__main__.py` to open `http://localhost:19532` in default browser when tray icon "Open Dashboard" is clicked.

### Files Produced

```
dashboard/
├── src/app/
│   ├── app.component.ts
│   ├── app.routes.ts
│   ├── services/
│   │   ├── api.service.ts
│   │   ├── websocket.service.ts
│   │   └── settings.service.ts
│   ├── models/
│   │   ├── session.model.ts
│   │   ├── project.model.ts
│   │   └── settings.model.ts
│   ├── pages/
│   │   ├── live/
│   │   ├── timeline/
│   │   ├── projects/
│   │   ├── privacy/
│   │   └── settings/
│   └── components/
│       ├── session-bar/
│       ├── time-chart/
│       ├── project-badge/
│       ├── date-range-picker/
│       ├── redaction-preview/
│       └── llm-usage-chart/
```

Backend additions:

```
chronolens/api/
├── routes_projects.py               # Full CRUD
├── routes_sessions.py               # Add PUT, split, merge
```

### Acceptance Criteria

- [ ] `ng serve` with proxy to localhost:19532 shows working dashboard
- [ ] Live View shows current activity updating in real-time via WebSocket
- [ ] Timeline shows sessions grouped by day with correct colors and durations
- [ ] Click a session → detail panel → change project → saves correctly
- [ ] Split a session at a timestamp → creates two sessions
- [ ] Merge two sessions → creates one combined session
- [ ] Projects page: create project with name, client, rate, color → appears in project list
- [ ] Privacy page: change level → redaction preview updates → LLM uses new level
- [ ] Privacy page: add custom rule → immediately applied to new classifications
- [ ] LLM page: enter API key → test → shows classification result
- [ ] LLM usage chart shows daily calls and costs
- [ ] Settings changes persist across app restart
- [ ] Production build serves from FastAPI static files
- [ ] "Open Dashboard" from tray opens browser to correct URL

---

## PHASE 5 — CALENDAR SYNC, CLOUDFLARE TUNNEL & REPORTS

**Goal**: Sessions sync to external calendars. The ICS feed is exposed via Cloudflare Tunnel with a stable custom domain. Report generation with export to PDF/CSV/JSON.

### Spec Sections Implemented

| Section                     | Coverage                                                        |
| --------------------------- | --------------------------------------------------------------- |
| §8 Calendar Sync & ICS Feed | Full: CalDAV, ICS feed, ICS export, Google Calendar             |
| §9 Cloudflare Tunnel        | Full: API client, tunnel manager, setup wizard, binary download |
| §10 Reports (non-invoice)   | Report types, export formats (PDF, CSV, JSON)                   |
| §7 API Server               | Calendar, Cloudflare, and report endpoints                      |
| §13.5 Reports page          | Full                                                            |
| §13.7 Calendar page         | Full                                                            |

### Implementation Order

**Step 5a — ICS feed generation**

Build `ics_feed.py` using the `icalendar` library. Generate RFC 5545 VEVENT entries from sessions. Implement `GET /api/calendar/feed/{token}.ics`.

**Step 5b — ICS export**

Simple: generate `.ics` file and return as download. `POST /api/reports/export` with `format=ics`.

**Step 5c — CalDAV provider**

Implement `CalDAVProvider` using the `caldav` Python library. Bidirectional sync: push new sessions as events, update modified ones.

**Step 5d — Google Calendar provider**

OAuth2 flow via browser popup → Google Calendar API v3. Push sessions as events.

**Step 5e — Calendar sync scheduler**

APScheduler with configurable interval. Runs sync for all active providers.

**Step 5f — Cloudflare Tunnel**

1. `binary.py`: auto-download `cloudflared` for current platform, verify checksum
2. `api_client.py`: Cloudflare API wrapper (create tunnel, create CNAME, manage ingress)
3. `tunnel_manager.py`: start/stop `cloudflared` subprocess, health monitoring
4. `setup.py`: 4-step wizard logic
5. API routes: `routes_cloudflare.py`

**Step 5g — Report generation**

`reports/generator.py`: aggregate session data into report structures (summary, billing, activity, detailed, productivity). Export via `pdf_export.py` (weasyprint) and `csv_export.py`.

**Step 5h — Dashboard pages**

Calendar page: ICS feed config, Cloudflare setup wizard UI, provider management, Tuta instructions.  
Reports page: type selector, date range, project filter, inline charts, export buttons.

### Files Produced

```
chronolens/calendar/
├── provider.py, caldav_provider.py, ics_feed.py, ics_export.py
├── google_provider.py, sync_service.py

chronolens/cloudflare/
├── api_client.py, tunnel_manager.py, setup.py, binary.py

chronolens/reports/
├── generator.py, pdf_export.py, csv_export.py

chronolens/api/
├── routes_calendar.py, routes_cloudflare.py, routes_reports.py

dashboard/src/app/pages/
├── calendar/, reports/

dashboard/src/app/components/
├── tunnel-status/
```

### Acceptance Criteria

- [ ] ICS feed URL returns valid iCalendar document (validate with `icalendar` library parse)
- [ ] Tuta Calendar subscribes to ICS feed URL and shows sessions (manual test with Tuta)
- [ ] CalDAV sync pushes sessions to a CalDAV server (test with Radicale or Nextcloud)
- [ ] Google Calendar sync creates events (test with real Google account)
- [ ] Cloudflare Tunnel: full wizard → tunnel created → CNAME set → `cloudflared` running → ICS feed accessible from internet
- [ ] Cloudflare deactivate → tunnel stopped → CNAME removed
- [ ] Reports: Time Summary grouped by week shows correct hours per project
- [ ] Reports: PDF export produces readable document with correct data
- [ ] Reports: CSV export has correct headers and data
- [ ] Dashboard Calendar page: toggle ICS feed on/off, see Cloudflare status, run manual sync

---

## PHASE 6 — INVOICING SYSTEM

**Goal**: Generate professional PDF invoices from tracked time. Manage freelancer profile, client profiles, invoice lifecycle (draft → sent → paid).

### Spec Sections Implemented

| Section                | Coverage                                                                                                        |
| ---------------------- | --------------------------------------------------------------------------------------------------------------- |
| §10 Invoice Generation | Full: creation wizard, line items, PDF rendering, status lifecycle                                              |
| §6 Database            | `invoices`, `invoice_line_items`, `freelancer_profile`, `clients` tables (already created in Phase 0, now used) |
| §7 API Server          | Invoice + client + profile endpoints                                                                            |
| §13.4 Clients page     | Full                                                                                                            |
| §13.6 Invoices page    | Full                                                                                                            |

### Implementation Order

**Step 6a — Freelancer profile API + UI**

`routes_profile.py`: GET/PUT profile, POST logo upload. Dashboard settings page gets a "Business Profile" link/section.

**Step 6b — Client management**

`routes_clients.py`: full CRUD. Dashboard clients page: list, create, edit.

**Step 6c — Invoice generator**

`invoices/generator.py`: given project ID + date range, query sessions, group by task category, calculate line items + totals + VAT.

**Step 6d — Invoice PDF renderer**

`invoices/pdf_renderer.py` + `templates/default.html` + `templates/default.css`. Uses weasyprint. Produces the layout from §10 of the spec: logo, from/to blocks, line item table, subtotal/VAT/total, payment details.

**Step 6e — Invoice API**

`routes_invoices.py`: CRUD, generate-pdf, mark-sent, mark-paid, download PDF.

**Step 6f — Dashboard invoices page**

Invoice list with status badges. "Create Invoice" wizard: project + date range → auto-populated line items → edit → save draft. Invoice detail: preview, PDF download, status actions.

### Files Produced

```
chronolens/invoices/
├── generator.py
├── pdf_renderer.py
├── templates/
│   ├── default.html
│   └── default.css

chronolens/api/
├── routes_invoices.py
├── routes_clients.py
├── routes_profile.py

dashboard/src/app/pages/
├── invoices/, clients/

dashboard/src/app/components/
├── invoice-preview/

dashboard/src/app/models/
├── invoice.model.ts, client.model.ts
```

### Acceptance Criteria

- [ ] Freelancer profile: save name, address, KVK, BTW, IBAN → persists and pre-fills invoices
- [ ] Logo upload → appears in generated PDF header
- [ ] Client CRUD: create client → appears in client list, linked to projects
- [ ] "Create Invoice" for project with tracked time → auto-generates line items with correct hours
- [ ] Line items editable: change description, hours, rate. Add custom line items.
- [ ] Invoice PDF: professional layout matching §10 mockup, correct calculations
- [ ] VAT calculation: 21% default, configurable per invoice
- [ ] Invoice number auto-increment: `INV-2026-001`, `INV-2026-002`, etc.
- [ ] Status lifecycle: draft → mark sent (records `sent_at`) → mark paid (records `paid_at`)
- [ ] Download PDF from invoice detail page

---

## PHASE 7 — POMODORO TIMER

**Goal**: Integrated Pomodoro timer that tags tracked sessions. Controls from tray, dashboard, and (later) browser extension and mobile.

### Spec Sections Implemented

| Section             | Coverage                                                      |
| ------------------- | ------------------------------------------------------------- |
| §11 Pomodoro Timer  | Full: state machine, configuration, integration with tracking |
| §7 API Server       | Pomodoro endpoints                                            |
| §12 System Tray     | Pomodoro status in tray, context menu controls                |
| §13.1 Live View     | Pomodoro widget                                               |
| §13.8 Pomodoro page | Full                                                          |

### Implementation Details

**Pomodoro timer thread**: runs independently, manages the state machine:

```
State: IDLE | FOCUS | SHORT_BREAK | LONG_BREAK
Transitions:
  IDLE → FOCUS (user starts)
  FOCUS → SHORT_BREAK (timer ends, auto if configured)
  FOCUS → LONG_BREAK (after N focus periods)
  SHORT_BREAK → FOCUS (timer ends, auto if configured)
  LONG_BREAK → FOCUS (timer ends, auto if configured)
  Any → IDLE (user stops)
```

The timer ticks every second, decrementing remaining time. When a state transition occurs:

- Write to `pomodoro_sessions` table
- Fire OS notification
- Send WebSocket message (for dashboard real-time update)
- Update tray icon state

**Integration with tracking**: during FOCUS, all activities get `pomodoro_session_id` set. When a session overlaps with a focus period, increment `pomodoro_count`.

### Files Produced

```
chronolens/pomodoro/
├── timer.py                         # State machine, timer thread

chronolens/api/
├── routes_pomodoro.py               # start, stop, status, history, settings

dashboard/src/app/pages/
├── pomodoro/

dashboard/src/app/components/
├── pomodoro-widget/                 # Reused on Live View and Pomodoro page

dashboard/src/app/models/
├── pomodoro.model.ts
```

### Acceptance Criteria

- [ ] Start focus from tray → timer runs, tray icon changes to focus state
- [ ] Timer counts down correctly (verify with wall clock)
- [ ] Focus ends → notification fires → auto-starts short break (if configured)
- [ ] After 4 focus periods → long break instead of short break
- [ ] Activities during focus have `pomodoro_session_id` set
- [ ] Dashboard pomodoro page: large timer, start/stop, today's history
- [ ] Dashboard live view: pomodoro widget shows current state
- [ ] WebSocket sends pomodoro tick events (dashboard updates in real-time)
- [ ] Pomodoro settings (durations, auto-start) configurable and persisted
- [ ] Stopping mid-focus marks session as `completed = false`

---

## PHASE 8 — BROWSER EXTENSION

**Goal**: Chrome and Firefox extensions that capture URL, tab title, and content snippets. Send to ChronoLens via WebSocket. Extension popup shows status and Pomodoro controls.

### Spec Sections Implemented

| Section               | Coverage                                      |
| --------------------- | --------------------------------------------- |
| §14 Browser Extension | Full                                          |
| §3.1 Capture Loop     | Browser context integration into capture loop |
| §7 API Server         | `/ws/browser-extension` WebSocket endpoint    |

### Implementation Details

**Backend**: add `/ws/browser-extension` WebSocket handler. On message, store the latest browser context. The capture loop checks this context alongside window info.

Modify `capture/browser_bridge.py`: store latest browser context with timestamp. If stale (>5s old), discard. The capture loop's change detection adds URL change as a fast-path trigger.

**Extension**: Chrome Manifest V3 service worker + content script. Firefox version with compatible manifest.

### Files Produced

```
browser-extension/
├── manifest.json                    # Chrome MV3
├── manifest.firefox.json            # Firefox variant
├── background.js                    # Service worker: WebSocket, tab events
├── content.js                       # Content script: extract page text
├── popup/
│   ├── popup.html, popup.js, popup.css
├── options/
│   ├── options.html, options.js, options.css
└── icons/
    ├── icon-16.png, icon-48.png, icon-128.png

chronolens/capture/
├── browser_bridge.py                # WebSocket message handler, context storage
```

### Acceptance Criteria

- [ ] Chrome extension loads unpacked, connects WebSocket to localhost:19532
- [ ] Tab switch → sends URL + title + content snippet to ChronoLens
- [ ] URL change within tab → sends updated context
- [ ] LLM classification uses browser URL when available (verify in `llm_reasoning`)
- [ ] Extension popup: shows connection status (green/red), current classification
- [ ] Extension popup: Pomodoro start/stop controls work
- [ ] Excluded domains: add `mail.google.com` → extension stops sending data for Gmail tabs
- [ ] Content capture toggle: disable → only URL + title sent, no snippets
- [ ] Firefox extension works identically (test with Firefox Developer Edition)
- [ ] No extension → app still works fine (browser_bridge returns None gracefully)

---

## PHASE 9 — MOBILE COMPANION (PWA)

**Goal**: Progressive Web App for viewing tracking data and controlling the Pomodoro timer from a phone. Requires Cloudflare Tunnel (Phase 5) for connectivity.

### Spec Sections Implemented

| Section                  | Coverage                                  |
| ------------------------ | ----------------------------------------- |
| §15 Mobile Companion App | Full PWA implementation                   |
| §7 API Server            | Mobile API endpoints + bearer auth        |
| §9 Cloudflare Tunnel     | Update ingress to include `/api/mobile/*` |

### Implementation Details

**Backend**: `routes_mobile.py` with all mobile endpoints. `auth.py` middleware for bearer token validation. QR code generation endpoint (render QR containing `chronolens://{hostname}/api/mobile?token={token}`).

**Tunnel update**: when mobile access is enabled, update Cloudflare Tunnel ingress to include `/api/mobile/*` path.

**PWA**: Angular project with `@angular/pwa`. Screens: pairing (QR scan or manual token entry), home (today's summary + current activity + Pomodoro), timeline, projects, Pomodoro timer. Service worker for offline shell + web push notifications.

### Files Produced

```
mobile/
├── src/app/
│   ├── pages/
│   │   ├── pairing/                 # QR scan / token entry
│   │   ├── home/                    # Today + current activity + pomodoro
│   │   ├── timeline/                # Daily session list
│   │   ├── projects/                # Project list + detail
│   │   └── pomodoro/                # Large timer + controls
│   ├── services/
│   │   └── api.service.ts           # HTTP with bearer token
│   ├── models/
│   ├── manifest.webmanifest
│   └── service-worker.js

chronolens/api/
├── routes_mobile.py
├── auth.py                          # Bearer token middleware

dashboard/src/app/components/
├── qr-code/                         # QR code display for mobile pairing

dashboard/src/app/pages/settings/
└── (add Mobile section with "Pair Device" button + QR display)
```

### Acceptance Criteria

- [ ] Dashboard Settings → Mobile → "Pair Device" → shows QR code
- [ ] Phone scans QR → PWA opens → token stored → shows today's summary
- [ ] Mobile home: current activity updates (polling every 5s)
- [ ] Mobile timeline: shows today's sessions correctly
- [ ] Mobile Pomodoro: start/stop focus → updates on desktop in real-time
- [ ] Pomodoro notification: web push fires when timer ends (HTTPS required → Cloudflare Tunnel must be active)
- [ ] Bearer token auth: requests without valid token → 401 Unauthorized
- [ ] PWA installable: "Add to Home Screen" works on iOS Safari and Android Chrome
- [ ] Offline: PWA shell loads even without network (data requires connection)
- [ ] Multiple devices: pair second phone → both work independently

---

## PHASE 10 — MULTI-MONITOR SUPPORT

**Goal**: Capture all connected monitors, classify the focused monitor, hash-track the others for instant classification on focus switch.

### Spec Sections Implemented

| Section                           | Coverage                   |
| --------------------------------- | -------------------------- |
| §3.1 Capture Loop — Multi-Monitor | Full multi-monitor capture |
| §13.10 Settings                   | Monitor selection UI       |

### Implementation Details

Modify `capture/screenshot.py`:

- Capture all monitors via `mss` each tick (already supports this natively)
- Return dict: `{monitor_index: screenshot_data}`

Modify `capture/loop.py`:

- Determine focused monitor by comparing active window position to monitor bounds
- Run OCR + classification only on focused monitor's screenshot
- Store perceptual hashes for all monitors
- On focus switch to another monitor: the screenshot is already captured, immediately classify it

Modify `capture/window_info_{platform}.py`:

- Add `get_focused_monitor()` function per platform (see §18 table)

Add multi-monitor settings to dashboard Settings page:

- List detected monitors with resolution
- Toggle which monitors to capture (default: all)
- Set primary monitor preference

### Files Modified

```
chronolens/capture/screenshot.py      # Multi-monitor capture
chronolens/capture/loop.py            # Focused monitor routing, hash tracking for all
chronolens/capture/window_info_*.py   # get_focused_monitor() per platform

dashboard/src/app/pages/settings/     # Multi-monitor settings section
```

### Acceptance Criteria

- [ ] With 2+ monitors: all monitors captured each tick (verify via screenshot count in logs)
- [ ] Only focused monitor's screenshot sent to OCR + LLM
- [ ] Switch focus to secondary monitor → classification happens within 1 tick (no lag)
- [ ] `activities.monitor_index` records correct monitor for each activity
- [ ] Settings page shows detected monitors with resolution info
- [ ] Disabling a monitor → capture skips it

---

## PHASE 11 — PACKAGING, POLISH & RELEASE

**Goal**: Build installable packages for all platforms. Browser extension packaged for store submission. Final QA pass across all features and platforms.

### Spec Sections Implemented

| Section                            | Coverage                                     |
| ---------------------------------- | -------------------------------------------- |
| §21 Build & Packaging              | Full: PyInstaller, NSIS, DMG, AppImage       |
| §14 Browser Extension — Publishing | Chrome Web Store + Firefox Add-ons packaging |
| §19 Performance Budget             | Full validation pass                         |
| §20 Security Considerations        | Full audit                                   |

### Deliverables

**Windows**:

- PyInstaller `--onedir --noconsole` → `ChronoLens/` directory
- NSIS installer: `chronolens-setup-{version}.exe`
  - Install location, start menu shortcut, uninstaller
  - Bundles PaddleOCR models + cloudflared

**macOS**:

- PyInstaller → `.app` bundle
- DMG: `ChronoLens-{version}.dmg`
  - Drag to Applications, code signing (if dev cert available)

**Linux**:

- PyInstaller → AppImage: `ChronoLens-{version}.AppImage`
  - Self-contained, `chmod +x`, run from anywhere

**Browser Extension**:

- Chrome: `.zip` package for Chrome Web Store submission
- Firefox: `.xpi` package for Firefox Add-ons submission

**Mobile PWA**:

- Built into `chronolens/static/mobile/` — no separate packaging needed

### Polish Checklist

- [ ] First-run experience: no API key configured → show setup wizard (pick provider, enter key, test, set privacy level)
- [ ] Empty states: no projects → "Create your first project" prompt
- [ ] Error messages: human-readable, actionable (not raw stack traces)
- [ ] Loading states: skeleton screens for dashboard pages
- [ ] Dark mode: respect system preference via `prefers-color-scheme`
- [ ] Keyboard shortcuts: `Ctrl+P` toggle Pomodoro, `Ctrl+D` open dashboard
- [ ] Database backup: export all data as JSON from Settings

### QA Matrix

Run full test pass on each platform:

| Test                                  | Win | Mac | Linux |
| ------------------------------------- | --- | --- | ----- |
| Clean install from package            |     |     |       |
| Capture loop starts, detects activity |     |     |       |
| OCR extracts text correctly           |     |     |       |
| Redaction all 4 levels                |     |     |       |
| LLM classification (Claude)           |     |     |       |
| LLM classification (OpenAI)           |     |     |       |
| Dashboard opens, shows live data      |     |     |       |
| Timeline: view, edit, split, merge    |     |     |       |
| Projects CRUD                         |     |     |       |
| Clients CRUD                          |     |     |       |
| Invoice creation + PDF generation     |     |     |       |
| Calendar ICS feed valid               |     |     |       |
| Cloudflare Tunnel setup + teardown    |     |     |       |
| Pomodoro full cycle                   |     |     |       |
| Browser extension (Chrome)            |     |     |       |
| Browser extension (Firefox)           |     |     |       |
| Mobile PWA pairing + viewing          |     |     |       |
| Multi-monitor capture                 |     |     |       |
| Autostart enable/disable              |     |     |       |
| Idle detection + resume               |     |     |       |
| Graceful shutdown from tray           |     |     |       |
| Database migration from empty         |     |     |       |
| CPU < 5%, RAM < 200MB                 |     |     |       |

### Performance Validation

| Metric              | Target        | How to Measure                                  |
| ------------------- | ------------- | ----------------------------------------------- |
| CPU (idle screen)   | < 1%          | System monitor over 5 min                       |
| CPU (active screen) | < 5%          | System monitor during normal coding             |
| RAM                 | < 200 MB      | System monitor after 1 hour of use              |
| VRAM                | 0             | GPU monitoring tool                             |
| DB growth           | < 10 MB/month | Calculate from 1 week of data                   |
| Dashboard load      | < 2s          | Browser DevTools network tab                    |
| LLM calls/min       | 2-4           | Check `llm_usage_log` over 30 min of active use |

### Security Audit

- [ ] FastAPI only on 127.0.0.1 (verify with `netstat`)
- [ ] Cloudflare Tunnel ingress only allows `/api/calendar/feed/*` and `/api/mobile/*`
- [ ] API keys stored in platform keyring, not in DB as plaintext
- [ ] No raw OCR text stored — only first 200 chars of redacted text
- [ ] No screenshots ever written to disk
- [ ] Mobile tokens are random 64-char hex
- [ ] ICS feed token is random 32-char hex

### Acceptance Criteria

- [ ] Windows installer: clean install on fresh Windows 10/11 → works
- [ ] macOS DMG: drag to Applications → works on Intel and Apple Silicon
- [ ] Linux AppImage: download → chmod +x → run → works on Ubuntu 22.04+
- [ ] Chrome extension: load from .zip → works
- [ ] Firefox extension: load from .xpi → works
- [ ] All QA matrix cells pass
- [ ] Performance metrics within budget
- [ ] Security audit passes

---

## DEPENDENCY GRAPH

```
Phase 0 ─── Foundation
   │
   ├── Phase 1 ─── Core Tracking Loop
   │      │
   │      ├── Phase 2 ─── Cross-Platform
   │      │
   │      └── Phase 3 ─── LLM Classification
   │             │
   │             └── Phase 4 ─── Dashboard MVP
   │                    │
   │                    ├── Phase 5 ─── Calendar / Tunnel / Reports
   │                    │      │
   │                    │      └── Phase 9 ─── Mobile PWA (needs Tunnel)
   │                    │
   │                    ├── Phase 6 ─── Invoicing
   │                    │
   │                    ├── Phase 7 ─── Pomodoro
   │                    │
   │                    └── Phase 8 ─── Browser Extension
   │
   └── Phase 10 ── Multi-Monitor (can start after Phase 1)
          │
          └── Phase 11 ── Packaging & Release (after all phases)
```

**Parallelization opportunities**: Phases 6, 7, 8, and 10 are largely independent of each other. If multiple people are working on this, they can run in parallel after Phase 4 is done. Phase 9 depends on Phase 5 (Cloudflare Tunnel). Phase 11 is a gate — everything must be done first.

---

## RISK REGISTER

| Risk                                                     | Impact                                                                     | Likelihood | Mitigation                                                                                                                                      |
| -------------------------------------------------------- | -------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| PaddleOCR CPU performance too slow on old hardware       | Degraded UX: long OCR times block classification                           | Medium     | Configurable downscale resolution, skip OCR if frame rate drops, profile on target hardware early (Phase 1)                                     |
| LLM API costs higher than expected                       | Monthly budget exhausted quickly                                           | Medium     | Classification cache, change detection, configurable budget cap — all designed to minimize calls. Test cost-per-day in Phase 3 with real usage. |
| LLM classification accuracy poor with heavy redaction    | Low confidence scores, many unclassified sessions at Level 3-4             | Medium     | Dashboard shows confidence, user can easily reclassify. Test all privacy levels in Phase 3 and document accuracy trade-offs.                    |
| Cross-platform window info APIs break on niche Linux DEs | Capture loop can't get window title on Wayland compositors other than Sway | Medium     | Document supported environments. Fallback: use process name only. Linux has the most variance — test Sway, GNOME (Wayland), and KDE.            |
| Cloudflare API changes break tunnel integration          | Tunnel stops working                                                       | Low        | Pin to specific API version, add error handling with user-facing messages. Cloudflare's tunnel API has been stable.                             |
| weasyprint rendering inconsistencies                     | Invoice PDF layout broken                                                  | Low        | Use simple HTML/CSS for invoice template, avoid complex CSS features. Test PDF output thoroughly in Phase 6.                                    |
| Browser extension store review delays                    | Extension not available to users at launch                                 | Medium     | Start store submission early in Phase 11. Have sideload instructions as fallback.                                                               |
| PaddleOCR model size inflates PyInstaller package        | Large installer download (500MB+)                                          | High       | Expected and accepted. Document download size. Consider lazy model download on first use as optimization.                                       |

---

## VERSIONING STRATEGY

| Version | Maps To  | Milestone                                |
| ------- | -------- | ---------------------------------------- |
| 0.1.0   | Phase 0  | Skeleton boots, DB created, API responds |
| 0.2.0   | Phase 1  | Capture loop works, sessions recorded    |
| 0.3.0   | Phase 2  | Cross-platform support                   |
| 0.4.0   | Phase 3  | LLM classification working               |
| 0.5.0   | Phase 4  | Dashboard MVP usable                     |
| 0.6.0   | Phase 5  | Calendar sync + Tunnel + Reports         |
| 0.7.0   | Phase 6  | Invoice generation                       |
| 0.8.0   | Phase 7  | Pomodoro timer                           |
| 0.9.0   | Phase 8  | Browser extension                        |
| 0.10.0  | Phase 9  | Mobile PWA                               |
| 0.11.0  | Phase 10 | Multi-monitor                            |
| 1.0.0   | Phase 11 | Release                                  |
