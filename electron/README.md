# Tickwise — Electron wrapper

Wraps the Tickwise dashboard in its own native window so it doesn't open
in a browser tab. Spawns the Python backend ([../tickwise](../tickwise))
in headless mode (no duplicate tray), waits for the API to come up, and
then loads <http://127.0.0.1:19532/> inside a `BrowserWindow`. Adds a
system-tray icon with show/hide and graceful quit.

## Layout

```
electron/
├── package.json     electron + electron-builder + build config (NSIS, DMG, AppImage)
├── main.js          main process — window, tray, backend lifecycle
├── preload.js       exposes window.tickwise = { isElectron: true, platform }
├── loading.html     splash shown while the Python backend starts
└── build/           icons (icon.ico, icon.png, icon-16…icon-1024.png)
```

## Develop

You need **Node.js 20+** and the Python venv at the repo root.

```powershell
# from repo root
.\.venv\Scripts\pip install -e .                                # backend deps
Push-Location dashboard ; npm install ; .\node_modules\.bin\ng build ; Pop-Location
Copy-Item dashboard\dist\tickwise-dashboard\browser\* tickwise\static -Recurse -Force

cd electron
npm install
npm start                                                       # opens the desktop app
```

In dev mode, `main.js` detects the venv and spawns `pythonw.exe -m tickwise`
with `TICKWISE_HEADLESS=1`. No tray icon from the Python side — Electron
owns the tray.

## Build distributables

The Electron installer needs the PyInstaller-built backend at
`../dist/Tickwise/`. Build that first, then run electron-builder:

```powershell
# 1. Build the Python backend
.\.venv\Scripts\python.exe -m PyInstaller packaging\tickwise.spec --clean --noconfirm

# 2. Refresh icons (optional — only when the brand SVG changes)
.\.venv\Scripts\python.exe packaging\generate_icons.py

# 3. Bundle the Electron app
cd electron
npm run build:win        # → dist-electron/Tickwise-Setup-1.0.0.exe + portable .exe
# or:
# npm run build:mac      # universal .dmg (requires macOS host)
# npm run build:linux    # AppImage (requires Linux host)
```

The bundled installer ships:

- The Electron renderer + main process
- Tickwise.exe + its `_internal/` (Python runtime, dashboard, dependencies)
  copied into `resources/tickwise-backend/` via `extraResources`

Total Windows installer size is roughly 100–120 MB.

## How it talks to the backend

| Concern                   | Mechanism                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------- |
| Spawn / detect            | Production: `process.resourcesPath/tickwise-backend/Tickwise.exe`. Dev: repo's `.venv` python module |
| Headless mode             | Env var `TICKWISE_HEADLESS=1` — Python skips the pystray tray                                        |
| Wait for API              | 30 × 500 ms polls of `GET /api/status` before showing the dashboard                                  |
| Load the UI               | `mainWindow.loadURL("http://127.0.0.1:19532/")`                                                      |
| Graceful quit             | `POST /api/shutdown` (signals SIGINT internally), with a 1 s `kill()` fallback                       |
| External links            | `setWindowOpenHandler` opens `target=_blank` URLs in the user's default browser, not Electron        |
| Single-instance enforcement | `app.requestSingleInstanceLock()` — second launch focuses the existing window                      |

## Caveats

- **Code signing.** The Electron installer is unsigned by default. Windows
  SmartScreen will warn on first run. macOS Gatekeeper will block.
  Add a code-signing cert and update `electron-builder.win.certificateFile` /
  `electron-builder.mac.identity` before public distribution.
- **Tray fights.** If the user has already started `Tickwise.exe` outside
  Electron, both processes will run a tray icon. Electron detects an
  existing API on `:19532` and won't spawn a duplicate backend, but the
  tray icons will both show. Recommended for v1: ship only the Electron
  installer.
