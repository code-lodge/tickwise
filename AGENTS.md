# ChronoLens — Engineering Workflow

You are an AI coding agent building ChronoLens. This document defines **how** you work — your development practices, quality standards, and workflow discipline. Read this before touching any code. It applies to every phase, every file, every commit.

---

## COMPANION DOCUMENTS

This is one of four documents that together form the complete project handoff:

| Document                       | Purpose                                                                       | Read When                                                                      |
| ------------------------------ | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **`specification.md`**         | **What** to build — architecture, schemas, APIs, features                     | Before implementing any feature                                                |
| **`implementation-phases.md`** | **When** to build it — 12 phases, ordering, dependencies, acceptance criteria | At the start of each phase                                                     |
| **`AGENTS.md`**                | **How** to work — this document: practices, testing, commits, quality         | Always; re-read when in doubt                                                  |
| **`engineering-ontology.md`**  | **Why** these standards — the canonical engineering standards reference       | When making architectural decisions, choosing patterns, or resolving ambiguity |

### How These Documents Interact

```
engineering-ontology.md                    ← The authority. Defines WHICH standards apply.
        │
        ├── Referenced by §16 of this doc  ← Maps ontology standards to ChronoLens code.
        │
        └── Informs the build spec         ← Spec decisions trace to ontology standards.

chronolens-build-spec-v3.md                ← The spec. Defines WHAT to build.
        │
        ├── Referenced by §2 of this doc   ← "Read the spec before coding."
        │
        └── Consumed by phases doc         ← Phases break the spec into ordered work.

chronolens-implementation-phases.md        ← The plan. Defines WHEN to build it.
        │
        └── Referenced by §2 of this doc   ← "Read the phase before starting it."

chronolens-engineering-workflow.md          ← This doc. Defines HOW to work.
        │
        └── Applied during every phase     ← Testing, commits, quality, standards.
```

**Rule: when the ontology and this document conflict, the ontology wins.** The ontology is the upstream authority for which standards apply. This document maps those standards to ChronoLens-specific implementation.

---

## TABLE OF CONTENTS

