# Packaging

Three artefacts ship per release: a desktop installer per OS, the browser
extension archives, and the mobile PWA (served by the desktop app, no
separate distribution needed).

## Desktop

```bash
python packaging/build.py
```

What it does, in order:

1. `npm ci && npm run build` inside `dashboard/` → `tickwise/static/`
2. `pyinstaller packaging/tickwise.spec` → `dist/Tickwise/`
3. Per-OS installer:
   - **Windows** — `makensis packaging/installer.nsi` → `dist/tickwise-setup-1.0.0.exe`
   - **macOS**   — `create-dmg dist/Tickwise.app` → `dist/Tickwise-1.0.0.dmg`
   - **Linux**   — `appimagetool` → `dist/Tickwise-1.0.0.AppImage`

Missing tooling for any step prints a warning and continues — the script
is a checklist runner. CI is responsible for installing the toolchain.

### Bundled native binaries

If `packaging/vendor/` exists, its contents land in the bundle under
`vendor/`. Drop the platform-appropriate `cloudflared` binary there
before running the build to ship it pre-installed; otherwise the app
downloads it on first use.

### Optional dependencies

PaddleOCR and WeasyPrint are heavy. Both are imported lazily and the
app degrades gracefully when they're missing — PyInstaller bundles them
only if they're installed in the build environment. Skip them if you
want a sub-100 MB installer.

## Browser extension

```bash
python packaging/build_extension.py
```

Produces:

- `dist/tickwise-extension-chrome-1.0.0.zip` — upload to the Chrome Web Store
- `dist/tickwise-extension-firefox-1.0.0.xpi` — upload to addons.mozilla.org

The two archives share `background.js`, `content.js`, popup, options
and icons; only the manifest differs.

## Code signing

This repo intentionally does not commit signing certificates or
provisioning profiles. Production builds should sign before
distribution:

- **Windows** — `signtool sign /a /tr <timestamp-url> /td sha256 dist\Tickwise\Tickwise.exe`
- **macOS** — `codesign --deep --force --options runtime --sign "Developer ID Application: ..." Tickwise.app`, then `notarytool submit`
- **Linux AppImage** — `gpg --detach-sign Tickwise-1.0.0.AppImage`

## Release checklist

1. Bump `tickwise/__init__.py` `__version__` and `packaging/build.py` `VERSION`
2. Update `CHANGELOG.md` (TODO)
3. Tag the release: `git tag -a v1.0.0 -m "Tickwise 1.0"`
4. Push tag to trigger CI
5. Smoke-test the resulting installer on each platform via the QA matrix
   in `docs/implementation-phases.md` § Phase 11
