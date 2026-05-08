#!/usr/bin/env node
/* Build the Python backend (PyInstaller) before electron-builder runs.
 *
 * Single-installer pipeline: `npm run build:win|mac|linux` from electron/
 * runs this first to produce dist/Tickwise/, then electron-builder picks
 * that up via `extraResources` and bundles it inside the Electron
 * installer. Net result: one user-facing artifact, no separate
 * standalone tray exe to install or confuse anyone.
 *
 * Skips the Python build if `--skip-backend` is in argv (CI escape
 * hatch when the backend was already built earlier in the pipeline).
 */

const { spawnSync } = require("child_process");
const { existsSync } = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const VENV_PY = process.platform === "win32"
  ? path.join(ROOT, ".venv", "Scripts", "python.exe")
  : path.join(ROOT, ".venv", "bin", "python");
const SPEC = path.join(ROOT, "packaging", "tickwise.spec");
const OUT_DIR = path.join(ROOT, "dist", "Tickwise");

if (process.argv.includes("--skip-backend")) {
  console.log("[build-backend] --skip-backend: skipping PyInstaller");
  process.exit(0);
}

if (!existsSync(VENV_PY)) {
  console.error(`[build-backend] No venv python found at ${VENV_PY}`);
  console.error("[build-backend] Run from the repo root:");
  console.error("    python -m venv .venv && .venv/Scripts/pip install -e . pyinstaller");
  process.exit(1);
}

if (!existsSync(SPEC)) {
  console.error(`[build-backend] PyInstaller spec missing: ${SPEC}`);
  process.exit(1);
}

console.log("[build-backend] Running PyInstaller...");
const result = spawnSync(
  VENV_PY,
  [
    "-m", "PyInstaller",
    SPEC,
    "--clean",
    "--noconfirm",
    "--distpath", path.join(ROOT, "dist"),
    "--workpath", path.join(ROOT, "build_pyinstaller"),
  ],
  { stdio: "inherit", cwd: ROOT },
);

if (result.status !== 0) {
  console.error(`[build-backend] PyInstaller failed (exit ${result.status})`);
  process.exit(result.status || 1);
}

if (!existsSync(path.join(OUT_DIR, "Tickwise.exe")) && !existsSync(path.join(OUT_DIR, "Tickwise"))) {
  console.error(`[build-backend] PyInstaller succeeded but ${OUT_DIR} is empty`);
  process.exit(1);
}

console.log(`[build-backend] OK → ${OUT_DIR}`);