1. [Core Principles](#1-core-principles)
2. [Development Workflow](#2-development-workflow)
3. [Git Discipline](#3-git-discipline)
4. [Testing Strategy](#4-testing-strategy)
5. [Code Quality Standards](#5-code-quality-standards)
6. [Documentation](#6-documentation)
7. [Error Handling & Logging](#7-error-handling--logging)
8. [Security Practices](#8-security-practices)
9. [Performance Discipline](#9-performance-discipline)
10. [Cross-Platform Discipline](#10-cross-platform-discipline)
11. [Database Discipline](#11-database-discipline)
12. [API Design Discipline](#12-api-design-discipline)
13. [Frontend Discipline](#13-frontend-discipline)
14. [Dependency Management](#14-dependency-management)
15. [Debugging & Troubleshooting](#15-debugging--troubleshooting)
16. [Standards Compliance Matrix](#16-standards-compliance-matrix)

---

## 1. CORE PRINCIPLES

These are non-negotiable. If you're ever uncertain about a decision, fall back to these:

**1. Working software over comprehensive code.** Get something running first, then refine. But "running" means tested and documented — not hacked together.

**2. Test before you move on.** Every function, every endpoint, every UI component gets tested before you start the next piece. No "I'll add tests later." You won't. (See `engineering-ontology.md` §17 — Testing Taxonomy.)

**3. Commit incrementally.** Small, focused commits with clear messages. Never commit a phase as a single giant blob. If you can't describe what a commit does in one sentence, it's too big. (See `engineering-ontology.md` §24.2 — Conventional Commits.)

**4. Document as you build.** Docstrings on every public function, module-level docstrings explaining purpose, inline comments for non-obvious logic. If you write code that makes you think "this is clever," add a comment explaining why. (See `engineering-ontology.md` §24.2 — Documentation Standards.)

**5. Fail loudly, recover gracefully.** Log errors clearly. Never silently swallow exceptions. But also never crash the whole app because of a non-critical failure. The capture loop crashing is critical. A single LLM API call timing out is not.

**6. Read the spec.** Before implementing any feature, re-read the relevant section of `chronolens-build-spec-v3.md`. The spec contains deliberate decisions. If you deviate from the spec, document why in the commit message and in a code comment.

**7. Read the phase.** Before starting a phase, re-read its entry in `chronolens-implementation-phases.md`. Check which spec sections it references, which files it expects, and verify all acceptance criteria are understood before writing code.

**8. One thing at a time.** Don't jump ahead. Don't partially implement three features. Finish one, test it, commit it, then start the next.

---

## 2. DEVELOPMENT WORKFLOW

### 2.1 Per-Feature Workflow

For every discrete feature or component, follow this cycle:

```
1. READ    — Re-read the relevant spec section(s) in chronolens-build-spec-v3.md
2. PLAN    — Identify files to create/modify, interfaces, dependencies
3. STUB    — Write function signatures, type hints, docstrings (no implementation)
4. TEST    — Write unit tests for the stubs (they will fail — that's correct)
5. IMPL    — Implement until all tests pass
6. VERIFY  — Run the full test suite, not just your new tests
7. LINT    — Run linter and type checker, fix all issues
8. DOC     — Update/write documentation (docstrings, README, CHANGELOG)
9. COMMIT  — Atomic commit with descriptive message
10. REVIEW — Manually test the feature end-to-end (does it actually work in the app?)
```

### 2.2 Per-Phase Workflow

At the start of each phase:

```
1. Read the phase description in chronolens-implementation-phases.md
2. Read ALL referenced spec sections in chronolens-build-spec-v3.md
3. Check the ontology (engineering-ontology.md) for relevant standards in the phase's domain
4. List all files to be created or modified
5. Identify the implementation order (dependencies within the phase)
6. Work through features in order, following the per-feature cycle
7. At the end, run ALL tests (not just this phase's tests)
8. Walk through ALL acceptance criteria for the phase
9. Only then tag and merge
```

### 2.3 Work in Progress Discipline

- Never leave the codebase in a broken state at end of a session
- If you can't finish a feature, stub it cleanly with `raise NotImplementedError("TODO: description")`
- Use `# TODO(phase-N):` comments for known work deferred to later phases
- Never commit code with `print()` debug statements — use the logging framework

---

## 3. GIT DISCIPLINE

### 3.1 Repository Initialization

```bash
git init
git add .gitignore README.md
git commit -m "chore: initialize repository"
```

`.gitignore` must include at minimum:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project
*.db
*.db-wal
*.db-shm
chronolens/static/
node_modules/

# Secrets (NEVER commit)
.env
*.pem
*.key
```

### 3.2 Branch Strategy

```
main                    ← always stable, always passes tests
├── phase/0-foundation
├── phase/1-tracking
├── phase/2-cross-platform
├── phase/3-classification
├── ...
└── phase/11-packaging
```

Each phase gets a branch. Merge into `main` only when all phase acceptance criteria from `chronolens-implementation-phases.md` pass. If working solo, commit directly to the phase branch and merge when done.

### 3.3 Commit Message Format

Use conventional commits (`engineering-ontology.md` §24.2 — `conventional_commits`). Every commit message has a type, scope, and description:

```
<type>(<scope>): <description>

[optional body explaining WHY, not WHAT]
```

**Types:**

| Type       | When                                       |
| ---------- | ------------------------------------------ |
| `feat`     | New feature or capability                  |
| `fix`      | Bug fix                                    |
| `test`     | Adding or updating tests                   |
| `refactor` | Code restructuring without behavior change |
| `docs`     | Documentation only                         |
| `chore`    | Build, config, tooling changes             |
| `perf`     | Performance improvement                    |
| `style`    | Formatting, linting (no logic change)      |
| `security` | Security fix or hardening                  |

**Scopes** (map to code areas):

`capture`, `ocr`, `redaction`, `classification`, `sessions`, `pomodoro`, `calendar`, `cloudflare`, `invoices`, `reports`, `api`, `db`, `tray`, `platform`, `dashboard`, `extension`, `mobile`, `config`

**Examples:**

```
feat(capture): implement 1-second capture loop with mss screenshot

feat(redaction): add Level 1 pattern matching for API keys and secrets

test(redaction): add unit tests for all Level 2 PII patterns

fix(classification): handle malformed JSON response from LLM API

refactor(sessions): extract merge logic into dedicated method

docs(api): add OpenAPI descriptions to all session endpoints

chore: update requirements.txt with pinned paddleocr version

perf(ocr): reduce downscale resolution from 1920 to 1280px width

security(redaction): add JWT detection pattern to Level 1
```

### 3.4 Commit Granularity

A single commit should represent **one logical change**. Guidelines:

- Adding a new file with its tests: 1-2 commits (implementation + tests, or both together if small)
- Adding a new API route: 1 commit (route + handler + schema)
- Adding a new dashboard page: 2-3 commits (component, service integration, styling)
- Bug fix: 1 commit (fix + test that verifies the fix)
- Refactoring: 1 commit per refactoring operation

**Anti-patterns** (never do these):

```
# TOO BIG — impossible to review or revert:
feat: implement entire LLM classification pipeline

# TOO VAGUE — what did you actually change?
fix: stuff

# MISLEADING TYPE — this isn't a feature if tests are failing:
feat(capture): wip capture loop (tests broken)
```

### 3.5 Tagging

Tag at the end of each phase (versions from `chronolens-implementation-phases.md` §Versioning Strategy):

```bash
git tag -a v0.1.0 -m "Phase 0: Foundation scaffolding complete"
git tag -a v0.2.0 -m "Phase 1: Core tracking loop working"
# ...
git tag -a v1.0.0 -m "Phase 11: Release candidate"
```

Use semantic versioning per `engineering-ontology.md` §24.1 (`semver`).

---

## 4. TESTING STRATEGY

### 4.1 Ontology Alignment

This project's testing approach is grounded in:

- **ISO 29119** (`engineering-ontology.md` §17) — testing levels and types
- **IEEE 730** (`engineering-ontology.md` §17.5) — quality assurance processes
- **ISO 25010** (`engineering-ontology.md` §17.5) — quality characteristics that tests must verify
- **TDD cycle** (`engineering-ontology.md` §17.3) — red → green → refactor

### 4.2 Testing Pyramid

```
         ╱╲
        ╱  ╲        E2E Tests (few, slow, critical paths)
       ╱────╲       - Full app startup → capture → classify → show in dashboard
      ╱      ╲
     ╱        ╲     Integration Tests (moderate count)
    ╱──────────╲    - API routes with real DB
   ╱            ╲   - Capture loop with mock screenshot
  ╱              ╲  - LLM client with mock HTTP
 ╱────────────────╲
╱                  ╲ Unit Tests (many, fast, isolated)
╱────────────────────╲ - Redaction patterns, session merging, cache logic
```

### 4.3 Python Testing

**Framework:** `pytest` with `pytest-asyncio` for async code.

**Directory structure:**

```
tests/
├── conftest.py                      # Shared fixtures: temp DB, mock settings, sample data
├── unit/
│   ├── test_redaction_level1.py
│   ├── test_redaction_level2.py
│   ├── test_redaction_level3.py
│   ├── test_redaction_level4.py
│   ├── test_redaction_custom.py
│   ├── test_change_detector.py
│   ├── test_session_tracker.py
│   ├── test_classification_cache.py
│   ├── test_cost_tracker.py
│   ├── test_pomodoro_state_machine.py
│   ├── test_invoice_generator.py
│   ├── test_ics_feed.py
│   └── test_platform_paths.py
├── integration/
│   ├── test_api_sessions.py
│   ├── test_api_projects.py
│   ├── test_api_invoices.py
│   ├── test_api_redaction.py
│   ├── test_api_llm.py
│   ├── test_capture_pipeline.py
│   ├── test_classification_pipeline.py
│   ├── test_calendar_sync.py
│   └── test_cloudflare_setup.py
└── e2e/
    ├── test_full_tracking_cycle.py
    └── test_invoice_generation.py
```

**Fixtures** (`conftest.py`):

```python
import pytest
import tempfile
import os
from chronolens.db.connection import get_db, init_db
from chronolens.db.schema import create_tables

@pytest.fixture
def temp_db(tmp_path):
    """Fresh SQLite database for each test."""
    db_path = tmp_path / "test.db"
    os.environ["CHRONOLENS_DB_PATH"] = str(db_path)
    conn = get_db(str(db_path))
    create_tables(conn)
    yield conn
    conn.close()

@pytest.fixture
def sample_projects(temp_db):
    """Insert sample projects and return their IDs."""
    cursor = temp_db.cursor()
    cursor.execute("INSERT INTO projects (name, client, hourly_rate) VALUES (?, ?, ?)",
                   ("Project Alpha", "Client A", 95.0))
    cursor.execute("INSERT INTO projects (name, client, hourly_rate) VALUES (?, ?, ?)",
                   ("Project Beta", "Client B", 85.0))
    temp_db.commit()
    return [1, 2]

@pytest.fixture
def redaction_engine():
    """RedactionEngine at default Level 2 with no custom rules."""
    from chronolens.redaction.engine import RedactionEngine
    return RedactionEngine(privacy_level=2, custom_rules=[])

@pytest.fixture
def mock_llm_response():
    """Standard LLM classification response."""
    return {
        "project": "Project Alpha",
        "task": "coding",
        "confidence": 0.92,
        "reasoning": "User is editing Python code in PhpStorm for Project Alpha"
    }
```

### 4.4 What to Test

**Always unit test:**

- Every redaction pattern at every level (including edge cases: empty string, Unicode, overlapping matches)
- Session merging logic (gap detection, idle splitting, minimum duration)
- Classification cache (hit, miss, expiry, key computation)
- Cost tracker (token estimation, budget enforcement, monthly reset)
- Pomodoro state machine (all transitions, auto-start, timer accuracy)
- Invoice calculations (hours aggregation, line items, VAT, totals, rounding)
- ICS feed generation (RFC 5545 compliance, VEVENT structure)
- Platform path resolution (test on current platform at minimum)
- Change detector (hamming distance threshold, edge cases)
- Database migrations (upgrade from each version to the next)

**Always integration test:**

- Every API endpoint (happy path + error cases + auth for mobile endpoints)
- Capture loop with mocked screenshot (verify it calls OCR only on change)
- Classification pipeline with mocked LLM (verify redaction → cache check → API call → store)
- Calendar sync with mock CalDAV server
- Cloudflare setup with mocked Cloudflare API responses

**Always E2E test (at phase completion):**

- Full startup → capture → classify → session appears in API → session appears in dashboard
- Create invoice from tracked time → generate PDF → verify PDF content

### 4.5 Test Naming

```python
# Pattern: test_{what}_{when/condition}_{expected_outcome}

def test_redact_api_key_with_sk_prefix_replaces_with_placeholder():
    ...

def test_session_merge_within_threshold_creates_single_session():
    ...

def test_classify_when_budget_exceeded_marks_pending():
    ...

def test_invoice_total_with_21_percent_vat_calculates_correctly():
    ...
```

### 4.6 Testing Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chronolens --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run a specific test file
pytest tests/unit/test_redaction_level2.py

# Run tests matching a pattern
pytest -k "redaction and level2"

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x
```

### 4.7 Coverage Requirements

Per `engineering-ontology.md` §17.4 — Code Coverage (general threshold: 80% line coverage minimum):

| Area              | Minimum Coverage | Rationale                                    |
| ----------------- | ---------------- | -------------------------------------------- |
| `redaction/`      | 95%              | Security-critical: data leaves the machine   |
| `classification/` | 85%              | Core business logic                          |
| `sessions/`       | 90%              | Time tracking accuracy is the product        |
| `invoices/`       | 90%              | Money calculations must be correct           |
| `api/`            | 80%              | All endpoints have at least happy-path tests |
| `capture/`        | 70%              | Platform-specific code is harder to test     |
| `pomodoro/`       | 85%              | State machine needs full transition coverage |
| `calendar/`       | 75%              | RFC compliance matters                       |
| `cloudflare/`     | 70%              | Relies on external API                       |
| Overall           | 80%              | ISO 29119 general threshold                  |

### 4.8 Angular Testing

```bash
# Run Angular tests
cd dashboard && ng test --watch=false --browsers=ChromeHeadless

# Run with coverage
ng test --watch=false --code-coverage
```

Test all services (API calls with `HttpClientTestingModule`), components (render + interaction), and pipes/utils (pure logic).

### 4.9 Mocking External Services

Never call real external APIs in automated tests. Mock them:

```python
# Mock LLM API
from unittest.mock import AsyncMock, patch

@patch("chronolens.classification.claude_client.httpx.AsyncClient.post")
async def test_classify_with_claude(mock_post, mock_llm_response):
    mock_post.return_value = MockResponse(json={
        "content": [{"type": "text", "text": json.dumps(mock_llm_response)}]
    })
    result = await classify_with_claude(prompt, config)
    assert result["project"] == "Project Alpha"

# Mock Cloudflare API
@patch("chronolens.cloudflare.api_client.httpx.AsyncClient")
async def test_create_tunnel(mock_client):
    mock_client.return_value.post.return_value = MockResponse(json={
        "result": {"id": "tunnel-123", "token": "tok-abc"}
    })
    ...
```

---

## 5. CODE QUALITY STANDARDS

### 5.1 Ontology Alignment

Code quality practices are drawn from `engineering-ontology.md` §24.4:

| Ontology Entry                | Applied Tool                                  |
| ----------------------------- | --------------------------------------------- |
| `python: ruff / pylint`       | `ruff` for linting                            |
| `python: black / ruff format` | `black` for formatting                        |
| `javascript: eslint`          | `eslint` with `@angular-eslint` for dashboard |
| `javascript: prettier`        | `prettier` for TypeScript formatting          |
| `cyclomatic_complexity` ≤ 10  | Enforced by `ruff` rules                      |

### 5.2 Python Style

- **Follow PEP 8** strictly. No exceptions.
- **Line length**: 120 characters max (not 79 — modern tooling handles this)
- **Formatter**: `black` with `--line-length 120`
- **Linter**: `ruff` (replaces flake8, isort, pyupgrade, and more)
- **Type checker**: `mypy` with `--strict` on new code
- **Import sorting**: `ruff` handles this (isort-compatible)

### 5.3 Tooling Configuration

`pyproject.toml`:

```toml
[tool.black]
line-length = 120
target-version = ["py312"]

[tool.ruff]
line-length = 120
target-version = "py312"
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
    "RUF",  # ruff-specific
    "S",    # flake8-bandit (security)
    "C90",  # mccabe complexity
]

[tool.ruff.mccabe]
max-complexity = 10  # engineering-ontology.md §24.4 — cyclomatic_complexity ≤ 10

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 5.4 Pre-Commit Checks

Before every commit, run:

```bash
black chronolens/ tests/
ruff check chronolens/ tests/ --fix
mypy chronolens/
pytest
```

If any of these fail, do not commit. Fix the issues first.

Consider setting up `pre-commit` hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks # engineering-ontology.md §19.7 — secrets scanning
```

### 5.5 Type Hints

Type hints are **required** on all function signatures. No exceptions.

```python
# CORRECT
def compute_cache_key(redacted_text: str, process_name: str) -> str:
    ...

async def classify(context: ClassificationContext, config: LLMConfig) -> ClassificationResult:
    ...

def merge_sessions(sessions: list[Session], threshold_seconds: int = 120) -> list[Session]:
    ...

# WRONG — no type hints
def compute_cache_key(redacted_text, process_name):
    ...
```

Use Pydantic models for complex data structures:

```python
from pydantic import BaseModel

class ClassificationResult(BaseModel):
    project: str | None
    task: str
    confidence: float
    reasoning: str
```

### 5.6 TypeScript Style (Dashboard / Mobile / Extension)

- **Strict mode**: `"strict": true` in `tsconfig.json`
- **Formatter**: Prettier
- **Linter**: ESLint with `@angular-eslint` for dashboard
- **No `any` types**: use proper interfaces and generics
- **Use Angular signals** for state management, not RxJS Subjects (unless specifically needed for streams like WebSocket)

### 5.7 Naming Conventions

**Python:**

| Kind       | Convention            | Example                    |
| ---------- | --------------------- | -------------------------- |
| Module     | `snake_case`          | `session_tracker.py`       |
| Class      | `PascalCase`          | `RedactionEngine`          |
| Function   | `snake_case`          | `compute_phash()`          |
| Constant   | `UPPER_SNAKE`         | `PHASH_CHANGE_THRESHOLD`   |
| Private    | `_leading_underscore` | `_apply_level2_patterns()` |
| Type alias | `PascalCase`          | `MonitorIndex = int`       |

**TypeScript:**

| Kind      | Convention                   | Example                              |
| --------- | ---------------------------- | ------------------------------------ |
| File      | `kebab-case`                 | `session-detail.component.ts`        |
| Class     | `PascalCase`                 | `SessionDetailComponent`             |
| Interface | `PascalCase`                 | `Session`, `Project` (no `I` prefix) |
| Method    | `camelCase`                  | `getSessions()`                      |
| Constant  | `UPPER_SNAKE` or `camelCase` | `API_BASE_URL` or `apiBaseUrl`       |
| Signal    | `camelCase`                  | `currentSession`                     |

### 5.8 Code Smells to Avoid

- Functions longer than 50 lines — extract helper functions
- Classes with more than 10 public methods — split responsibilities (SRP from `engineering-ontology.md` §9.2 — SOLID)
- Deeply nested conditionals (3+ levels) — use early returns or extract
- Magic numbers — define as named constants with comments
- Commented-out code — delete it, git has history
- Global mutable state — pass dependencies explicitly (DIP from SOLID)
- Bare `except:` — always catch specific exceptions
- `# type: ignore` without explanation — if you must suppress mypy, explain why
- God objects — prefer composition over inheritance (`engineering-ontology.md` §9.2)

---

## 6. DOCUMENTATION

### 6.1 Ontology Alignment

Documentation practices are grounded in `engineering-ontology.md` §24.2:

| Format                  | Used For                                                         | Reference              |
| ----------------------- | ---------------------------------------------------------------- | ---------------------- |
| Google-style docstrings | Python (`engineering-ontology.md` §24.2: `python: google_style`) | PEP 257                |
| JSDoc                   | Browser extension JavaScript                                     | Standard JSDoc format  |
| OpenAPI 3.1             | REST API docs (`engineering-ontology.md` §12.2)                  | FastAPI auto-generates |
| ADR                     | Architecture decisions (`engineering-ontology.md` §9.3)          | `docs/adr/` directory  |
| Keep a Changelog        | Release notes (`engineering-ontology.md` §24.2)                  | CHANGELOG.md           |
| Conventional Commits    | Commit history (`engineering-ontology.md` §24.2)                 | git log                |

### 6.2 Docstrings

Every public module, class, function, and method gets a docstring. Use Google style:

```python
def redact(self, text: str, window_title: str | None = None) -> RedactionResult:
    """Apply redaction to text according to the configured privacy level.

    Processes text through level-based patterns and custom rules, replacing
    sensitive content with category-specific placeholders (e.g., [EMAIL], [API_KEY]).

    Args:
        text: Raw OCR text or other content to redact.
        window_title: Optional window title to also redact. If provided,
            the redacted title is included in the result.

    Returns:
        RedactionResult containing the redacted text, count of redactions
        applied, and which categories were triggered.

    Raises:
        ValueError: If the privacy level is not between 1 and 4.

    Example:
        >>> engine = RedactionEngine(privacy_level=2)
        >>> result = engine.redact("Contact john@example.com for details")
        >>> result.redacted_text
        'Contact [EMAIL] for details'
        >>> result.redaction_count
        1
    """
```

Module-level docstrings explain the module's role in the system:

```python
"""Text redaction engine for ChronoLens.

This module implements a multi-level privacy redaction system that sanitizes
OCR text, window titles, and browser content before they are sent to the
LLM classification API. Four cumulative privacy levels are supported,
from minimal (secrets only) to maximum (aggressive content stripping).

Architecture:
    RedactionEngine orchestrates the process:
    1. Load custom rules from database
    2. Apply custom rules (always, regardless of level)
    3. Apply level-based patterns in order (Level 1 → Level N)
    4. Collapse whitespace and trim to max length

See Also:
    chronolens-build-spec-v3.md §4 for full pattern tables.
    engineering-ontology.md §19 (Security) for the standards behind redaction.
"""
```

### 6.3 Inline Comments

Use inline comments for **why**, not **what**:

```python
# GOOD — explains a non-obvious decision:
# Skip OCR for monitors that aren't focused — we only hash-track them
# for instant classification when the user switches focus
# (see chronolens-build-spec-v3.md §3.1 Multi-Monitor Capture)
if monitor_index != focused_monitor:
    continue

# BAD — restates the code:
# Increment the counter
counter += 1
```

### 6.4 Architecture Decision Records

For significant decisions that deviate from or extend the spec, write an ADR:

```
docs/adr/
├── 0001-use-paddleocr-cpu-only.md
├── 0002-sqlite-over-postgres.md
├── 0003-weasyprint-over-reportlab.md
└── template.md
```

ADR format (from `engineering-ontology.md` §9.3):

```markdown
# ADR-NNNN: Title

## Status

Accepted | Superseded | Deprecated

## Context

What is the issue?

## Decision

What was decided?

## Consequences

What are the trade-offs?

## References

- chronolens-build-spec-v3.md §N
- engineering-ontology.md §N
```

### 6.5 README.md

Maintain a root `README.md` with: project description, feature list, quick start instructions, architecture overview, tech stack, links to all four companion documents, and license.

Update it at the end of each phase if the setup instructions change.

### 6.6 CHANGELOG.md

Maintain a `CHANGELOG.md` using Keep a Changelog format (`engineering-ontology.md` §24.2):

```markdown
# Changelog

## [Unreleased]

## [0.5.0] - 2026-XX-XX

### Added

- Dashboard MVP with live view, timeline, projects, privacy settings
- WebSocket real-time updates for current activity

### Changed

- API now serves Angular static files from /static/

### Fixed

- Session tracker crash when idle_split_threshold is 0
```

### 6.7 API Documentation

FastAPI auto-generates OpenAPI 3.1 docs (`engineering-ontology.md` §12.2). Enhance them with descriptions:

```python
@router.get(
    "/api/sessions",
    response_model=list[SessionResponse],
    summary="List tracked sessions",
    description="Returns sessions within a date range, optionally filtered by project or task category.",
    responses={
        200: {"description": "List of sessions"},
        422: {"description": "Invalid date format or filter parameters"},
    },
)
async def list_sessions(
    from_date: datetime = Query(None, alias="from", description="Start of date range (ISO 8601)"),
    to_date: datetime = Query(None, alias="to", description="End of date range (ISO 8601)"),
    project_id: int | None = Query(None, description="Filter by project ID"),
):
    ...
```

---

## 7. ERROR HANDLING & LOGGING

### 7.1 Ontology Alignment

Logging practices follow `engineering-ontology.md` §20.4 — Logging:

- **Format**: structured (JSON preferred for production, human-readable for development)
- **Levels**: TRACE, DEBUG, INFO, WARN, ERROR, FATAL (mapping to Python's logging levels)
- **Rule**: never log secrets or PII (`engineering-ontology.md` §20.4 best_practices)
- **Correlation**: include context IDs where possible (classification request ID, session ID)

### 7.2 Logging Setup

Use Python's `logging` module. Configure at startup:

```python
import logging
import logging.handlers

def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging.

    Log format includes timestamp, level, module, and message.
    Logs go to both console (stderr) and a rotating log file.
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_file = get_data_dir() / "chronolens.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5_000_000, backupCount=3
            ),
        ],
    )
```

**Logger per module:**

```python
# At the top of each module:
logger = logging.getLogger(__name__)

# Usage:
logger.debug("Capture tick: title='%s', process='%s'", title, process)
logger.info("LLM classification: project=%s, confidence=%.2f", result.project, result.confidence)
logger.warning("LLM API rate limited, retrying in %d seconds", retry_delay)
logger.error("Failed to connect to Cloudflare API: %s", str(e))
logger.critical("Database integrity check failed, shutting down")
```

### 7.3 Log Levels

| Level      | Use For                                                                |
| ---------- | ---------------------------------------------------------------------- |
| `DEBUG`    | Capture loop ticks, hash comparisons, cache hits, raw API responses    |
| `INFO`     | Classifications, session creation, calendar sync, tunnel state changes |
| `WARNING`  | API rate limits, budget approaching threshold, stale browser context   |
| `ERROR`    | API call failures, OCR errors, database write failures                 |
| `CRITICAL` | Database corruption, unrecoverable startup failures                    |

### 7.4 Error Handling Patterns

**Thread-level**: each thread has a top-level try/except. Non-critical threads (capture, LLM, calendar) log errors and continue. Critical threads (API server, tray) propagate.

```python
def capture_loop():
    """Main capture loop. Must never crash — log and continue."""
    while running.is_set():
        try:
            tick()
        except Exception:
            logger.exception("Capture tick failed, continuing")
        running.wait(1.0)
```

**API-level**: FastAPI exception handlers return structured error responses:

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception in API: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )
```

**LLM-level**: classification failures should never block tracking:

```python
async def classify(context: ClassificationContext) -> ClassificationResult:
    try:
        result = await llm_client.call(context)
        return result
    except httpx.TimeoutException:
        logger.warning("LLM API timeout, marking as pending")
        return ClassificationResult(project=None, task="unclassified",
                                    confidence=0.0, reasoning="API timeout")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("LLM API rate limited")
        else:
            logger.error("LLM API error: %d %s", e.response.status_code, e.response.text)
        return ClassificationResult(project=None, task="unclassified",
                                    confidence=0.0, reasoning=f"API error: {e.response.status_code}")
    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON, raw response: %s", raw_text[:500])
        return ClassificationResult(project=None, task="unclassified",
                                    confidence=0.0, reasoning="Invalid LLM response")
```

### 7.5 Never Swallow Exceptions Silently

```python
# WRONG — silent failure, impossible to debug:
try:
    sync_calendar()
except Exception:
    pass

# CORRECT — logged, recoverable:
try:
    sync_calendar()
except Exception:
    logger.exception("Calendar sync failed")
```

---

## 8. SECURITY PRACTICES

### 8.1 Ontology Alignment

Security is **always loaded** per `engineering-ontology.md` §1.1 — it applies to all domains. This project's security practices are grounded in:

| Ontology Standard                                           | Where It Applies                                   | Spec Section          |
| ----------------------------------------------------------- | -------------------------------------------------- | --------------------- |
| OWASP Top 10 (`engineering-ontology.md` §19.3)              | API server: input validation, injection prevention | `build-spec` §7, §20  |
| OWASP API Security Top 10 (`engineering-ontology.md` §12.6) | REST API: auth, rate limiting, error handling      | `build-spec` §7       |
| CWE-20 (Improper Input Validation)                          | All API endpoints                                  | `build-spec` §7       |
| CWE-89 (SQL Injection)                                      | Database queries                                   | `build-spec` §6       |
| CWE-798 (Hardcoded Credentials)                             | Credential storage                                 | `build-spec` §18, §20 |
| NIST CSF v2.0 (`engineering-ontology.md` §23.2)             | Overall posture: identify, protect, detect         | `build-spec` §20      |
| GDPR (`engineering-ontology.md` §23.2)                      | Redaction engine, data handling                    | `build-spec` §4       |
| RFC 8446 TLS 1.3 (`engineering-ontology.md` §8.6)           | All external connections                           | `build-spec` §20      |

### 8.2 Secrets

- **Never hardcode** API keys, tokens, or credentials in source code (CWE-798)
- **Never log** secrets — mask them: `logger.info("API key configured: %s...%s", key[:4], key[-4:])`
- **Never commit** `.env` files, API keys, or test credentials
- Store secrets via the platform keyring (`build-spec` §18)
- Database stores encrypted references, not raw keys
- Use `gitleaks` in pre-commit hooks (`engineering-ontology.md` §19.7)

### 8.3 Input Validation

Validate all inputs at the API boundary (CWE-20, OWASP A03 — Injection):

```python
from pydantic import BaseModel, Field, validator

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    client: str | None = Field(None, max_length=200)
    hourly_rate: float | None = Field(None, ge=0, le=10000)
    color: str = Field("#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")

    @validator("name")
    def name_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Project name cannot be blank")
        return v.strip()
```

### 8.4 SQL Injection Prevention

**Always use parameterized queries** (CWE-89). Never construct SQL with string formatting.

```python
# CORRECT:
cursor.execute("SELECT * FROM sessions WHERE project_id = ?", (project_id,))

# WRONG — SQL injection vulnerability:
cursor.execute(f"SELECT * FROM sessions WHERE project_id = {project_id}")
```

### 8.5 Network Security

- FastAPI binds to `127.0.0.1` only — verify this in code and in tests
- Cloudflare Tunnel ingress restricts paths — verify the ingress config programmatically
- Mobile bearer tokens must be cryptographically random: `secrets.token_hex(32)`
- ICS feed tokens same: `secrets.token_hex(16)`
- All external HTTP calls use TLS 1.3 (RFC 8446)

### 8.6 Dependency Auditing

Per `engineering-ontology.md` §19.6 — Supply Chain Security:

```bash
# Python
pip-audit                    # Check for known vulnerabilities
pip install safety && safety check

# JavaScript (dashboard, mobile, extension)
npm audit

# Run periodically and before every release (Phase 11)
```

---

## 9. PERFORMANCE DISCIPLINE

### 9.1 Profile Before Optimizing

Don't guess at performance problems. Measure:

```python
import cProfile
import pstats

cProfile.run("capture_tick()", "capture_stats")
stats = pstats.Stats("capture_stats")
stats.sort_stats("cumulative")
stats.print_stats(20)
```

### 9.2 Memory Awareness

- Screenshots are large (~6MB raw RGB per 1920x1080). Never accumulate them.
- Clear references after OCR: `screenshot = None` after extracting text
- Classification queue has `maxsize=100` — respect this
- PaddleOCR model stays loaded (intentional — loading is ~2s)

### 9.3 Database Performance

- Use indices for frequently queried columns (defined in `build-spec` §6)
- Use `LIMIT` on queries that could return large result sets
- Use WAL mode (already configured) for concurrent read/write
- Periodically run `VACUUM` (weekly via scheduler)
- Batch inserts for activities (collect 10-30 seconds, then bulk insert)

### 9.4 Performance Budget Validation

Validate against `build-spec` §19 at Phase 1 completion and Phase 11. The targets:

| Metric              | Target   |
| ------------------- | -------- |
| CPU (idle screen)   | < 1%     |
| CPU (active screen) | < 5%     |
| RAM                 | < 200 MB |
| VRAM                | 0        |
| Dashboard load      | < 2s     |

---

## 10. CROSS-PLATFORM DISCIPLINE

### 10.1 Never Use Platform-Specific Code in Shared Modules

All platform-specific logic goes in `_windows.py`, `_macos.py`, `_linux.py` files with a dispatcher module. This pattern is defined in `build-spec` §18.

```python
# CORRECT — dispatcher pattern:
# window_info.py
import platform
_system = platform.system()
if _system == "Windows":
    from .window_info_windows import *
elif _system == "Darwin":
    from .window_info_macos import *
else:
    from .window_info_linux import *

# WRONG — platform check in shared code:
# capture/loop.py
if platform.system() == "Windows":
    import win32gui
    title = win32gui.GetWindowText(...)
```

### 10.2 Path Handling

**Always use `pathlib.Path`**, never string concatenation for paths:

```python
# CORRECT:
from pathlib import Path
db_path = Path(get_data_dir()) / "chronolens.db"

# WRONG:
db_path = get_data_dir() + "/chronolens.db"       # fails on Windows
db_path = get_data_dir() + "\\chronolens.db"      # fails on Linux/macOS
```

### 10.3 Testing Cross-Platform Code

- Test on your primary platform thoroughly
- Use `unittest.mock` to mock platform-specific functions in cross-platform tests
- Document which platforms have been manually tested in the commit message
- Mark platform-specific tests: `@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")`
- Full cross-platform QA happens in Phase 11 (see `implementation-phases.md` §Phase 11 QA Matrix)

---

## 11. DATABASE DISCIPLINE

### 11.1 Ontology Alignment

Database practices follow `engineering-ontology.md` §11:

- **ACID compliance**: SQLite WAL mode provides this (`engineering-ontology.md` §11.1)
- **SQL standard**: ISO/IEC 9075 — use standard SQL where possible
- **Schema as defined**: `build-spec` §6 is the canonical schema

### 11.2 Migrations

The database schema will evolve. Use a versioned migration system:

```python
MIGRATIONS = [
    (1, "Initial schema", INITIAL_SCHEMA_SQL),
    (2, "Add browser_url to activities",
     "ALTER TABLE activities ADD COLUMN browser_url TEXT"),
    (3, "Add invoice_id to sessions",
     "ALTER TABLE sessions ADD COLUMN invoice_id INTEGER REFERENCES invoices(id)"),
]

def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply pending migrations in order."""
    current_version = get_schema_version(conn)
    for version, description, sql in MIGRATIONS:
        if version > current_version:
            logger.info("Running migration %d: %s", version, description)
            conn.executescript(sql)
            set_schema_version(conn, version)
```

### 11.3 Schema Change Rules

- Never modify existing migration SQL — always add a new migration
- Always test migration from empty database AND from previous version
- Always backup database before running migrations (copy file)
- Add `CREATE INDEX` in the same migration as its table alteration

### 11.4 Connection Management

- Thread-local connections (`threading.local()`) since SQLite connections aren't thread-safe
- Always use context managers: `with get_db() as conn:`
- Enable WAL mode and foreign keys on every new connection

---

## 12. API DESIGN DISCIPLINE

### 12.1 Ontology Alignment

API design follows `engineering-ontology.md` §12:

| Principle                   | Source                                     | Applied How                                               |
| --------------------------- | ------------------------------------------ | --------------------------------------------------------- |
| REST constraints            | `engineering-ontology.md` §12.1 (Fielding) | Stateless, resource-oriented, uniform interface           |
| HTTP semantics              | RFC 9110 (`engineering-ontology.md` §12.1) | Correct status codes, content negotiation                 |
| OpenAPI 3.1                 | `engineering-ontology.md` §12.2            | FastAPI auto-generates spec                               |
| API Security                | `engineering-ontology.md` §12.6            | Bearer tokens (RFC 6750), input validation                |
| Richardson Maturity Level 2 | `engineering-ontology.md` §12.1            | Resources + HTTP verbs (Level 3/HATEOAS is overkill here) |

### 12.2 REST Conventions

- **Nouns for resources**, verbs via HTTP methods: `GET /api/sessions`, not `GET /api/getSessions`
- **Plural nouns**: `/api/projects`, not `/api/project`
- **Nested routes for relationships**: `/api/invoices/{id}/line-items`
- **Query params for filtering**: `GET /api/sessions?project_id=1&from=2026-01-01`
- **HTTP status codes** per RFC 9110: 200, 201, 204, 400, 404, 422, 500

### 12.3 Response Format

Error responses are consistent:

```json
{
  "error": "not_found",
  "message": "Session with ID 42 not found"
}
```

### 12.4 Pagination

For endpoints returning large lists:

```
GET /api/sessions?from=2026-01-01&to=2026-01-31&limit=50&offset=0
```

Response includes pagination metadata:

```json
{
    "items": [...],
    "total": 342,
    "limit": 50,
    "offset": 0
}
```

---

## 13. FRONTEND DISCIPLINE

### 13.1 Ontology Alignment

Frontend work is grounded in:

| Standard             | Reference                       | Applied How                                |
| -------------------- | ------------------------------- | ------------------------------------------ |
| ECMA-262             | `engineering-ontology.md` §6.1  | TypeScript compiles to ECMAScript          |
| HTML Living Standard | `engineering-ontology.md` §7.1  | Valid semantic HTML                        |
| CSS Specifications   | `engineering-ontology.md` §7.2  | Flexbox, Grid, custom properties           |
| DOM Standard         | `engineering-ontology.md` §7.1  | Correct DOM API usage in extension         |
| WCAG 2.2             | `engineering-ontology.md` §21.1 | Accessible dashboard UI                    |
| WAI-ARIA 1.2         | `engineering-ontology.md` §7.12 | ARIA roles on custom widgets               |
| PWA standards        | `engineering-ontology.md` §7.11 | Mobile companion manifest + service worker |
| ES Modules           | `engineering-ontology.md` §7.13 | Import/export in extension code            |

### 13.2 Angular Conventions

- **Standalone components** (no NgModules) — Angular 19+ default
- **Signals** for state, not BehaviorSubject (unless you specifically need RxJS stream operators)
- **Lazy-loaded routes** for every page
- **OnPush change detection** on all components
- **No external CSS framework** — write custom styles

### 13.3 Service Pattern

```typescript
@Injectable({ providedIn: "root" })
export class ApiService {
  private readonly baseUrl = "http://localhost:19532/api";

  constructor(private http: HttpClient) {}

  getSessions(params: SessionFilter): Observable<SessionResponse> {
    return this.http.get<SessionResponse>(`${this.baseUrl}/sessions`, {
      params: toHttpParams(params),
    });
  }
}
```

### 13.4 Accessibility

All dashboard UI must be keyboard-navigable and screen-reader compatible. Per WCAG 2.2 Level AA (`engineering-ontology.md` §21.1):

- Every `<img>` has `alt` text
- Form inputs have associated `<label>` elements
- Interactive elements are focusable with visible focus indicators
- Color is not the only way to convey information (use icons/text alongside project colors)
- ARIA roles on custom interactive elements (session bars, timeline, pomodoro widget)
- Sufficient color contrast ratios (4.5:1 for normal text, 3:1 for large text)

---

## 14. DEPENDENCY MANAGEMENT

### 14.1 Ontology Alignment

Package management follows `engineering-ontology.md` §6.12:

| Ecosystem  | Manager | Registry                                           |
| ---------- | ------- | -------------------------------------------------- |
| Python     | pip     | PyPI (`engineering-ontology.md` §6.12: `pip`)      |
| JavaScript | npm     | npmjs.org (`engineering-ontology.md` §6.12: `npm`) |

### 14.2 Pin Versions

`requirements.txt` pins exact versions. No `>=`, no `~=`, no unpinned:

```
fastapi==0.115.0
uvicorn[standard]==0.29.0
paddleocr==2.7.3
```

### 14.3 Minimize Dependencies

Before adding a dependency, ask:

1. Can I do this in <50 lines of my own code?
2. Is this library actively maintained?
3. Does it have known security issues? (check `pip-audit` / `npm audit`)
4. How large is the transitive dependency tree?

### 14.4 Separate Prod and Dev Dependencies

```
# requirements.txt — production
fastapi==0.115.0
uvicorn[standard]==0.29.0
...

# requirements-dev.txt — development only
pytest==8.2.0
pytest-asyncio==0.23.0
pytest-cov==5.0.0
black==24.4.0
ruff==0.4.0
mypy==1.10.0
pre-commit==3.7.0
pip-audit==2.7.0
```

### 14.5 Angular Dependencies

`package.json` uses exact versions (no `^` or `~`):

```json
"dependencies": {
    "@angular/core": "19.0.0",
    "chart.js": "4.4.0",
    "ng2-charts": "6.0.0"
}
```

Run `npm audit` regularly. Fix vulnerabilities before release.

### 14.6 License Compliance

Per `engineering-ontology.md` §24.3 — Licensing:

- All dependencies must use compatible open-source licenses
- Use SPDX identifiers in `pyproject.toml` and `package.json`
- Run `pip-licenses` or equivalent to verify no GPL-only dependencies leak into the codebase (if you want a permissive-licensed output)
- Document license in `pyproject.toml`: `license = {text = "MIT"}` (or your chosen license)

---

## 15. DEBUGGING & TROUBLESHOOTING

### 15.1 Debug Mode

Add a `--debug` CLI flag that:

- Sets log level to `DEBUG`
- Enables FastAPI reload mode
- Prints capture loop state every tick
- Logs full LLM request/response bodies (with redacted text, not raw)

### 15.2 Health Check Endpoint

`GET /api/status` returns comprehensive health info (defined in `build-spec` §7):

```json
{
  "status": "ok",
  "version": "0.5.0",
  "platform": "Windows",
  "uptime_seconds": 3600,
  "capture": {
    "state": "tracking",
    "ticks_total": 3600,
    "ticks_with_change": 142,
    "last_tick_at": "2026-05-08T14:30:00Z"
  },
  "llm": {
    "provider": "claude",
    "model": "claude-sonnet-4-20250514",
    "state": "active",
    "calls_today": 87,
    "cache_hit_rate": 0.63,
    "budget_remaining_cents": 450
  },
  "tunnel": {
    "state": "active",
    "hostname": "time.example.com"
  },
  "db": {
    "path": "/home/user/.local/share/chronolens/chronolens.db",
    "size_bytes": 4521984,
    "sessions_count": 1247
  }
}
```

### 15.3 Common Issues Checklist

When something breaks, check in this order:

1. **Logs** — `chronolens.log` in the data directory
2. **Database** — `sqlite3 chronolens.db ".tables"` / `"SELECT COUNT(*) FROM activities"`
3. **API** — `curl http://localhost:19532/api/status`
4. **Tray** — is the icon present? What color? (see `build-spec` §12 Tray Icon States)
5. **Processes** — is `chronolens` running? Multiple instances?
6. **Ports** — is 19532 already in use? `netstat -tlnp | grep 19532`

---

## 16. STANDARDS COMPLIANCE MATRIX

This project adheres to the **Global Software Engineering Standards Ontology v3.0** (`engineering-ontology.md`). The ontology loading strategy (§1.1) requires loading relevant domains plus always-loaded domains (`security`, `internet_protocols`, `software_quality`).

### 16.1 Ontology Loading — Domains Active for ChronoLens

Per `engineering-ontology.md` §1.1, load based on language, runtime, and deployment model:

```yaml
always_loaded: # §1.1 — always include
  - security # §19
  - internet_protocols # §8
  - software_quality # §17

loaded_by_language:
  - programming_languages # §6 — Python (§6.6), TypeScript (§6.1)
  - web_platform # §7 — HTML, CSS, DOM, PWA, WebSocket

loaded_by_domain:
  - api_design # §12 — REST, OpenAPI
  - data_storage # §11 — SQLite/SQL
  - architecture # §9 — patterns, principles
  - design_patterns # §10 — patterns used in code
  - observability # §20 — logging
  - accessibility # §21 — WCAG, ARIA
  - governance # §23 — GDPR, licensing
  - meta # §24 — semver, docs, formatting

not_loaded: # Not relevant to this project
  - cloud_native # No Kubernetes, no containers
  - distributed_systems # Single-process desktop app
  - devops # No CI/CD pipeline (yet)
  - ai_data # We USE an LLM, but don't train or govern models
  - networking # No custom networking infrastructure
  - reliability # No SRE (desktop app, not a service)
```

### 16.2 Language & Runtime Standards

| Ontology Reference | Standard                  | Applies To                               | Implementation Note                       |
| ------------------ | ------------------------- | ---------------------------------------- | ----------------------------------------- |
| §6.6 `python`      | Python Language Reference | Backend                                  | Python 3.12+, follow reference semantics  |
| §6.1 `javascript`  | ECMA-262                  | Dashboard TS, extension JS, mobile TS    | TypeScript compiles to ES2022+            |
| §6.1 `typescript`  | TypeScript Language       | Dashboard, mobile                        | Strict mode enabled                       |
| §6.7 `sql`         | ISO/IEC 9075              | Database queries                         | Standard SQL, SQLite dialect where needed |
| §6.8 `html`        | HTML Living Standard      | Dashboard templates, invoice HTML        | Valid semantic HTML5                      |
| §6.8 `css`         | W3C CSS Specifications    | Dashboard, invoice PDFs                  | Valid CSS, flexbox/grid (§7.2)            |
| §6.8 `json`        | RFC 8259 / ECMA-404       | API responses, LLM communication, config | Valid JSON everywhere                     |

### 16.3 Web Platform Standards

| Ontology Reference           | Standard                | Applies To                  | Implementation Note                             |
| ---------------------------- | ----------------------- | --------------------------- | ----------------------------------------------- |
| §7.1 `dom`                   | DOM Standard (WHATWG)   | Extension content scripts   | DOM API per spec                                |
| §7.4 `fetch`                 | Fetch Standard (WHATWG) | Dashboard API calls         | Angular HttpClient follows Fetch semantics      |
| §7.4 `websockets`            | WebSocket (WHATWG)      | Live view, extension bridge | RFC 6455 via FastAPI/uvicorn                    |
| §7.5 `local_session_storage` | Web Storage             | Extension settings          | Extension uses chrome.storage, not localStorage |
| §7.6 `service_workers`       | Service Workers (W3C)   | Mobile PWA                  | Offline shell, push notifications               |
| §7.9 `secure_contexts`       | Secure Contexts (W3C)   | Mobile PWA (requires HTTPS) | Cloudflare Tunnel provides HTTPS                |
| §7.11 `pwa`                  | Web App Manifest (W3C)  | Mobile companion            | manifest.webmanifest, service worker            |
| §7.12 `aria`                 | WAI-ARIA 1.2 (W3C)      | Dashboard components        | ARIA roles on custom widgets                    |

### 16.4 Internet Protocol Standards

| Ontology Reference | Standard           | Applies To                       | Implementation Note                 |
| ------------------ | ------------------ | -------------------------------- | ----------------------------------- |
| §8.3 `http_1_1`    | RFC 9110 / 9112    | API server, LLM clients          | FastAPI serves HTTP/1.1 locally     |
| §8.3 `websocket`   | RFC 6455           | Live updates, extension bridge   | `/ws/live`, `/ws/browser-extension` |
| §8.6 `tls`         | RFC 8446 (TLS 1.3) | LLM API calls, Cloudflare tunnel | All external HTTPS connections      |
| §8.7 `json`        | RFC 8259           | API responses, LLM payloads      | Content-Type: application/json      |

### 16.5 Security Standards

| Ontology Reference        | Standard                  | Applies To                               | Implementation Note                                                                                       |
| ------------------------- | ------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| §19.3 `owasp_top_10`      | OWASP Top 10 (2021)       | API server                               | A03 (Injection): parameterized SQL. A05 (Misconfiguration): bind to localhost. A07 (Auth): mobile tokens. |
| §12.6 `api_security`      | OWASP API Security Top 10 | REST API                                 | Input validation (CWE-20), bearer auth (RFC 6750)                                                         |
| §19.3 `cwe_key`           | CWE (MITRE)               | All code                                 | CWE-20 (validation), CWE-89 (SQLi), CWE-798 (hardcoded creds)                                             |
| §19.4 `hashing: sha2`     | FIPS 180-4 (SHA-256)      | Classification cache keys                | SHA-256 for cache key computation                                                                         |
| §19.5 `oauth2`            | RFC 6749                  | Google Calendar integration              | OAuth2 authorization_code flow                                                                            |
| §19.5 `jwt`               | RFC 7519                  | Redaction pattern (detect & redact JWTs) | Level 1 redaction detects JWT format                                                                      |
| §23.2 `gdpr`              | GDPR (EU)                 | Redaction engine, data lifecycle         | All data local by default, redaction before external transmission, user controls data                     |
| §19.6 `slsa`              | SLSA (OpenSSF)            | Release builds (Phase 11)                | Provenance for release artifacts                                                                          |
| §19.6 `sbom: spdx`        | SPDX (Linux Foundation)   | Package metadata                         | License identifiers in pyproject.toml                                                                     |
| §19.7 `secrets: gitleaks` | Gitleaks                  | Pre-commit hook                          | Prevent accidental secret commits                                                                         |
| §23.2 `nist_csf`          | NIST CSF v2.0             | Overall security posture                 | Identify (threat model), Protect (redaction, auth), Detect (logging)                                      |

### 16.6 API Design Standards

| Ontology Reference     | Standard            | Applies To        | Implementation Note                                                            |
| ---------------------- | ------------------- | ----------------- | ------------------------------------------------------------------------------ |
| §12.1 `rest`           | REST (Fielding)     | API design        | Resource-oriented, stateless, HTTP verbs                                       |
| §12.1 `http_semantics` | RFC 9110            | Status codes      | Correct 2xx/4xx/5xx usage                                                      |
| §12.2 `openapi`        | OpenAPI 3.1         | API documentation | FastAPI auto-generates valid OpenAPI spec                                      |
| §12.7 `api_versioning` | URL path versioning | Future-proofing   | Not needed for v1 (single-user local app), but spec allows `/v1/` prefix later |

### 16.7 Architecture & Design Patterns

| Ontology Reference            | Pattern                | Used Where                     | Implementation Note                          |
| ----------------------------- | ---------------------- | ------------------------------ | -------------------------------------------- |
| §9.2 `solid`                  | SOLID principles       | All code                       | SRP per module, DIP via dispatchers          |
| §9.2 `separation_of_concerns` | Separation of concerns | Module boundaries              | capture/ vs redaction/ vs classification/    |
| §10.2 `strategy`              | Strategy pattern       | LLM client, calendar providers | Abstract base + concrete implementations     |
| §10.3 `observer`              | Observer pattern       | WebSocket live updates         | Pub/sub for real-time dashboard              |
| §10.3 `state`                 | State pattern          | Pomodoro timer                 | State machine: IDLE → FOCUS → BREAK          |
| §10.5 `pipes_and_filters`     | Pipeline pattern       | Classification pipeline        | capture → OCR → redact → cache → LLM → store |
| §10.6 `circuit_breaker`       | Circuit breaker        | LLM API calls                  | Budget exceeded → stop calling, mark pending |
| §10.6 `retry_with_backoff`    | Retry with backoff     | LLM API rate limits            | Exponential backoff on 429                   |

### 16.8 Software Quality Standards

| Ontology Reference    | Standard            | Applies To           | Implementation Note                                                                                          |
| --------------------- | ------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------ |
| §17.5 `iso_25010`     | ISO 25010 (SQuaRE)  | Overall quality      | Targets: functional suitability, reliability, performance, usability, security, maintainability, portability |
| §17 `iso_29119`       | ISO 29119 (Testing) | Test strategy        | Unit → integration → system → acceptance levels                                                              |
| §17.4 `code_coverage` | Coverage thresholds | Test suite           | 80% overall minimum, 95% for security-critical code                                                          |
| §17.3 `tdd`           | TDD cycle           | Development workflow | Red → green → refactor (§2.1 per-feature workflow)                                                           |

### 16.9 Data & Calendar Standards

| Ontology Reference   | Standard             | Applies To           | Implementation Note                             |
| -------------------- | -------------------- | -------------------- | ----------------------------------------------- |
| §11.1 `acid`         | ACID properties      | SQLite               | WAL mode provides this                          |
| §11.1 `sql_standard` | ISO/IEC 9075         | Database queries     | Standard SQL dialect                            |
| §8.4 (related)       | RFC 5545 (iCalendar) | ICS feed, ICS export | Valid VEVENT generation via `icalendar` library |
| §8.4 (related)       | RFC 4791 (CalDAV)    | CalDAV calendar sync | Standard CalDAV operations via `caldav` library |

### 16.10 Documentation & Meta Standards

| Ontology Reference                       | Standard                      | Applies To         | Implementation Note                                         |
| ---------------------------------------- | ----------------------------- | ------------------ | ----------------------------------------------------------- |
| §24.1 `semver`                           | Semantic Versioning           | Release tags       | MAJOR.MINOR.PATCH per `implementation-phases.md` versioning |
| §24.2 `conventional_commits`             | Conventional Commits          | Git history        | type(scope): description                                    |
| §24.2 `keep_a_changelog`                 | Keep a Changelog              | CHANGELOG.md       | Added/Changed/Fixed/Removed sections                        |
| §24.2 `adr`                              | Architecture Decision Records | `docs/adr/`        | Significant deviations from spec documented                 |
| §24.3 `spdx_identifiers`                 | SPDX License IDs              | Package metadata   | Correct SPDX identifier in pyproject.toml                   |
| §24.4 `formatting: python: black`        | Black formatter               | Python code        | `--line-length 120`                                         |
| §24.4 `linting: python: ruff`            | Ruff linter                   | Python code        | Full rule set in pyproject.toml                             |
| §24.4 `formatting: javascript: prettier` | Prettier                      | TypeScript/JS      | Dashboard, extension, mobile                                |
| §24.4 `linting: javascript: eslint`      | ESLint                        | Angular TypeScript | @angular-eslint plugin                                      |
| §24.4 `cyclomatic_complexity`            | McCabe ≤ 10                   | All code           | Enforced by ruff `C90` rules                                |

### 16.11 Priority Resolution

When multiple standards apply to the same decision, resolve per `engineering-ontology.md` §1.2:

```
1. Formal Standards (ISO, RFC, IEEE)          ← highest priority
2. Living Standards (WHATWG, W3C)
3. Foundation Specs (CNCF, OpenAPI, etc.)
4. Industry De facto standards                ← lowest priority
```

Example: if an Angular convention conflicts with the WHATWG HTML Standard, the WHATWG spec wins. If a Python community convention conflicts with PEP 8 (which ISO doesn't cover), follow PEP 8 as the de facto standard.

---

## QUICK REFERENCE CARD

```
BEFORE writing code:    Read the spec section. Read the phase. Check the ontology.
BEFORE committing:      Run black, ruff, mypy, pytest. All must pass.
EVERY function:         Type hints + docstring. No exceptions.
EVERY feature:          Unit tests first, then implementation (TDD: red → green → refactor).
EVERY commit:           type(scope): description — one logical change.
EVERY phase:            Branch, build, test, tag, merge to main.
NEVER:                  Commit secrets, print() debug, bare except, magic numbers, any types.
ALWAYS:                 Log errors, validate input, parameterize SQL, use pathlib.
WHEN IN DOUBT:          Check engineering-ontology.md for the authoritative standard.
```

---

## DOCUMENT VERSIONS

| Document              | Location                                             |
| --------------------- | ---------------------------------------------------- |
| Build Specification   | `chronolens-build-spec-v3.md`                        |
| Implementation Phases | `chronolens-implementation-phases.md`                |
| Engineering Workflow  | `chronolens-engineering-workflow.md` (this document) |
| Engineering Ontology  | `engineering-ontology.md`                            |
