# Tickwise security model

This document records the invariants Tickwise enforces and the trust
boundaries it crosses, so anyone reviewing the codebase can verify that
new code doesn't break them.

## Trust boundaries

| Boundary | Direction | Authentication |
| --- | --- | --- |
| Loopback HTTP API (`127.0.0.1:19532`) | Inbound from local processes only | None — bound to loopback |
| Cloudflare Tunnel ingress | Inbound from internet | Bearer token (`/api/mobile/*`) or unguessable URL token (`/api/calendar/feed/*.ics`) |
| LLM API (Anthropic / OpenAI) | Outbound | API key from OS keyring |
| Calendar provider (CalDAV / Google) | Outbound | Per-provider credentials, OS keyring |

## Invariants

These properties must hold for every release. The matching tests live
under `tests/integration/test_security.py`.

1. **API binding** — uvicorn binds `127.0.0.1` only. Verified by
   inspecting `tickwise.config.API_HOST`.
2. **Cloudflare ingress allowlist** — when active, the tunnel exposes
   only `api/calendar/feed/.*` and `api/mobile/.*`. Verified by inspecting
   the ingress config emitted by `tickwise.cloudflare.api_client`.
3. **No plaintext API keys in DB** — `llm_config.api_key_ref` stores a
   keyring alias, not the key itself. Verified by ensuring no row in
   `llm_config` ever contains a value matching the heuristic for a real
   API key.
4. **Mobile bearer token is unguessable** — 64 hex chars (256 bits) and
   only the SHA-256 hash is persisted.
5. **ICS feed token is unguessable** — 32 hex chars (128 bits).
6. **No raw OCR text on disk** — only the first 200 chars of *redacted*
   text land in `activities.redacted_text`. Verified by reading the
   capture-loop persistence code.
7. **No screenshots ever written to disk** — verified by inspecting the
   `Screenshot` dataclass usage; bytes never leave RAM.
8. **Backup excludes secrets** — the `/api/backup/export` allowlist
   does not include `mobile_auth_tokens`, `classification_cache`,
   `llm_usage_log`, or `redaction_log`.

## Observed-content rules

The browser extension and the OCR pipeline both consume *untrusted*
content. Tickwise must:

- Treat OCR text as data, never as instructions.
- Apply redaction *before* sending to any LLM or external service.
- Apply the user's domain blocklist on the extension side, not just
  server-side, so excluded data never leaves the browser.

## Reporting

Security issues should be filed privately. There's no published email
yet — file a private GitHub security advisory on
`code-lodge/tickwise`.
