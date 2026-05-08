# ChronoLens — Complete Build Specification v3

You are building **ChronoLens**, a cross-platform, privacy-conscious, automatic time tracking application for freelancers and consultants. It passively monitors computer usage across all monitors, uses a cloud LLM (Claude or OpenAI) to intelligently classify activities into projects and task categories, and produces billing reports, invoices, and calendar entries. It runs as a system tray / menu bar application on Windows, macOS, and Linux.

Read this entire specification before writing any code. Follow it precisely — every architectural decision documented here was made deliberately.

---

## TABLE OF CONTENTS

1. [Project Context](#1-project-context)
2. [Architecture Overview](#2-architecture-overview)
3. [Background Agent](#3-background-agent)
4. [Text Redaction Engine](#4-text-redaction-engine)
5. [LLM Classification](#5-llm-classification)
6. [Database](#6-database)
7. [API Server](#7-api-server)
8. [Calendar Sync & ICS Feed](#8-calendar-sync--ics-feed)
9. [Cloudflare Tunnel Integration](#9-cloudflare-tunnel-integration)
10. [Report & Invoice Generation](#10-report--invoice-generation)
11. [Pomodoro Timer](#11-pomodoro-timer)
12. [System Tray Application](#12-system-tray-application)
13. [Dashboard UI](#13-dashboard-ui)
14. [Browser Extension](#14-browser-extension)
15. [Mobile Companion App](#15-mobile-companion-app)
16. [Directory Structure](#16-directory-structure)
17. [Tech Stack](#17-tech-stack)
18. [Cross-Platform Considerations](#18-cross-platform-considerations)
19. [Performance Budget](#19-performance-budget)
20. [Security Considerations](#20-security-considerations)
21. [Build & Packaging](#21-build--packaging)
22. [Future Enhancements (Out of Scope)](#22-future-enhancements-out-of-scope)

---

## 1. PROJECT CONTEXT

The user is a freelance software engineer starting a consultancy. They need to know exactly how long projects take so they can set accurate hourly rates and produce billing evidence — including professional invoices — for clients. Existing tools like Toggl require manual time entry. ChronoLens tracks automatically by observing what's on screen, using a cloud LLM to intelligently classify what the user is working on, and generating reports and invoices.

### Key Requirements

- **Automatic passive tracking** — no manual start/stop, no rules to configure
- **Cross-platform** — Windows, macOS, and Linux
- **Multi-monitor support** — capture and classify activity across all connected displays
- **LLM-based classification** — Claude API or OpenAI API (user provides their own API key)
- **Configurable text redaction** — multiple privacy levels before any data leaves the machine
- **Zero VRAM usage** — all local processing on CPU (GPU reserved for other workloads)
- **Calendar sync** — Tuta Calendar (ICS feed subscription), CalDAV, Google Calendar
- **Cloudflare Tunnel** — stable custom domain for exposing the ICS feed
- **Invoice generation** — professional PDF invoices from tracked time
- **Pomodoro timer** — integrated focus timer that tags sessions
- **Browser extension** — captures exact URLs, tab titles, and active tab content context
- **Mobile companion app** — view reports, current activity, timer controls from phone
- **System tray / menu bar app** — autostarts, runs silently, dashboard in browser

---

## 2. ARCHITECTURE OVERVIEW

```
┌───────────────────────────────────────────────────────────────────────┐
│                   SYSTEM TRAY / MENU BAR                              │
│  Icon + Context Menu: Dashboard / Pause / Pomodoro / Settings / Quit  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ launches / manages
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND SERVICE (daemon)                         │
│                                                                        │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │Capture Loop │→│Change Detect │→│  OCR     │→│ Redaction Engine │  │
│  │(1s tick)    │ │(phash + meta)│ │(PaddleOCR│ │ (configurable    │  │
│  │             │ │              │ │ CPU only)│ │  privacy levels) │  │
│  │- screenshots│ │skip if no    │ │          │ │                  │  │
│  │  (all mons) │ │change        │ │          │ │                  │  │
│  │- win title  │ │              │ │          │ │                  │  │
│  │- process    │ │              │ │          │ │                  │  │
│  │- idle state │ │              │ │          │ │                  │  │
│  │- browser ext│ │              │ │          │ │                  │  │
│  └─────────────┘ └──────────────┘ └──────────┘ └───────┬──────────┘  │
│                                                         │             │
│                                                ┌────────▼───────┐    │
│                                                │  LLM Client   │    │
│                                                │ Claude / OpenAI│    │
│                                                └────────┬───────┘    │
│                                                         │             │
│  ┌──────────────────┐                         ┌─────────▼──────────┐ │
│  │ Pomodoro Timer   │ ──── tags sessions ───→ │  Session Tracker   │ │
│  │ (focus/break)    │                          │  (gap detection,   │ │
│  └──────────────────┘                          │   merging, idle)   │ │
│                                                └─────────┬──────────┘ │
└──────────────────────────────────────────────────────────┼────────────┘
                                                           │ writes
                                                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         SQLite DATABASE                                │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ reads
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    LOCAL API SERVER (FastAPI)                           │
│                                                                        │
│  REST + WebSocket + ICS feed                                          │
│  Binds to 127.0.0.1:19532                                            │
│                                                                        │
│  Also serves:                                                         │
│  - Angular dashboard (static files)                                   │
│  - Browser extension communication (native messaging or localhost)    │
│  - Mobile companion API (via Cloudflare Tunnel or local network)      │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│ Dashboard UI     │ │ Browser Extension│ │ Mobile Companion App     │
│ (Angular 19+)    │ │ (Chrome/Firefox) │ │ (React Native or PWA)   │
│ in browser       │ │                  │ │                          │
└──────────────────┘ └──────────────────┘ └──────────────────────────┘
          │
          ▼ (optional)
┌──────────────────────────────────────────────────────────────────────┐
│  CLOUDFLARE TUNNEL (cloudflared subprocess)                           │
│  Exposes ONLY:                                                        │
│  - /api/calendar/feed/* (ICS for Tuta etc.)                          │
│  - /api/mobile/* (mobile companion endpoints)                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Process Architecture

```
chronolens (single main process)
├── Thread: System tray / menu bar icon
├── Thread: Capture loop (1s tick, multi-monitor, change detection, OCR)
├── Thread: LLM classification queue consumer
├── Thread: Session aggregation
├── Thread: Pomodoro timer
├── Thread: FastAPI server (uvicorn)
├── Thread: Calendar sync scheduler (APScheduler)
└── Subprocess: cloudflared (optional, managed by app)
```

---

## 3. BACKGROUND AGENT

### 3.1 Capture Loop

Runs in a dedicated thread. Every 1 second, collects raw signals from the OS.

**Signals per tick:**

| Signal                     | Source                                              | Notes                                    |
| -------------------------- | --------------------------------------------------- | ---------------------------------------- |
| Active window title        | Platform-specific (see §18)                         | The currently focused window             |
| Process name + PID         | Platform-specific (see §18)                         | Which application owns the window        |
| Screenshots (all monitors) | `mss` library                                       | One screenshot per monitor, all captured |
| Active monitor             | Determine which monitor contains the focused window | Used to pick primary screenshot for OCR  |
| Idle duration (seconds)    | Platform-specific (see §18)                         | Time since last keyboard/mouse input     |
| Input activity             | Event counter (NOT keylogger)                       | For idle detection only                  |
| Browser context            | Via browser extension WebSocket (if available)      | URL, tab title, page content snippet     |

#### Multi-Monitor Capture

`mss` can capture individual monitors or all monitors at once:

```python
import mss

with mss.mss() as sct:
    monitors = sct.monitors  # [0] = virtual screen (all), [1] = primary, [2] = secondary, etc.

    # Capture each physical monitor individually
    for i, monitor in enumerate(monitors[1:], start=1):  # skip [0] which is the virtual combined screen
        screenshot = sct.grab(monitor)
        # store as { monitor_index: i, image: screenshot, bounds: monitor }
```

**Which monitor to classify:**

The primary classification target is the monitor containing the active/focused window. Determine this by comparing the focused window's position (`GetWindowRect` on Windows, equivalent on other platforms) against monitor bounds.

However, **all monitor screenshots are captured** every tick. The focused-monitor screenshot goes through OCR + LLM classification. The other monitors' screenshots are only change-detected (perceptual hash) and stored in a rolling buffer — if the user switches focus to another monitor, the pre-captured screenshot is already available for immediate classification without waiting for the next tick.

**Implementation notes:**

- Use `mss` for all platforms — it supports Windows, macOS, and Linux
- Screenshots held in memory only, never written to disk
- The loop uses `threading.Event.wait(1.0)` for timing
- When idle exceeds `idle_split_threshold` (default 300s), pause capture entirely
- PaddleOCR model loaded once at startup, kept in memory

### 3.2 Change Detection

Same as v2 but applied to the focused monitor's screenshot:

```python
def on_tick():
    focused_monitor = get_focused_monitor_index()
    screenshot = screenshots[focused_monitor]
    current_title = get_active_window_title()
    current_process = get_active_process()
    browser_context = get_browser_context()  # from extension, if available

    # Fast path: window or browser context changed
    title_changed = current_title != previous_title
    process_changed = current_process != previous_process
    url_changed = browser_context and browser_context.url != previous_url

    if title_changed or process_changed or url_changed:
        update_previous_state()
        enqueue_for_classification(screenshot, current_title, current_process, browser_context)
        return

    # Slow path: same window, check screen content
    current_hash = compute_phash(screenshot, hash_size=8)
    if (current_hash - previous_hash) > PHASH_CHANGE_THRESHOLD:
        previous_hash = current_hash
        enqueue_for_classification(screenshot, current_title, current_process, browser_context)
    else:
        extend_current_session()
```

### 3.3 OCR Text Extraction

Runs only on screen change. Extracts text from the focused monitor's screenshot.

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=False, show_log=False)

# Downscale to 1280px width for speed
result = ocr.ocr(downscaled_screenshot_np, cls=False)
raw_text = " ".join([line[1][0] for line in result[0]])
```

- CPU mode only — zero VRAM
- Angle classification disabled
- Downscale to 1280px width before OCR
- Raw text passed through redaction engine before LLM

### 3.4 Classification Queue

The capture loop pushes work onto a thread-safe queue. The LLM thread consumes asynchronously.

```python
import queue

classification_queue = queue.Queue(maxsize=100)

classification_queue.put({
    "timestamp": datetime.now(),
    "window_title": current_title,
    "process_name": current_process,
    "raw_ocr_text": raw_text,
    "browser_url": browser_context.url if browser_context else None,
    "browser_title": browser_context.title if browser_context else None,
    "browser_snippet": browser_context.content_snippet if browser_context else None,
    "monitor_index": focused_monitor,
    "screenshot_hash": current_hash,
})
```

If the queue is full (LLM can't keep up), drop the oldest unprocessed items. The session tracker interpolates from adjacent classifications.

---

## 4. TEXT REDACTION ENGINE

### Purpose

Before any text leaves the machine (sent to Claude or OpenAI API), it must be sanitized. The redaction engine strips or masks sensitive content according to the user's configured privacy level. This applies to OCR text, window titles, browser URLs, and browser content snippets.

### Privacy Levels

The user selects a privacy level in Settings. Each level is cumulative — it includes everything from the levels below it.

#### Level 1: Minimal (least redaction)

Redacts only high-risk secrets that should never be transmitted under any circumstances:

| Category                  | Detection Method                                                                                                                                    | Replacement          |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------- | ----------- | ------------ | ----- | ---- | ------------------ | --------------------- |
| API keys & tokens         | Regex: `sk-[a-zA-Z0-9]{20,}`, `sk-proj-`, `ghp_[a-zA-Z0-9]+`, `glpat-`, `AKIA[0-9A-Z]{16}`, `xox[bpsa]-`, `Bearer\s+\S{20,}`, `token[:\s=]+\S{20,}` | `[API_KEY]`          |
| Passwords in context      | Regex: `password[:\s=]+\S+`, `passwd[:\s=]+\S+`, `secret[:\s=]+\S+`, `wachtwoord[:\s=]+\S+` (Dutch)                                                 | `[PASSWORD]`         |
| Private keys              | Regex: `-----BEGIN\s+.*PRIVATE KEY-----[\s\S]*?-----END`                                                                                            | `[PRIVATE_KEY]`      |
| Connection strings        | Regex: `(mysql                                                                                                                                      | postgres             | postgresql                | mongodb     | mongodb\+srv | redis | amqp | mssql):\/\/[^\s]+` | `[CONNECTION_STRING]` |
| Cloud credentials         | Regex: AWS access keys, Azure connection strings, GCP service account patterns                                                                      | `[CLOUD_CREDENTIAL]` |
| SSH keys                  | Regex: `ssh-(rsa                                                                                                                                    | ed25519              | ecdsa)\s+[A-Za-z0-9+/=]+` | `[SSH_KEY]` |
| JWT tokens                | Regex: `eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+`                                                                               | `[JWT]`              |
| .env file values          | Regex: `^[A-Z][A-Z0-9_]+=.+` (multi-line blocks of env vars)                                                                                        | `[ENV_VAR]`          |
| Hex secrets (32+ chars)   | Regex: `\b[0-9a-fA-F]{32,}\b` in suspicious context (near "key", "token", "secret", "hash")                                                         | `[HEX_SECRET]`       |
| Base64 blobs (100+ chars) | Regex: `[A-Za-z0-9+/=]{100,}`                                                                                                                       | `[BASE64_BLOB]`      |
| PGP/GPG blocks            | Regex: `-----BEGIN PGP.*-----[\s\S]*?-----END PGP`                                                                                                  | `[PGP_BLOCK]`        |
| Certificate content       | Regex: `-----BEGIN CERTIFICATE-----[\s\S]*?-----END`                                                                                                | `[CERTIFICATE]`      |

#### Level 2: Standard (recommended default)

Everything in Level 1, plus personally identifiable information and network identifiers:

| Category            | Detection Method                                                                                | Replacement                |
| ------------------- | ----------------------------------------------------------------------------------------------- | -------------------------- |
| Email addresses     | Regex: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}`                                           | `[EMAIL]`                  |
| Phone numbers       | Regex: international formats, `+31`, `06-\d{8}`, `(\d{3}) \d{3}-\d{4}`, `\+\d{1,3}[\s-]?\d+`    | `[PHONE]`                  |
| IPv4 addresses      | Regex: `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b` (excluding `127.0.0.1`, `0.0.0.0`, `localhost`) | `[IP_ADDRESS]`             |
| IPv6 addresses      | Regex: standard IPv6 patterns                                                                   | `[IP_ADDRESS]`             |
| MAC addresses       | Regex: `([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}`                                                  | `[MAC_ADDRESS]`            |
| URLs → domain only  | Regex: `https?://([^/\s]+)\S*` → keep scheme + domain, strip path/query                         | `https://[URL:domain.com]` |
| Local file paths    | Regex: `[A-Z]:\\[\w\s\\.-]+` (Windows), `/home/\S+`, `/Users/\S+`, `/etc/\S+`, `/var/\S+`       | `[PATH]`                   |
| Credit card numbers | Regex: `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,4}\b` + Luhn validation                         | `[CREDIT_CARD]`            |
| IBAN numbers        | Regex: `\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b`                                                        | `[IBAN]`                   |
| BSN (Dutch)         | Regex: `\b\d{9}\b` near context keywords "BSN", "burgerservicenummer"                           | `[NATIONAL_ID]`            |
| SSN (US)            | Regex: `\b\d{3}-\d{2}-\d{4}\b`                                                                  | `[NATIONAL_ID]`            |
| Postal addresses    | Regex: Dutch format `\d{4}\s?[A-Z]{2}`, US zip `\d{5}(-\d{4})?`, street patterns                | `[ADDRESS]`                |
| Dates of birth      | Regex: keywords `DOB`, `geboren`, `birth`, `geboortedatum` near date patterns                   | `[DOB]`                    |

#### Level 3: Aggressive

Everything in Level 1 + 2, plus content that could identify people, organizations, or business details:

| Category                 | Detection Method                                                                                                                                    | Replacement      |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ----------------------------------------------- | ---------- |
| Person names             | Heuristic: 2-3 capitalized words not in a common-words dictionary, near context like "Dear", "From:", "To:", "Hi", "Beste", "Geachte", "@" mentions | `[PERSON]`       |
| Organization names       | Heuristic: capitalized words near "BV", "B.V.", "NV", "VOF", "LLC", "Inc", "GmbH", "Ltd", "Corp", or appearing after "©"                            | `[ORG]`          |
| Monetary amounts         | Regex: `[€$£¥]\s?\d[\d.,]*`, `\d[\d.,]\*\s?(EUR                                                                                                     | USD              | GBP)`, `\b\d+[.,]\d{2}\b` near currency context | `[AMOUNT]` |
| Numeric identifiers      | Regex: `INV[-#]\d+`, `ORD[-#]\d+`, `#\d{3,}`, `KVK[-:\s]\d+`, ticket/issue patterns                                                                 | `[ID_NUMBER]`    |
| Chat/messaging content   | Heuristic: timestamp + username + message patterns (Slack, Teams, Discord, WhatsApp Web)                                                            | `[CHAT_MESSAGE]` |
| Shell commands with args | Regex: lines starting with `$`, `>`, `#` (shell prompt), or containing `curl`, `wget`, `ssh`, `scp`, `docker`, `kubectl` with arguments             | `[COMMAND]`      |
| Git diffs / patches      | Heuristic: lines starting with `+`, `-`, `@@`, `diff --git`, `index `                                                                               | `[CODE_DIFF]`    |
| Database query results   | Heuristic: aligned columns of data, SQL output patterns, table-formatted text                                                                       | `[DB_OUTPUT]`    |
| Log file content         | Heuristic: repeated timestamp-prefixed lines, structured log patterns (JSON logs, syslog format)                                                    | `[LOG_CONTENT]`  |
| HTTP headers             | Regex: `[A-Za-z-]+:\s+.+` patterns matching common HTTP headers (Cookie, Authorization, Set-Cookie, X-)                                             | `[HTTP_HEADER]`  |

#### Level 4: Maximum (most redaction)

Everything in Level 1 + 2 + 3, plus broad content reduction. At this level, the LLM receives primarily structural information (what app, what type of content) rather than actual content:

| Category                | Detection Method                                                                                                                                            | Replacement     |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| All numbers > 4 digits  | Regex: `\b\d{5,}\b`                                                                                                                                         | `[NUMBER]`      |
| All email-like domains  | Strip all text after `@`                                                                                                                                    | `[DOMAIN]`      |
| Code content (bulk)     | Heuristic: lines containing `{`, `}`, `=>`, `->`, `function`, `class`, `import`, `const`, `let`, `var`, `def`, `if (`, `for (`, indented blocks of 3+ lines | `[CODE_BLOCK]`  |
| All URLs entirely       | Regex: any URL completely removed                                                                                                                           | `[URL]`         |
| Multi-word proper nouns | Any sequence of 2+ capitalized words not matching common English/Dutch word pairs                                                                           | `[PROPER_NOUN]` |
| Non-ASCII text          | Sequences of non-ASCII characters (potential names in other scripts)                                                                                        | `[NON_ASCII]`   |
| All tabular data        | Heuristic: aligned columns, CSV-like patterns, pipe-separated data                                                                                          | `[TABLE_DATA]`  |
| Quoted text             | Text inside quotation marks, `"..."`, `'...'`, `«...»`                                                                                                      | `[QUOTED]`      |
| Paragraphs of prose     | Blocks of 3+ sentences (likely document content, emails, articles)                                                                                          | `[TEXT_BLOCK]`  |

**Note to implementer:** At Level 4, classification accuracy will decrease significantly since the LLM has very little content to work with. The UI should warn the user about this trade-off.

### Custom Redaction Patterns

In addition to the privacy level, users can define custom patterns that are always applied regardless of level:

```sql
CREATE TABLE custom_redaction_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern         TEXT NOT NULL,             -- the pattern string
    match_mode      TEXT DEFAULT 'contains',   -- contains | regex | exact
    replacement     TEXT DEFAULT '[REDACTED]', -- what to replace with
    description     TEXT,                      -- user's note about why
    is_active       BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Example user rules:

- Pattern: `scenery-en-zo\.nl`, Mode: regex, Replacement: `[CLIENT_DOMAIN]`
- Pattern: `Klant XYZ`, Mode: contains, Replacement: `[CLIENT_NAME]`
- Pattern: `192\.168\.1\.\d+`, Mode: regex, Replacement: `[HOME_NETWORK]`

### Redaction Application Order

```
1. Custom redaction rules (always, regardless of level)
2. Level-based redaction patterns (in order: secrets → PII → content → broad)
3. Final pass: collapse multiple whitespace, trim to max length (default 800 chars)
```

### What Gets Redacted

The redaction engine processes ALL text before it leaves the machine:

| Field                                    | Redacted?                                                      |
| ---------------------------------------- | -------------------------------------------------------------- |
| OCR text from screenshot                 | Yes — full redaction                                           |
| Window title                             | Yes — full redaction                                           |
| Process name                             | No — this is just "firefox.exe", "phpstorm64.exe" etc.         |
| Browser URL (from extension)             | Yes — Level 2+ strips to domain only, Level 4 removes entirely |
| Browser page title (from extension)      | Yes — full redaction                                           |
| Browser content snippet (from extension) | Yes — full redaction                                           |

### Redaction Preview

The dashboard Settings page should include a **redaction preview** tool: the user pastes sample text, selects a privacy level, and sees the redacted output in real-time. This helps them understand what the LLM will see.

### Redaction Log

For transparency, the app stores redaction statistics (NOT the redacted content itself):

```sql
CREATE TABLE redaction_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    privacy_level   INTEGER NOT NULL,
    original_length INTEGER,
    redacted_length INTEGER,
    redaction_count INTEGER,          -- how many items were redacted
    categories_hit  TEXT,             -- JSON array of triggered categories, e.g. ["EMAIL", "API_KEY"]
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. LLM CLASSIFICATION

### Architecture

A dedicated thread consumes from the classification queue and calls the configured LLM API.

```python
# LLM classification thread
def classification_worker():
    while running:
        try:
            item = classification_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # 1. Redact the text
        redacted = redaction_engine.redact(
            ocr_text=item["raw_ocr_text"],
            window_title=item["window_title"],
            browser_url=item.get("browser_url"),
            browser_title=item.get("browser_title"),
            browser_snippet=item.get("browser_snippet"),
        )

        # 2. Check classification cache
        cache_key = compute_cache_key(redacted, item["process_name"])
        cached = get_cached_classification(cache_key)
        if cached:
            store_activity(item["timestamp"], cached)
            continue

        # 3. Call LLM
        classification = call_llm(redacted, item["process_name"])

        # 4. Cache the result
        cache_classification(cache_key, classification)

        # 5. Store activity record
        store_activity(item["timestamp"], classification)
```

### Classification Cache

To reduce API costs, cache LLM responses. If the same (redacted text + process name) has been seen before, reuse the classification.

```sql
CREATE TABLE classification_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key       TEXT NOT NULL UNIQUE,      -- hash of (redacted_text + process_name)
    project_id      INTEGER,
    task_category   TEXT,
    confidence      REAL,
    llm_response    TEXT,                      -- full JSON response for debugging
    hit_count       INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_hit_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cache_key ON classification_cache(cache_key);
```

Cache entries expire after a configurable TTL (default: 24 hours). The cache key is a SHA-256 hash of the concatenation of redacted OCR text + process name.

### LLM Provider Configuration

```sql
CREATE TABLE llm_config (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
    provider        TEXT NOT NULL DEFAULT 'claude',       -- claude | openai
    api_key         TEXT,                                 -- encrypted via platform keyring
    model           TEXT,                                 -- e.g. "claude-sonnet-4-20250514" or "gpt-4o-mini"
    max_tokens      INTEGER DEFAULT 200,
    temperature     REAL DEFAULT 0.0,                     -- deterministic classification
    monthly_budget_cents INTEGER DEFAULT 0,              -- 0 = unlimited
    monthly_spent_cents INTEGER DEFAULT 0,
    budget_reset_day INTEGER DEFAULT 1,                   -- day of month to reset counter
    is_active       BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### LLM Prompt

The prompt must be carefully structured to get consistent, parseable JSON responses:

```python
SYSTEM_PROMPT = """You are a time tracking classifier for a freelance software engineer.
Your job is to determine which project and task category the user is currently working on,
based on their screen context.

You will receive:
- The application name (process)
- The window title (may be partially redacted)
- Visible screen text (redacted for privacy — items like [EMAIL], [API_KEY], [PATH] are placeholders)
- Browser URL and page title (if available, may be redacted)

Respond with ONLY a JSON object, no other text:
{
    "project": "exact project name from the list, or null if unclear",
    "task": "one of the allowed task categories",
    "confidence": 0.0 to 1.0,
    "reasoning": "one sentence explaining your classification"
}

Rules:
- If the activity clearly matches a project, set confidence >= 0.8
- If it's ambiguous between projects, pick the most likely one with lower confidence
- If it doesn't match any project (e.g. personal browsing, system settings), set project to null
- Always assign a task category even if project is null
- Redacted placeholders like [EMAIL], [CODE_BLOCK] still provide structural hints — use them"""

def build_user_prompt(context: dict, projects: list[dict], task_categories: list[str]) -> str:
    project_list = "\n".join([
        f"- {p['name']}" + (f" (client: {p['client']})" if p['client'] else "")
        for p in projects if p['is_active']
    ])

    return f"""Active projects:
{project_list}

Allowed task categories: {", ".join(task_categories)}

Current context:
- Application: {context['process_name']}
- Window title: {context['redacted_title']}
- Browser URL: {context.get('redacted_url', 'N/A')}
- Browser page title: {context.get('redacted_browser_title', 'N/A')}
- Visible text: {context['redacted_ocr_text'][:800]}"""
```

### API Calls

#### Claude API (Anthropic)

```python
import httpx

async def classify_with_claude(prompt: str, config: LLMConfig) -> dict:
    response = await httpx.AsyncClient().post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.model or "claude-sonnet-4-20250514",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=10.0,
    )
    text = response.json()["content"][0]["text"]
    return json.loads(text)
```

#### OpenAI API

```python
async def classify_with_openai(prompt: str, config: LLMConfig) -> dict:
    response = await httpx.AsyncClient().post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model or "gpt-4o-mini",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=10.0,
    )
    text = response.json()["choices"][0]["message"]["content"]
    return json.loads(text)
```

### Cost Management

- **Classification cache** eliminates redundant calls (same screen = same classification)
- **Change detection** means only ~2-4 calls per minute instead of 60
- **Monthly budget cap**: if `monthly_spent_cents >= monthly_budget_cents`, stop calling the LLM and mark new activities as `unclassified` with a tray notification
- **Cost tracking**: each API call logs estimated token count and cost in the database
- **Dashboard shows**: daily/weekly/monthly API spend, calls count, cache hit rate

```sql
CREATE TABLE llm_usage_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    estimated_cost_cents REAL,
    cache_hit       BOOLEAN DEFAULT 0,
    classification_success BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Fallback Behavior

If the LLM is unavailable (API error, rate limit, budget exceeded, no API key configured):

1. Use process name as the application identifier
2. Store the window title and OCR text locally
3. Mark the activity as `source = "pending_classification"`
4. Queue for retry when the LLM becomes available again
5. The session tracker still creates sessions based on window title + process changes — they just lack project assignment until classified

### New Project Learning

When the LLM encounters context that doesn't match any existing project, it returns `"project": null`. The dashboard shows these unclassified sessions prominently. When the user creates a new project and manually assigns sessions to it, the LLM naturally learns to classify future similar activities to that project because the project now appears in the project list sent with each prompt.

---

## 6. DATABASE

SQLite with WAL mode. Database file at platform-appropriate location:

- **Windows**: `%APPDATA%/ChronoLens/chronolens.db`
- **macOS**: `~/Library/Application Support/ChronoLens/chronolens.db`
- **Linux**: `~/.local/share/chronolens/chronolens.db`

```sql
-- ============================================================
-- PROJECTS
-- ============================================================

CREATE TABLE projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    client          TEXT,
    hourly_rate     REAL,                    -- in configured currency per hour
    color           TEXT DEFAULT '#6366f1',   -- hex color for UI
    is_billable     BOOLEAN DEFAULT 1,
    is_active       BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TASK CATEGORIES
-- ============================================================

CREATE TABLE task_categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    is_billable     BOOLEAN DEFAULT 1
);

INSERT INTO task_categories (name, is_billable) VALUES
    ('coding', 1),
    ('code-review', 1),
    ('devops', 1),
    ('debugging', 1),
    ('testing', 1),
    ('design', 1),
    ('meeting', 1),
    ('email', 1),
    ('communication', 1),
    ('documentation', 1),
    ('research', 1),
    ('planning', 1),
    ('administration', 0),
    ('browsing', 0),
    ('other', 0),
    ('unclassified', 0);

-- ============================================================
-- ACTIVITIES (raw 1-second records)
-- ============================================================

CREATE TABLE activities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    window_title    TEXT,
    process_name    TEXT,
    project_id      INTEGER REFERENCES projects(id),
    task_category   TEXT,
    application     TEXT,                     -- human-readable app name
    confidence      REAL DEFAULT 0.0,
    source          TEXT DEFAULT 'pending',   -- llm | manual | pending_classification | cache
    llm_reasoning   TEXT,                     -- one-sentence from LLM
    ocr_snippet     TEXT,                     -- first 200 chars of REDACTED text (not raw)
    monitor_index   INTEGER DEFAULT 0,
    is_idle         BOOLEAN DEFAULT 0,
    pomodoro_session_id INTEGER REFERENCES pomodoro_sessions(id),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SESSIONS (aggregated time blocks)
-- ============================================================

CREATE TABLE sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time      DATETIME NOT NULL,
    end_time        DATETIME NOT NULL,
    duration_seconds INTEGER NOT NULL,
    project_id      INTEGER REFERENCES projects(id),
    task_category   TEXT,
    application     TEXT,
    confidence_avg  REAL,
    manually_reviewed BOOLEAN DEFAULT 0,
    notes           TEXT,
    synced_to_calendar BOOLEAN DEFAULT 0,
    calendar_event_uid TEXT,
    invoice_id      INTEGER REFERENCES invoices(id),
    pomodoro_count  INTEGER DEFAULT 0,        -- how many pomodoros occurred during this session
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- POMODORO
-- ============================================================

CREATE TABLE pomodoro_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,             -- focus | short_break | long_break
    start_time      DATETIME NOT NULL,
    end_time        DATETIME,
    planned_duration_seconds INTEGER NOT NULL,
    actual_duration_seconds INTEGER,
    completed       BOOLEAN DEFAULT 0,         -- ran to completion vs cancelled
    project_id      INTEGER REFERENCES projects(id),
    task_category   TEXT,
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INVOICES
-- ============================================================

CREATE TABLE invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number  TEXT NOT NULL UNIQUE,      -- user-defined or auto-generated format
    project_id      INTEGER NOT NULL REFERENCES projects(id),
    client_name     TEXT NOT NULL,
    client_address  TEXT,
    client_email    TEXT,
    client_vat      TEXT,                      -- VAT/tax number
    from_name       TEXT NOT NULL,             -- freelancer name
    from_address    TEXT,
    from_email      TEXT,
    from_vat        TEXT,                      -- freelancer VAT number
    from_kvk        TEXT,                      -- Dutch KVK number
    from_iban       TEXT,                      -- bank account for payment
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    hours_billable  REAL NOT NULL,
    hours_non_billable REAL DEFAULT 0,
    hourly_rate     REAL NOT NULL,
    subtotal        REAL NOT NULL,             -- hours × rate
    vat_percentage  REAL DEFAULT 21.0,         -- default Dutch BTW
    vat_amount      REAL NOT NULL,
    total           REAL NOT NULL,             -- subtotal + VAT
    currency        TEXT DEFAULT 'EUR',
    status          TEXT DEFAULT 'draft',      -- draft | sent | paid | overdue
    due_date        DATE,
    payment_terms   TEXT DEFAULT 'Net 30',
    notes           TEXT,                      -- additional notes on invoice
    pdf_path        TEXT,                      -- path to generated PDF
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at         DATETIME,
    paid_at         DATETIME
);

CREATE TABLE invoice_line_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id),
    description     TEXT NOT NULL,             -- e.g. "Development — coding" or "DevOps — deployment"
    hours           REAL NOT NULL,
    rate            REAL NOT NULL,
    amount          REAL NOT NULL,             -- hours × rate
    task_category   TEXT,
    sort_order      INTEGER DEFAULT 0
);

-- ============================================================
-- FREELANCER PROFILE (for invoices)
-- ============================================================

CREATE TABLE freelancer_profile (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
    name            TEXT,
    company_name    TEXT,
    address_line1   TEXT,
    address_line2   TEXT,
    postal_code     TEXT,
    city            TEXT,
    country         TEXT DEFAULT 'Netherlands',
    email           TEXT,
    phone           TEXT,
    website         TEXT,
    vat_number      TEXT,                      -- BTW-nummer
    kvk_number      TEXT,                      -- KVK number
    iban            TEXT,
    bic             TEXT,
    payment_terms   TEXT DEFAULT 'Net 30',
    default_vat_percentage REAL DEFAULT 21.0,
    invoice_number_prefix TEXT DEFAULT 'INV',
    invoice_number_next INTEGER DEFAULT 1,     -- auto-increment
    logo_path       TEXT,                      -- path to logo image for invoice header
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CLIENT PROFILES (for invoices)
-- ============================================================

CREATE TABLE clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    company_name    TEXT,
    address_line1   TEXT,
    address_line2   TEXT,
    postal_code     TEXT,
    city            TEXT,
    country         TEXT,
    email           TEXT,
    vat_number      TEXT,
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CALENDAR PROVIDERS
-- ============================================================

CREATE TABLE calendar_providers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    provider_type   TEXT NOT NULL,             -- caldav | ics_export | ics_feed | google_api
    caldav_url      TEXT,
    calendar_id     TEXT,
    auth_token      TEXT,                      -- encrypted via platform keyring
    is_active       BOOLEAN DEFAULT 1,
    last_sync       DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SYNC LOG
-- ============================================================

CREATE TABLE sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(id),
    provider_id     INTEGER REFERENCES calendar_providers(id),
    event_uid       TEXT,
    action          TEXT,                      -- created | updated | deleted
    status          TEXT,                      -- success | failed
    error_message   TEXT,
    synced_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CLOUDFLARE TUNNEL CONFIG
-- ============================================================

CREATE TABLE cloudflare_config (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
    api_token       TEXT,                      -- encrypted via platform keyring
    account_id      TEXT,
    tunnel_id       TEXT,
    tunnel_token    TEXT,                      -- encrypted
    zone_id         TEXT,
    zone_name       TEXT,                      -- e.g. "example.com"
    subdomain       TEXT,                      -- e.g. "time"
    full_hostname   TEXT,                      -- e.g. "time.example.com"
    cname_record_id TEXT,
    is_active       BOOLEAN DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ICS FEED CONFIG
-- ============================================================

CREATE TABLE ics_feed_config (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
    feed_token      TEXT NOT NULL,             -- random 32-char hex secret
    include_project_ids TEXT,                  -- comma-separated, or NULL for all
    include_billable_only BOOLEAN DEFAULT 0,
    min_session_minutes INTEGER DEFAULT 5,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- LLM CONFIG
-- ============================================================

CREATE TABLE llm_config (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
    provider        TEXT NOT NULL DEFAULT 'claude',       -- claude | openai
    api_key         TEXT,                                 -- encrypted via platform keyring
    model           TEXT,
    max_tokens      INTEGER DEFAULT 200,
    temperature     REAL DEFAULT 0.0,
    monthly_budget_cents INTEGER DEFAULT 0,
    monthly_spent_cents INTEGER DEFAULT 0,
    budget_reset_day INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- LLM USAGE LOG
-- ============================================================

CREATE TABLE llm_usage_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    estimated_cost_cents REAL,
    cache_hit       BOOLEAN DEFAULT 0,
    classification_success BOOLEAN DEFAULT 1,
    error_message   TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CLASSIFICATION CACHE
-- ============================================================

CREATE TABLE classification_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key       TEXT NOT NULL UNIQUE,
    project_id      INTEGER,
    task_category   TEXT,
    confidence      REAL,
    llm_response    TEXT,
    hit_count       INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_hit_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME NOT NULL
);

-- ============================================================
-- REDACTION CONFIG
-- ============================================================

CREATE TABLE custom_redaction_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern         TEXT NOT NULL,
    match_mode      TEXT DEFAULT 'contains',   -- contains | regex | exact
    replacement     TEXT DEFAULT '[REDACTED]',
    description     TEXT,
    is_active       BOOLEAN DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE redaction_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    privacy_level   INTEGER NOT NULL,
    original_length INTEGER,
    redacted_length INTEGER,
    redaction_count INTEGER,
    categories_hit  TEXT,                      -- JSON array
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SETTINGS
-- ============================================================

CREATE TABLE settings (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO settings (key, value) VALUES
    ('idle_merge_threshold', '120'),
    ('idle_split_threshold', '300'),
    ('min_session_duration', '10'),
    ('capture_interval_ms', '1000'),
    ('ocr_enabled', 'true'),
    ('ocr_downscale_width', '1280'),
    ('phash_change_threshold', '5'),
    ('default_hourly_rate', '0'),
    ('currency', 'EUR'),
    ('autostart', 'true'),
    ('api_port', '19532'),
    ('privacy_level', '2'),
    ('cache_ttl_hours', '24'),
    ('pomodoro_focus_minutes', '25'),
    ('pomodoro_short_break_minutes', '5'),
    ('pomodoro_long_break_minutes', '15'),
    ('pomodoro_long_break_interval', '4'),
    ('pomodoro_auto_start_breaks', 'true'),
    ('pomodoro_auto_start_focus', 'false');

-- ============================================================
-- MOBILE AUTH
-- ============================================================

CREATE TABLE mobile_auth_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    token           TEXT NOT NULL UNIQUE,      -- random 64-char hex
    device_name     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at    DATETIME,
    is_active       BOOLEAN DEFAULT 1
);

-- ============================================================
-- INDICES
-- ============================================================

CREATE INDEX idx_activities_timestamp ON activities(timestamp);
CREATE INDEX idx_activities_project ON activities(project_id);
CREATE INDEX idx_sessions_time ON sessions(start_time, end_time);
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_invoice ON sessions(invoice_id);
CREATE INDEX idx_cache_key ON classification_cache(cache_key);
CREATE INDEX idx_cache_expires ON classification_cache(expires_at);
CREATE INDEX idx_sync_log_session ON sync_log(session_id);
CREATE INDEX idx_pomodoro_time ON pomodoro_sessions(start_time);
CREATE INDEX idx_invoices_project ON invoices(project_id);
CREATE INDEX idx_invoice_lines ON invoice_line_items(invoice_id);
CREATE INDEX idx_llm_usage_time ON llm_usage_log(timestamp);
CREATE INDEX idx_redaction_log_time ON redaction_log(timestamp);
```

---

## 7. API SERVER

FastAPI with uvicorn, running in a thread. Binds to `127.0.0.1:19532`.

### Endpoints

```
# ── Sessions ──
GET    /api/sessions                  ?from=&to=&project_id=&task_category=&source=
GET    /api/sessions/{id}
PUT    /api/sessions/{id}             # reassign project, edit notes, change task
POST   /api/sessions/{id}/split       # split at timestamp
POST   /api/sessions/merge            # merge multiple IDs

# ── Projects ──
GET    /api/projects
POST   /api/projects
PUT    /api/projects/{id}
DELETE /api/projects/{id}             # soft delete

# ── Clients ──
GET    /api/clients
POST   /api/clients
PUT    /api/clients/{id}
DELETE /api/clients/{id}

# ── Reports ──
GET    /api/reports/summary           ?from=&to=&group_by=project|task|day|week|month
GET    /api/reports/billing           ?from=&to=&project_id=
GET    /api/reports/activity          ?from=&to=
GET    /api/reports/productivity      ?from=&to=
POST   /api/reports/export            { type, format, from, to, project_id }

# ── Invoices ──
GET    /api/invoices                  ?status=&project_id=
GET    /api/invoices/{id}
POST   /api/invoices                  # create from tracked time
PUT    /api/invoices/{id}
DELETE /api/invoices/{id}
POST   /api/invoices/{id}/generate-pdf
POST   /api/invoices/{id}/mark-sent
POST   /api/invoices/{id}/mark-paid
GET    /api/invoices/{id}/pdf         # download generated PDF

# ── Freelancer Profile ──
GET    /api/profile
PUT    /api/profile
POST   /api/profile/logo             # upload logo image

# ── Calendar ──
GET    /api/calendar/providers
POST   /api/calendar/providers
PUT    /api/calendar/providers/{id}
DELETE /api/calendar/providers/{id}
POST   /api/calendar/sync
POST   /api/calendar/sync/{id}
GET    /api/calendar/feed/{token}.ics

# ── Cloudflare Tunnel ──
GET    /api/cloudflare/status
POST   /api/cloudflare/setup
POST   /api/cloudflare/test-token
GET    /api/cloudflare/zones
POST   /api/cloudflare/activate
POST   /api/cloudflare/deactivate
DELETE /api/cloudflare/teardown

# ── Pomodoro ──
POST   /api/pomodoro/start            { type: "focus"|"short_break"|"long_break", project_id?, task? }
POST   /api/pomodoro/stop
GET    /api/pomodoro/status            # current timer state
GET    /api/pomodoro/history           ?from=&to=
PUT    /api/pomodoro/settings

# ── LLM ──
GET    /api/llm/config
PUT    /api/llm/config
GET    /api/llm/usage                 ?from=&to=     # usage stats + costs
POST   /api/llm/test                  # test API key + classify a sample

# ── Redaction ──
GET    /api/redaction/level
PUT    /api/redaction/level
GET    /api/redaction/custom-rules
POST   /api/redaction/custom-rules
PUT    /api/redaction/custom-rules/{id}
DELETE /api/redaction/custom-rules/{id}
POST   /api/redaction/preview         { text, level } → returns redacted text
GET    /api/redaction/stats           ?from=&to=

# ── Settings ──
GET    /api/settings
PUT    /api/settings
GET    /api/settings/{key}
PUT    /api/settings/{key}

# ── Status ──
GET    /api/status                    # health: capture, LLM, tunnel, DB size, cache stats

# ── Mobile ──
POST   /api/mobile/auth              # generate auth token (shown as QR code in dashboard)
GET    /api/mobile/verify             # verify token from mobile app
GET    /api/mobile/summary            # today's summary for mobile widget
GET    /api/mobile/sessions           ?from=&to=&project_id=
GET    /api/mobile/projects
GET    /api/mobile/pomodoro/status
POST   /api/mobile/pomodoro/start
POST   /api/mobile/pomodoro/stop

# ── Real-time ──
WS     /ws/live                       # current activity, session changes, pomodoro ticks
```

### Mobile API Authentication

Mobile endpoints under `/api/mobile/*` require a bearer token in the `Authorization` header. The token is generated in the dashboard (displayed as a QR code) and stored in `mobile_auth_tokens`. The Cloudflare Tunnel ingress must be updated to also allow `/api/mobile/*` paths when mobile access is enabled.

---

## 8. CALENDAR SYNC & ICS FEED

### Provider Architecture

```
CalendarSyncService
├── CalendarProvider (abstract base class)
│   ├── CalDAVProvider          — RFC 4791, bidirectional
│   ├── ICSFeedProvider         — RFC 5545, served as HTTP endpoint
│   ├── ICSExportProvider       — RFC 5545, manual .ics file download
│   └── GoogleCalendarProvider  — Google Calendar API v3 via OAuth2
```

### ICS Feed (for Tuta and URL-subscribing calendars)

```
GET /api/calendar/feed/{feed_token}.ics
```

Dynamically generates an RFC 5545 iCalendar document containing all qualifying sessions as VEVENT entries. The `feed_token` is a random 32-char hex string.

Feed filtering via `ics_feed_config`: project filter, billable-only toggle, minimum session duration.

**Tuta setup flow:**

1. Enable ICS Feed in ChronoLens dashboard
2. Enable Cloudflare Tunnel with a stable domain
3. Public URL becomes: `https://time.example.com/api/calendar/feed/{token}.ics`
4. In Tuta Calendar → click "+" → "from URL" → paste URL

### CalDAV, ICS Export, Google Calendar

Same as v2 spec. CalDAV uses the `caldav` Python library. ICS Export generates downloadable `.ics` files. Google Calendar uses their REST API with OAuth2.

---

## 9. CLOUDFLARE TUNNEL INTEGRATION

### Purpose

Exposes the ICS feed and mobile API via a stable custom domain without opening firewall ports.

### Requirements

- Free Cloudflare account
- Domain with DNS on Cloudflare
- API token with `Zone:DNS:Edit` + `Account:Cloudflare Tunnel:Edit`
- `cloudflared` binary (auto-downloaded on first use)

### Tunnel Ingress Configuration

```json
{
  "config": {
    "ingress": [
      {
        "hostname": "time.example.com",
        "path": "api/calendar/feed/.*",
        "service": "http://localhost:19532"
      },
      {
        "hostname": "time.example.com",
        "path": "api/mobile/.*",
        "service": "http://localhost:19532"
      },
      {
        "service": "http_status:404"
      }
    ]
  }
}
```

Only the ICS feed and mobile API are exposed. Dashboard, main API, and WebSocket are never exposed.

### Setup Flow

Same 4-step wizard as v2:

1. Enter API token → validate → get account ID
2. Select domain from account's zones
3. Choose subdomain
4. Activate: create named tunnel, configure ingress, create DNS CNAME, start `cloudflared`

### cloudflared Binary Management

Per-platform download on first use:

- **Windows**: `cloudflared-windows-amd64.exe`
- **macOS**: `cloudflared-darwin-amd64.tgz` (or arm64 for Apple Silicon)
- **Linux**: `cloudflared-linux-amd64`

Stored in platform data directory under `bin/`. Checksum verified against GitHub releases.

---

## 10. REPORT & INVOICE GENERATION

### Report Types

| Type                | Description                                                              |
| ------------------- | ------------------------------------------------------------------------ |
| Time Summary        | Total hours per project/task for a date range, grouped by day/week/month |
| Billing Report      | Hours × hourly rate per project, billable vs non-billable                |
| Activity Breakdown  | Time distribution across task categories and applications                |
| Detailed Log        | Full session list with timestamps                                        |
| Productivity Report | Active vs idle, most productive hours, pomodoro completion rate          |

### Export Formats

PDF, CSV, JSON, ICS.

### Invoice Generation

Invoices are generated from tracked time data. The flow:

1. User navigates to Invoices page → "Create Invoice"
2. Selects project, date range
3. App auto-populates from tracked sessions:
   - Line items grouped by task category (e.g. "Development — coding: 15.5h", "DevOps — deployment: 3.2h")
   - Hours × hourly rate per line
   - Subtotal, VAT, total
4. User can edit line items, add custom lines, adjust amounts
5. User reviews and saves (status: `draft`)
6. "Generate PDF" creates a professional PDF invoice
7. "Mark as Sent" updates status + records `sent_at`
8. "Mark as Paid" updates status + records `paid_at`

### Invoice PDF Layout

Professional invoice PDF generated with `weasyprint` from an HTML/CSS template:

```
┌──────────────────────────────────────────────────────────────┐
│  [LOGO]                                    INVOICE           │
│  Your Company Name                                           │
│  Address Line 1                     Invoice #: INV-2025-042  │
│  1234 AB City                       Date: 2025-05-08         │
│  Netherlands                        Due: 2025-06-07          │
│  BTW: NL123456789B01                                         │
│  KVK: 12345678                                               │
│                                                              │
│  BILL TO:                                                    │
│  Client Company BV                                           │
│  Client Address                                              │
│  BTW: NL987654321B01                                         │
│                                                              │
│  ──────────────────────────────────────────────────────────  │
│  Description                    Hours    Rate    Amount      │
│  ──────────────────────────────────────────────────────────  │
│  Development — coding           15.50   €95.00   €1,472.50  │
│  Development — code review       4.25   €95.00   €  403.75  │
│  DevOps — deployment             3.00   €95.00   €  285.00  │
│  Communication — meetings        2.75   €95.00   €  261.25  │
│  ──────────────────────────────────────────────────────────  │
│                                Subtotal:         €2,422.50  │
│                                BTW (21%):        €  508.73  │
│                                ─────────────────────────────│
│                                TOTAL:            €2,931.23  │
│                                                              │
│  Payment Details:                                            │
│  IBAN: NL00 BANK 0123 4567 89                               │
│  BIC: BANKNNL2A                                              │
│  Reference: INV-2025-042                                     │
│                                                              │
│  Payment Terms: Net 30                                       │
│                                                              │
│  Notes: [optional custom notes]                              │
└──────────────────────────────────────────────────────────────┘
```

The HTML template should be customizable — stored as an HTML/CSS file that the user can modify for branding.

### Invoice Number Auto-Generation

Format: `{prefix}-{year}-{sequence}` e.g. `INV-2025-042`

The prefix and next sequence number are stored in `freelancer_profile`. The sequence auto-increments on each new invoice. The user can override the format.

---

## 11. POMODORO TIMER

### Concept

An integrated Pomodoro timer that tags tracked sessions with focus/break metadata. The timer runs alongside passive tracking — it doesn't replace it, it annotates it.

### Configuration (in Settings)

| Setting                        | Default | Description                               |
| ------------------------------ | ------- | ----------------------------------------- |
| `pomodoro_focus_minutes`       | 25      | Focus period duration                     |
| `pomodoro_short_break_minutes` | 5       | Short break duration                      |
| `pomodoro_long_break_minutes`  | 15      | Long break after N focus periods          |
| `pomodoro_long_break_interval` | 4       | Number of focus periods before long break |
| `pomodoro_auto_start_breaks`   | true    | Auto-start break timer when focus ends    |
| `pomodoro_auto_start_focus`    | false   | Auto-start next focus when break ends     |

### Timer States

```
IDLE → (user starts) → FOCUS → (timer ends) → SHORT_BREAK → (timer ends) → FOCUS → ...
                                                                              ↓ (after N cycles)
                                                                        LONG_BREAK → FOCUS
```

### Integration with Tracking

When a Pomodoro focus session is active:

- Activities recorded during that period are tagged with `pomodoro_session_id`
- The user can optionally assign a project + task to the Pomodoro session upfront
- Sessions that overlap with a Pomodoro focus period get `pomodoro_count` incremented
- The dashboard shows Pomodoro completion data alongside time tracking

### Timer Controls

Available from:

- System tray context menu (Start / Stop / Skip)
- Dashboard UI (dedicated Pomodoro widget)
- Mobile companion app
- Browser extension popup

### Notifications

When a timer period ends:

- System notification (OS-native) with sound
- Tray icon briefly changes to indicate timer state
- Dashboard updates in real-time via WebSocket
- Mobile push notification (if companion app is connected)

---

## 12. SYSTEM TRAY APPLICATION

### Technology

`pystray` for cross-platform tray/menu bar icon + `Pillow` for icon rendering.

### Tray Icon States

| State                     | Visual                        | Description                                            |
| ------------------------- | ----------------------------- | ------------------------------------------------------ |
| Tracking                  | Green circle                  | Actively capturing and classifying                     |
| Tracking + Pomodoro Focus | Green circle with timer badge | Focus session active                                   |
| Tracking + Pomodoro Break | Blue circle with pause badge  | Break period                                           |
| Paused                    | Yellow circle                 | User paused tracking                                   |
| Idle                      | Gray circle                   | System idle, capture paused                            |
| Error                     | Red circle                    | Capture error, LLM error, tunnel down                  |
| No LLM                    | Orange circle                 | No API key configured, tracking without classification |

### Context Menu

```
┌──────────────────────────────────────────┐
│ ● Tracking: Scenery en Zo — coding       │  ← live project + task
│ ⏱ 3h 42m today (2h 15m billable)        │  ← today's summary
│ 🍅 Focus: 18:32 remaining               │  ← pomodoro status (if active)
│ ──────────────────────────────────────── │
│ 📊 Open Dashboard                        │
│ ⏸ Pause Tracking                         │
│ ──────────────────────────────────────── │
│ 🍅 Start Focus (25 min)                  │  ← or "Stop Focus" if running
│ ⏭ Skip to Break                          │  ← only shown during focus
│ ──────────────────────────────────────── │
│ 🔄 Sync Calendar Now                     │
│ ⚙ Settings                               │
│ ──────────────────────────────────────── │
│ ✕ Quit ChronoLens                        │
└──────────────────────────────────────────┘
```

### Autostart

**Windows**: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key
**macOS**: `~/Library/LaunchAgents/com.chronolens.plist` launch agent
**Linux**: `~/.config/autostart/chronolens.desktop` XDG autostart entry

### Startup Sequence

```
1. Initialize platform-specific paths
2. Initialize SQLite database (create tables if first run, migrations, integrity check)
3. Load settings
4. Load PaddleOCR model
5. Start capture loop thread
6. Start LLM classification thread
7. Start session aggregation thread
8. Start Pomodoro timer thread
9. Start FastAPI/uvicorn thread on 127.0.0.1:19532
10. Start calendar sync scheduler
11. If Cloudflare tunnel configured + active → start cloudflared
12. Create system tray icon
13. If NOT --background → open dashboard in browser
```

### Shutdown Sequence

```
1. Stop capture loop
2. Flush pending classifications (process queue or save as pending)
3. Flush session data to database
4. Stop Pomodoro timer
5. Stop calendar sync scheduler
6. Stop cloudflared subprocess
7. Stop FastAPI/uvicorn
8. Close database connections
9. Remove tray icon
10. Exit
```

---

## 13. DASHBOARD UI

Angular 19+ with standalone components and signals. Served as static files by FastAPI.

### Pages

#### 13.1 Live View (Home — `/`)

- **Current activity card**: project (color-coded), task, application, live duration counter
- **Pomodoro widget**: current timer (if active), start button (if idle), today's completed count
- **Today's timeline**: horizontal stacked bar of color-coded sessions
- **Today's summary**: total tracked, billable, top projects, LLM API calls today
- **Unclassified sessions alert**: prominent banner if there are recent unclassified sessions to review
- Real-time via WebSocket

#### 13.2 Timeline (`/timeline`)

- Day / week / month view selector
- Horizontal stacked timeline bars per day
- Click session → detail panel: view, edit project/task, add notes, split, merge
- Filter: project, task category, application, confidence level, source (LLM/manual/pending)
- Bulk actions: select multiple → reassign / mark reviewed
- Pomodoro markers shown on timeline (tomato icons at focus session boundaries)

#### 13.3 Projects (`/projects`)

- Project list: name, client, rate, color, total hours, billable amount, active toggle
- Project detail: time trend chart, task breakdown pie, app usage, recent sessions
- CRUD with soft delete
- Link to client profile

#### 13.4 Clients (`/clients`)

- Client list with associated projects, total billed, outstanding invoices
- Client detail page: contact info, project history, invoice history
- CRUD for client profiles

#### 13.5 Reports (`/reports`)

- Report type tabs: Summary, Billing, Activity, Detailed Log, Productivity
- Date range picker with presets (today, this week, this month, last month, custom)
- Project filter (multi-select)
- Inline chart preview (Chart.js)
- Export: PDF, CSV, JSON
- Productivity report includes: active vs idle ratio, most productive hours, pomodoro stats

#### 13.6 Invoices (`/invoices`)

- Invoice list: number, client, project, period, total, status badge (draft/sent/paid/overdue)
- "Create Invoice" wizard:
  1. Select project + date range
  2. Auto-generated line items from tracked time (grouped by task category)
  3. Edit line items, add custom lines, adjust
  4. Review: preview the invoice layout
  5. Save as draft
- Invoice detail page:
  - Full invoice preview (rendered HTML matching PDF layout)
  - Actions: Generate PDF, Mark Sent, Mark Paid, Delete
  - Edit all fields
  - Download PDF
- **Freelancer profile** link: edit your business details, logo, bank info, VAT

#### 13.7 Calendar Sync (`/calendar`)

- **ICS Feed**: enable/disable, URL display with copy button, feed filters
- **Cloudflare Tunnel**: status, setup wizard, hostname display
- **Calendar providers**: CalDAV/Google config, sync status, manual sync
- Tuta-specific instructions panel

#### 13.8 Pomodoro (`/pomodoro`)

- Large timer display with start/stop/skip controls
- Optional project + task assignment for the focus session
- Today's Pomodoro history: completed/cancelled, durations
- Weekly/monthly Pomodoro stats: completion rate, average focus time, streaks
- Settings: durations, auto-start toggles

#### 13.9 Privacy & LLM (`/privacy`)

- **Privacy level selector**: Level 1-4 with clear descriptions of what each level redacts
- **Redaction preview tool**: paste text → see redacted output at current level
- **Custom redaction rules**: list, add, edit, delete
- **Redaction statistics**: chart showing daily redaction counts by category
- **LLM configuration**: provider selector, API key input, model selection
- **LLM usage dashboard**: daily/weekly/monthly API calls, tokens, estimated cost, cache hit rate
- **Monthly budget**: set cap, current spend, progress bar
- **Test classification**: run a sample through the full pipeline (OCR → redact → LLM)

#### 13.10 Settings (`/settings`)

- **Tracking**: capture interval, idle thresholds, min session duration
- **OCR**: enable/disable, downscale width, language
- **Billing defaults**: currency, default hourly rate
- **Startup**: autostart toggle
- **Multi-monitor**: select which monitors to capture (default: all), set primary
- **Data management**: export all data, import, reset database
- **About**: version, platform, database path + size, links

### Technical Notes

- Angular 19+ with standalone components
- State management via signals
- Lazy-loaded routes
- HTTP via `HttpClient` to `http://localhost:19532/api/`
- WebSocket for live view + Pomodoro ticks
- Charts via Chart.js
- No external CSS framework — custom styles

---

## 14. BROWSER EXTENSION

### Purpose

The browser extension provides richer context than window titles alone. It captures the exact URL, page title, and a snippet of page content, then sends this to ChronoLens via a local WebSocket or HTTP connection.

### Supported Browsers

- **Chrome / Chromium** (Manifest V3)
- **Firefox** (Manifest V2/V3 depending on current support)

### Architecture

```
Browser Extension (content script + background worker)
    │
    │ WebSocket or HTTP POST to localhost:19532
    │
    ▼
ChronoLens API Server
    │
    │ merges browser context into capture loop
    │
    ▼
Classification Pipeline
```

### Data Captured

| Field             | Source                                                               | Example                                                  |
| ----------------- | -------------------------------------------------------------------- | -------------------------------------------------------- |
| URL               | `tabs.query({active: true})`                                         | `https://github.com/org/repo/pull/42`                    |
| Page title        | `tab.title`                                                          | `"Fix login redirect — Pull Request #42"`                |
| Content snippet   | Content script: extract first 500 chars of `document.body.innerText` | `"This PR fixes the redirect loop after OAuth login..."` |
| Tab change events | `tabs.onActivated` listener                                          | Fires when user switches tabs                            |

### Communication Protocol

The extension connects to ChronoLens via WebSocket at `ws://localhost:19532/ws/browser-extension`:

```typescript
// Extension background worker
const ws = new WebSocket("ws://localhost:19532/ws/browser-extension");

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  // Get content snippet from content script
  const [result] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => document.body.innerText.substring(0, 500),
  });

  ws.send(
    JSON.stringify({
      type: "tab_context",
      url: tab.url,
      title: tab.title,
      content_snippet: result?.result || "",
      timestamp: Date.now(),
    }),
  );
});

// Also send on URL change within same tab
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url && tab.active) {
    // send updated context
  }
});
```

### Extension Popup

A small popup when clicking the extension icon:

- Connection status (connected / disconnected to ChronoLens)
- Current classification: "Project: Scenery en Zo — coding"
- Pomodoro timer display + start/stop button
- Quick project switch (override current classification)
- Link to open full dashboard

### Privacy

- The extension only sends data to `localhost` — never to any external server
- Content snippets are subject to the same redaction engine before being sent to the LLM
- The extension can be configured to exclude specific domains (e.g. banking sites, personal email)
- Extension has a domain blocklist in its own settings

### Extension Settings (in extension popup or options page)

- **Excluded domains**: list of domains where the extension won't capture content (e.g. `bank.example.com`, `mail.google.com`)
- **Content capture toggle**: disable content snippet capture entirely (only send URL + title)
- **Auto-connect**: automatically connect to ChronoLens on browser start

---

## 15. MOBILE COMPANION APP

### Purpose

View time tracking data, control the Pomodoro timer, and review reports from a phone. The mobile app is read-heavy, write-light — it doesn't do any tracking itself.

### Technology Options

Two approaches (implementer should choose based on team expertise):

1. **Progressive Web App (PWA)**: Angular-based, served from ChronoLens. Works in mobile browser. No app store needed. Lower effort.
2. **React Native**: Native app for iOS/Android. Better notifications, home screen widget. Higher effort.

**Recommendation: Start with PWA for v1.** If native features are needed later, build React Native for v2.

### Connectivity

The mobile app connects to ChronoLens via the Cloudflare Tunnel. All mobile endpoints are under `/api/mobile/*` and require bearer token authentication.

### Pairing Flow

1. In ChronoLens dashboard → Settings → Mobile → "Pair Device"
2. App generates a random auth token and displays it as a QR code
3. User scans QR code with phone camera or enters the token manually
4. QR code encodes: `chronolens://{hostname}/api/mobile?token={token}`
5. Mobile app stores the hostname + token for future requests

### Mobile Screens

#### Home

- Today's summary: total tracked, billable hours, top project
- Current activity: what's being tracked right now (live updates via polling)
- Pomodoro timer: current state, start/stop controls

#### Timeline

- Simplified daily view: list of sessions with project, task, duration
- Tap session to see details (read-only on mobile)

#### Projects

- Project list with hours and billable amounts
- Tap for project detail with time trend

#### Reports

- Simplified report views: summary, billing
- Date range picker
- Export not available on mobile (use desktop)

#### Pomodoro

- Large timer display
- Start / stop / skip controls
- Today's Pomodoro count
- Push notification when timer ends (PWA: web notification, Native: push)

### Push Notifications (PWA)

For PWA, use the Web Push API for Pomodoro timer notifications. Requires the Cloudflare Tunnel to be active (service worker needs HTTPS).

---

## 16. DIRECTORY STRUCTURE

```
chronolens/
├── chronolens/                         # Python package (backend)
│   ├── __init__.py
│   ├── __main__.py                     # Entry point
│   ├── app.py                          # FastAPI app + uvicorn
│   ├── tray.py                         # System tray (pystray)
│   ├── config.py                       # Paths, defaults, platform detection
│   │
│   ├── capture/
│   │   ├── __init__.py
│   │   ├── loop.py                     # 1-second capture loop
│   │   ├── screenshot.py              # mss multi-monitor capture
│   │   ├── window_info.py             # Active window (platform-dispatched)
│   │   ├── window_info_windows.py     # Windows: win32gui
│   │   ├── window_info_macos.py       # macOS: AppKit / Quartz
│   │   ├── window_info_linux.py       # Linux: Xdotool / sway IPC
│   │   ├── idle_detector.py           # Platform-dispatched idle detection
│   │   ├── idle_detector_windows.py   # Windows: GetLastInputInfo
│   │   ├── idle_detector_macos.py     # macOS: IOKit HID
│   │   ├── idle_detector_linux.py     # Linux: XScreenSaver / D-Bus
│   │   ├── change_detector.py         # Perceptual hash comparison
│   │   └── browser_bridge.py          # Receives context from browser extension
│   │
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── extractor.py              # PaddleOCR wrapper
│   │
│   ├── redaction/
│   │   ├── __init__.py
│   │   ├── engine.py                  # Main redaction orchestrator
│   │   ├── levels.py                  # Level 1-4 pattern definitions
│   │   ├── patterns.py                # All regex patterns organized by category
│   │   └── custom_rules.py            # User-defined pattern loader
│   │
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── pipeline.py                # Orchestrates: OCR → redact → LLM
│   │   ├── llm_client.py             # Abstract LLM client
│   │   ├── claude_client.py           # Anthropic API implementation
│   │   ├── openai_client.py           # OpenAI API implementation
│   │   ├── cache.py                   # Classification cache management
│   │   ├── cost_tracker.py            # Token counting + budget enforcement
│   │   └── prompts.py                 # System prompt + user prompt templates
│   │
│   ├── sessions/
│   │   ├── __init__.py
│   │   └── tracker.py                 # Session aggregation
│   │
│   ├── pomodoro/
│   │   ├── __init__.py
│   │   └── timer.py                   # Pomodoro state machine + notifications
│   │
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── provider.py                # Abstract base
│   │   ├── caldav_provider.py         # CalDAV (RFC 4791)
│   │   ├── ics_feed.py                # ICS feed generation (RFC 5545)
│   │   ├── ics_export.py              # ICS file export
│   │   ├── google_provider.py         # Google Calendar API
│   │   └── sync_service.py            # Orchestration + scheduling
│   │
│   ├── cloudflare/
│   │   ├── __init__.py
│   │   ├── api_client.py              # Cloudflare REST API
│   │   ├── tunnel_manager.py          # cloudflared subprocess
│   │   ├── setup.py                   # Setup wizard logic
│   │   └── binary.py                  # Download + verify cloudflared
│   │
│   ├── invoices/
│   │   ├── __init__.py
│   │   ├── generator.py               # Invoice creation from tracked time
│   │   ├── pdf_renderer.py            # HTML → PDF via weasyprint
│   │   └── templates/
│   │       ├── default.html            # Default invoice HTML template
│   │       └── default.css             # Default invoice styles
│   │
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py               # Report data aggregation
│   │   ├── pdf_export.py              # Report PDF rendering
│   │   └── csv_export.py              # CSV export
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_sessions.py
│   │   ├── routes_projects.py
│   │   ├── routes_clients.py
│   │   ├── routes_reports.py
│   │   ├── routes_invoices.py
│   │   ├── routes_calendar.py
│   │   ├── routes_cloudflare.py
│   │   ├── routes_pomodoro.py
│   │   ├── routes_llm.py
│   │   ├── routes_redaction.py
│   │   ├── routes_settings.py
│   │   ├── routes_mobile.py
│   │   ├── routes_profile.py
│   │   ├── websocket.py               # /ws/live + /ws/browser-extension
│   │   └── auth.py                    # Mobile token verification middleware
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py              # SQLite WAL, thread-local
│   │   ├── schema.py                  # Table creation + migrations
│   │   └── models.py                  # Pydantic models / dataclasses
│   │
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── keyring.py                 # Cross-platform credential storage
│   │   ├── keyring_windows.py         # Windows DPAPI
│   │   ├── keyring_macos.py           # macOS Keychain
│   │   └── keyring_linux.py           # Linux Secret Service / libsecret
│   │
│   ├── platform/
│   │   ├── __init__.py
│   │   ├── autostart.py               # Cross-platform autostart registration
│   │   ├── autostart_windows.py       # Registry
│   │   ├── autostart_macos.py         # LaunchAgent
│   │   ├── autostart_linux.py         # XDG desktop entry
│   │   ├── notifications.py           # Cross-platform notifications
│   │   └── paths.py                   # Platform data/config directories
│   │
│   └── static/                        # Angular production build
│
├── dashboard/                         # Angular 19+ project
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.component.ts
│   │   │   ├── app.routes.ts
│   │   │   │
│   │   │   ├── pages/
│   │   │   │   ├── live/              # Home — current activity + today
│   │   │   │   ├── timeline/          # Session timeline
│   │   │   │   ├── projects/          # Project management
│   │   │   │   ├── clients/           # Client profiles
│   │   │   │   ├── reports/           # Report generation
│   │   │   │   ├── invoices/          # Invoice management
│   │   │   │   ├── calendar/          # Calendar sync + Cloudflare
│   │   │   │   ├── pomodoro/          # Pomodoro timer + stats
│   │   │   │   ├── privacy/           # Redaction + LLM config
│   │   │   │   └── settings/          # App settings
│   │   │   │
│   │   │   ├── components/
│   │   │   │   ├── session-bar/
│   │   │   │   ├── time-chart/
│   │   │   │   ├── project-badge/
│   │   │   │   ├── pomodoro-widget/
│   │   │   │   ├── invoice-preview/
│   │   │   │   ├── redaction-preview/
│   │   │   │   ├── date-range-picker/
│   │   │   │   ├── tunnel-status/
│   │   │   │   ├── session-detail/
│   │   │   │   ├── llm-usage-chart/
│   │   │   │   └── qr-code/           # For mobile pairing
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── api.service.ts
│   │   │   │   ├── websocket.service.ts
│   │   │   │   └── settings.service.ts
│   │   │   │
│   │   │   └── models/
│   │   │       ├── session.model.ts
│   │   │       ├── project.model.ts
│   │   │       ├── client.model.ts
│   │   │       ├── invoice.model.ts
│   │   │       ├── pomodoro.model.ts
│   │   │       ├── report.model.ts
│   │   │       └── cloudflare.model.ts
│   │   │
│   │   ├── styles.css
│   │   └── index.html
│   │
│   ├── angular.json
│   ├── tsconfig.json
│   └── package.json
│
├── browser-extension/                 # Browser extension
│   ├── manifest.json                  # Chrome Manifest V3
│   ├── manifest.firefox.json          # Firefox variant
│   ├── background.js                  # Service worker: tab tracking, WebSocket
│   ├── content.js                     # Content script: page text extraction
│   ├── popup/
│   │   ├── popup.html                 # Extension popup UI
│   │   ├── popup.js
│   │   └── popup.css
│   ├── options/
│   │   ├── options.html               # Extension settings (excluded domains, etc.)
│   │   ├── options.js
│   │   └── options.css
│   └── icons/
│       ├── icon-16.png
│       ├── icon-48.png
│       └── icon-128.png
│
├── mobile/                            # Mobile companion (PWA)
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/
│   │   │   │   ├── home/
│   │   │   │   ├── timeline/
│   │   │   │   ├── projects/
│   │   │   │   ├── pomodoro/
│   │   │   │   └── pairing/          # QR scan / token entry
│   │   │   ├── services/
│   │   │   │   └── api.service.ts
│   │   │   └── models/
│   │   ├── manifest.webmanifest
│   │   ├── service-worker.js
│   │   └── index.html
│   ├── angular.json
│   └── package.json
│
├── assets/
│   ├── icon.ico
│   ├── icon.icns                      # macOS
│   ├── icon.png                       # Linux
│   ├── icon_tracking.png
│   ├── icon_paused.png
│   ├── icon_idle.png
│   ├── icon_error.png
│   ├── icon_pomodoro_focus.png
│   └── icon_pomodoro_break.png
│
├── requirements.txt
├── pyproject.toml
├── README.md
└── installer/
    ├── windows/
    │   └── chronolens.nsi             # NSIS installer
    ├── macos/
    │   └── build_dmg.sh               # DMG builder script
    └── linux/
        ├── chronolens.desktop         # XDG desktop entry
        └── build_appimage.sh          # AppImage builder
```

---

## 17. TECH STACK

| Component             | Technology                                 | Rationale                                                          |
| --------------------- | ------------------------------------------ | ------------------------------------------------------------------ |
| Backend language      | Python 3.12+                               | Best ecosystem for OCR, screen capture, cross-platform system APIs |
| System tray           | pystray + Pillow                           | Cross-platform tray/menu bar                                       |
| Screen capture        | mss                                        | Cross-platform, shared memory, multi-monitor                       |
| OCR                   | PaddleOCR (CPU mode)                       | Best accuracy-to-speed without GPU                                 |
| Image hashing         | imagehash                                  | Perceptual hash for change detection                               |
| Window info (Windows) | pywin32                                    | Native Win32 API                                                   |
| Window info (macOS)   | pyobjc (AppKit, Quartz)                    | Native macOS API                                                   |
| Window info (Linux)   | python-xlib / subprocess (xdotool)         | X11; sway IPC for Wayland                                          |
| Idle detection        | Platform-specific (see §18)                | Per-platform native API                                            |
| API server            | FastAPI + uvicorn                          | Async, fast, OpenAPI auto-docs                                     |
| Database              | SQLite (WAL mode)                          | Zero-config, single-file, cross-platform                           |
| LLM (Claude)          | httpx → Anthropic Messages API             | Async HTTP                                                         |
| LLM (OpenAI)          | httpx → OpenAI Chat Completions API        | Async HTTP                                                         |
| Calendar (iCal)       | icalendar                                  | RFC 5545                                                           |
| Calendar (CalDAV)     | caldav                                     | RFC 4791                                                           |
| Cloudflare API        | httpx                                      | Async                                                              |
| Scheduling            | APScheduler                                | Calendar sync jobs                                                 |
| Invoice PDF           | weasyprint                                 | HTML/CSS → PDF                                                     |
| Report PDF            | weasyprint                                 | Same engine                                                        |
| Credential storage    | keyring (or platform-specific)             | Cross-platform secrets                                             |
| Notifications         | plyer or platform-specific                 | Cross-platform notifications                                       |
| Frontend              | Angular 19+                                | Standalone components, signals                                     |
| Charts                | Chart.js (ng2-charts)                      | Lightweight                                                        |
| Browser extension     | Chrome Manifest V3 + Firefox WebExtensions | Cross-browser                                                      |
| Mobile companion      | Angular PWA                                | Reuses Angular expertise, no app store                             |
| Packaging (Windows)   | PyInstaller + NSIS                         | .exe + installer                                                   |
| Packaging (macOS)     | PyInstaller + py2app                       | .app + .dmg                                                        |
| Packaging (Linux)     | PyInstaller + AppImage                     | Portable Linux package                                             |

### Python Dependencies

```
fastapi>=0.110
uvicorn[standard]>=0.29
pystray>=0.19
Pillow>=10.0
mss>=9.0
paddleocr>=2.7
paddlepaddle>=2.6
imagehash>=4.3
psutil>=5.9
httpx>=0.27
icalendar>=5.0
caldav>=1.3
apscheduler>=3.10
weasyprint>=62
pydantic>=2.6
numpy>=1.26
opencv-python-headless>=4.9
keyring>=25.0
plyer>=2.1

# Platform-specific (conditional):
# Windows: pywin32>=306
# macOS: pyobjc-core, pyobjc-framework-Cocoa, pyobjc-framework-Quartz
# Linux: python-xlib (for X11)
```

---

## 18. CROSS-PLATFORM CONSIDERATIONS

### Platform Abstraction Pattern

All platform-specific code goes in platform-dispatched modules. The main code imports a unified interface:

```python
# window_info.py (dispatcher)
import platform

if platform.system() == "Windows":
    from .window_info_windows import get_active_window_title, get_active_process, get_focused_monitor
elif platform.system() == "Darwin":
    from .window_info_macos import get_active_window_title, get_active_process, get_focused_monitor
else:
    from .window_info_linux import get_active_window_title, get_active_process, get_focused_monitor
```

### Window Information

| Platform                 | Active Window Title                                                                         | Process Name                                                             | Focused Monitor                        |
| ------------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------- |
| **Windows**              | `win32gui.GetWindowText(win32gui.GetForegroundWindow())`                                    | `psutil.Process(pid).name()` via `win32process.GetWindowThreadProcessId` | `win32api.MonitorFromWindow`           |
| **macOS**                | `NSWorkspace.sharedWorkspace().frontmostApplication()` + Accessibility API for window title | `frontmostApplication().localizedName()`                                 | `NSScreen.screens()` + window position |
| **Linux (X11)**          | `xdotool getactivewindow getwindowname` or `python-xlib`                                    | `_NET_WM_PID` property → `psutil`                                        | `_NET_WM_DESKTOP` + `xrandr`           |
| **Linux (Wayland/Sway)** | `swaymsg -t get_tree` → find focused node                                                   | From sway tree                                                           | From sway output info                  |

### Idle Detection

| Platform            | Method                                                        |
| ------------------- | ------------------------------------------------------------- |
| **Windows**         | `GetLastInputInfo` via `ctypes`                               |
| **macOS**           | `IOKit` HID idle time: `IOHIDGetParameter(kIOHIDIdleTimeKey)` |
| **Linux (X11)**     | `XScreenSaverQueryInfo` via `python-xlib` or `xprintidle`     |
| **Linux (Wayland)** | `org.freedesktop.ScreenSaver` D-Bus interface, or `swayidle`  |

### Autostart

| Platform    | Method                                                         |
| ----------- | -------------------------------------------------------------- |
| **Windows** | Registry: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| **macOS**   | LaunchAgent plist in `~/Library/LaunchAgents/`                 |
| **Linux**   | `.desktop` file in `~/.config/autostart/` (XDG spec)           |

### Credential Storage

| Platform    | Method                                                                       |
| ----------- | ---------------------------------------------------------------------------- |
| **Windows** | Windows DPAPI via `win32crypt.CryptProtectData`                              |
| **macOS**   | macOS Keychain via `keyring` library (SecItemAdd)                            |
| **Linux**   | GNOME Keyring or KDE Wallet via `keyring` library (Secret Service D-Bus API) |

Use the `keyring` Python library for a unified API. Fall back to encrypted file if no keyring is available.

### Data Directories

| Platform    | Data                                        | Config                  |
| ----------- | ------------------------------------------- | ----------------------- |
| **Windows** | `%APPDATA%/ChronoLens/`                     | Same                    |
| **macOS**   | `~/Library/Application Support/ChronoLens/` | Same                    |
| **Linux**   | `~/.local/share/chronolens/`                | `~/.config/chronolens/` |

### Notifications

| Platform    | Method                                                             |
| ----------- | ------------------------------------------------------------------ |
| **Windows** | `win10toast` or Windows Toast via `plyer`                          |
| **macOS**   | `osascript` or `pyobjc` `NSUserNotificationCenter`                 |
| **Linux**   | `notify-send` via `plyer` or D-Bus `org.freedesktop.Notifications` |

### Screen Capture

`mss` handles all platforms natively. Multi-monitor works identically on all three.

### cloudflared Binary

| Platform                  | Binary                                                           |
| ------------------------- | ---------------------------------------------------------------- |
| **Windows**               | `cloudflared-windows-amd64.exe`                                  |
| **macOS (Intel)**         | `cloudflared-darwin-amd64.tgz`                                   |
| **macOS (Apple Silicon)** | `cloudflared-darwin-arm64.tgz` (detect via `platform.machine()`) |
| **Linux**                 | `cloudflared-linux-amd64` (or arm64)                             |

---

## 19. PERFORMANCE BUDGET

| Metric                 | Target          | Notes                                             |
| ---------------------- | --------------- | ------------------------------------------------- |
| CPU (unchanged screen) | < 1%            | Hash compare only                                 |
| CPU (screen changing)  | < 5%            | OCR ~2-4x per minute                              |
| RAM                    | < 200 MB        | Python + PaddleOCR + classification queue         |
| VRAM                   | 0               | Everything CPU-only                               |
| Disk (DB growth)       | ~5-10 MB/month  | Activities + sessions + LLM logs                  |
| LLM API calls          | ~2-4/min active | Change detection + cache reduces dramatically     |
| LLM monthly cost       | Varies          | With cache: estimated $1-5/month at typical usage |
| API response time      | < 50ms          | SQLite + indices, all local                       |
| Dashboard load         | < 2s            | Static Angular from localhost                     |
| cloudflared overhead   | ~10 MB RAM      | Lightweight Go binary                             |

---

## 20. SECURITY CONSIDERATIONS

| Concern                | Mitigation                                                             |
| ---------------------- | ---------------------------------------------------------------------- |
| Network exposure       | FastAPI binds to `127.0.0.1` only                                      |
| Tunnel scope           | Ingress only routes `/api/calendar/feed/*` and `/api/mobile/*`         |
| ICS feed auth          | Random 32-char hex token in URL path                                   |
| Mobile API auth        | Bearer token in Authorization header                                   |
| Credential storage     | Platform keyring (DPAPI / Keychain / Secret Service)                   |
| LLM data leakage       | Multi-level redaction engine strips sensitive content before API calls |
| OCR text storage       | Only first 200 chars of REDACTED text stored (not raw)                 |
| Keylogging prevention  | Never record keystrokes — event count only                             |
| Database integrity     | WAL mode + integrity check on startup                                  |
| cloudflared binary     | Official GitHub release + checksum verification                        |
| Invoice data           | Stored locally only, PDFs in local filesystem                          |
| Browser extension      | Communicates only with localhost, never external                       |
| Custom redaction rules | User can add patterns for client-specific sensitive terms              |

---

## 21. BUILD & PACKAGING

### Development

```bash
# Backend
cd chronolens
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m chronolens

# Dashboard (separate terminal)
cd dashboard
npm install
ng serve --proxy-config proxy.conf.json

# Browser Extension
cd browser-extension
# Load unpacked in Chrome: chrome://extensions → Load unpacked → select folder

# Mobile PWA (separate terminal)
cd mobile
npm install
ng serve --port 4300
```

### Production Build

```bash
# Dashboard
cd dashboard && ng build --configuration=production --output-path=../chronolens/static

# Mobile PWA
cd mobile && ng build --configuration=production --output-path=../chronolens/static/mobile

# Package
pyinstaller --onedir --noconsole --name ChronoLens \
    --add-data "chronolens/static:static" \
    --add-data "chronolens/invoices/templates:invoices/templates" \
    chronolens/__main__.py
```

### Platform Packaging

**Windows**: PyInstaller → NSIS installer (.exe)
**macOS**: PyInstaller → .app bundle → .dmg
**Linux**: PyInstaller → AppImage

### Browser Extension Publishing

- **Chrome Web Store**: Package as .zip, submit for review
- **Firefox Add-ons**: Package as .xpi, submit for review

---

## 22. FUTURE ENHANCEMENTS (Out of Scope for v1)

Do not implement these:

- Team mode with shared server and multi-user auth
- AI-powered project detection learning (auto-improve classifications from corrections)
- Tuta direct API integration (if/when they expose one)
- Desktop widgets (Windows/macOS native)
- Time tracking for non-computer work (manual entries with categories)
- Integration with project management tools (Jira, Linear, Asana)
- Git commit correlation (match tracked time to specific commits)
- Automatic screenshot archival (optional, for proof-of-work billing)
- White-label / multi-tenant SaaS version
- Local LLM fallback via Ollama (for offline or privacy-maximum mode)
