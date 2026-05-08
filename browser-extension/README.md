# Tickwise browser bridge

The browser extension forwards the active tab's URL and title (and an
optional 1.5 KB plain-text snippet) to the local Tickwise app over
WebSocket. Tickwise uses that context to classify activity into
projects more accurately than window-title alone allows.

## Install (development)

### Chrome / Edge / Brave / Vivaldi

1. Open `chrome://extensions`.
2. Toggle **Developer mode** (top right).
3. Click **Load unpacked** and pick this folder (`browser-extension/`).
4. Open the popup — the badge should turn green when the desktop app
   is running on `127.0.0.1:19532`.

### Firefox

1. Rename `manifest.firefox.json` → `manifest.json` (or copy the folder
   first; Chrome and Firefox can't share a manifest).
2. Open `about:debugging#/runtime/this-firefox`.
3. Click **Load Temporary Add-on…** and select `manifest.json`.

The extension targets MV3 on Chrome and MV2 on Firefox because
Firefox's MV3 background-script support is still maturing.

## Privacy controls

Both controls live in the extension's options page:

- **Excluded domains** — URLs and titles for these hosts are never
  sent. Subdomains match implicitly: `mail.google.com` excludes itself
  and `inbox.mail.google.com`.
- **Send page-text snippet** — when enabled, the first ~1.5 KB of
  visible text is included to help the LLM disambiguate. When
  disabled, only URL + title are sent.

The snippet is redacted by Tickwise before reaching the LLM, but
disabling it removes the data at the source so it never leaves the
browser.
