/* Tickwise — Electron wrapper.
 *
 * This main process owns:
 *  • the Tickwise BrowserWindow (the dashboard, in its own native window
 *    instead of a browser tab)
 *  • a system tray icon with a context menu
 *  • the bundled Python backend, spawned in headless mode so the
 *    Tickwise API + capture loop run while the window is open
 *
 * The bundled backend lives at `process.resourcesPath/tickwise-backend/Tickwise.exe`
 * (Windows). In dev mode (no asar, no resourcesPath) we fall back to
 * spawning `python -m tickwise` from the repo root.
 */

const { app, BrowserWindow, Tray, Menu, shell, nativeImage, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");

const API_HOST = "127.0.0.1";
const API_PORT = 19532;
const API_URL = `http://${API_HOST}:${API_PORT}`;

let mainWindow = null;
let tray = null;
let backendProc = null;
let backendShuttingDown = false;
let isQuitting = false;

// ─── Backend lifecycle ───────────────────────────────────────────

function locateBackend() {
  // Production (packaged): bundled exe shipped alongside Electron.
  const packagedExe = path.join(process.resourcesPath || "", "tickwise-backend", "Tickwise.exe");
  if (fs.existsSync(packagedExe)) {
    return { kind: "exe", cmd: packagedExe, args: [] };
  }
  // Dev: run from the repo using the venv python.
  const repoRoot = path.resolve(__dirname, "..");
  const isWin = process.platform === "win32";
  const venvPy = isWin
    ? path.join(repoRoot, ".venv", "Scripts", "pythonw.exe")
    : path.join(repoRoot, ".venv", "bin", "python");
  if (fs.existsSync(venvPy)) {
    return { kind: "python", cmd: venvPy, args: ["-m", "tickwise"], cwd: repoRoot };
  }
  return null;
}

function pingApi() {
  return new Promise((resolve) => {
    const req = http.get(
      `${API_URL}/api/status`,
      { timeout: 1000 },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      },
    );
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForApi(maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    if (await pingApi()) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

async function startBackend() {
  if (await pingApi()) {
    console.log("[Tickwise] backend already running on", API_URL);
    return;
  }

  const target = locateBackend();
  if (!target) {
    console.error("[Tickwise] no backend found — neither bundled nor dev venv");
    return;
  }

  console.log(`[Tickwise] spawning backend (${target.kind}):`, target.cmd, target.args.join(" "));
  backendProc = spawn(target.cmd, target.args, {
    cwd: target.cwd || path.dirname(target.cmd),
    env: { ...process.env, TICKWISE_HEADLESS: "1" },
    detached: false,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProc.stdout?.on("data", (b) => process.stdout.write(`[tickwise] ${b}`));
  backendProc.stderr?.on("data", (b) => process.stderr.write(`[tickwise] ${b}`));
  backendProc.on("exit", (code) => {
    if (!backendShuttingDown) {
      console.warn(`[Tickwise] backend exited unexpectedly: code=${code}`);
    }
    backendProc = null;
  });
}

function stopBackend() {
  if (!backendProc) return;
  backendShuttingDown = true;
  try {
    if (process.platform === "win32") {
      // Best-effort graceful shutdown via the local API; fall back to kill.
      const req = http.request(
        { host: API_HOST, port: API_PORT, path: "/api/shutdown", method: "POST", timeout: 800 },
        () => {},
      );
      req.on("error", () => {});
      req.end();
      setTimeout(() => backendProc && backendProc.kill(), 1000);
    } else {
      backendProc.kill("SIGTERM");
    }
  } catch (err) {
    console.error("[Tickwise] error stopping backend:", err);
  }
}

// ─── Window ─────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: "#08131d",
    title: "Tickwise",
    icon: path.join(__dirname, "build", process.platform === "win32" ? "icon.ico" : "icon.png"),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadFile("loading.html");

  // External links open in the user's default browser, not inside the app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("close", (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

async function loadDashboard() {
  if (!mainWindow) return;
  const ok = await waitForApi(40);
  if (!ok) {
    mainWindow.webContents.executeJavaScript(
      `document.body.innerHTML = '<div style="display:grid;place-items:center;height:100vh;font-family:system-ui;color:#e9f2f8;background:#08131d"><div style="text-align:center"><h1 style="font-size:1.6rem">Backend not reachable</h1><p style="color:#9fb4c3">Could not start the Tickwise service. Check the logs and restart.</p></div></div>'`,
    );
    return;
  }
  mainWindow.loadURL(API_URL);
}

// ─── Tray ───────────────────────────────────────────────────────

function buildTrayMenu() {
  return Menu.buildFromTemplate([
    {
      label: "Open Dashboard",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    { type: "separator" },
    {
      label: "Quit Tickwise",
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);
}

function createTray() {
  const iconPath = path.join(
    __dirname,
    "build",
    process.platform === "darwin" ? "icon-32.png" : process.platform === "win32" ? "icon.ico" : "icon-64.png",
  );
  tray = new Tray(nativeImage.createFromPath(iconPath));
  tray.setToolTip("Tickwise");
  tray.setContextMenu(buildTrayMenu());
  tray.on("click", () => {
    if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
    }
  });
}

// ─── App lifecycle ──────────────────────────────────────────────

// One-instance lock so the user can't spawn a second Electron process
// (and a second backend) by double-clicking the icon twice.
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    createWindow();
    createTray();
    await startBackend();
    await loadDashboard();
  });

  app.on("activate", () => {
    if (mainWindow === null) {
      createWindow();
      loadDashboard();
    } else {
      mainWindow.show();
    }
  });

  app.on("before-quit", () => {
    isQuitting = true;
    stopBackend();
  });

  // We deliberately keep the app running on macOS+Linux when all windows
  // close — the tray icon is still there.
  app.on("window-all-closed", () => {
    // no-op
  });
}
