"""Cross-platform build orchestrator for Tickwise.

Pipeline:

    1. ng build → tickwise/static/                (dashboard production bundle)
    2. PyInstaller(packaging/tickwise.spec) → dist/Tickwise/
    3. Per-platform packager
       - Windows: makensis packaging/installer.nsi → dist/tickwise-setup-{ver}.exe
       - macOS:   create-dmg dist/Tickwise.app → dist/Tickwise-{ver}.dmg
       - Linux:   appimagetool dist/Tickwise → dist/Tickwise-{ver}.AppImage

Each step is skipped (with a warning) when its tooling is missing — this
script is a checklist runner, not a hermetic build environment. CI is
expected to install the right tools before invoking it.

Usage:
    python packaging/build.py [--skip-dashboard] [--skip-installer]
"""

from __future__ import annotations

import argparse
import logging
import platform
import shutil
import subprocess  # noqa: S404 — invoking trusted local toolchains
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("build")

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
DASHBOARD = ROOT / "dashboard"
SPEC = ROOT / "packaging" / "tickwise.spec"
NSI = ROOT / "packaging" / "installer.nsi"

VERSION = "1.0.0"


def run(cmd: list[str], *, cwd: Path | None = None) -> int:
    log.info("$ %s", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(cwd) if cwd else None)  # noqa: S603


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


def build_dashboard() -> None:
    if not (DASHBOARD / "package.json").is_file():
        log.warning("dashboard/package.json missing — skipping dashboard build")
        return
    npm = "npm.cmd" if platform.system() == "Windows" else "npm"
    if not have(npm):
        log.warning("%s not on PATH — skipping dashboard build", npm)
        return
    if run([npm, "ci"], cwd=DASHBOARD) != 0:
        sys.exit("dashboard: npm ci failed")
    if run(
        [
            npm,
            "run",
            "build",
            "--",
            "--configuration=production",
            "--output-path=../tickwise/static",
        ],
        cwd=DASHBOARD,
    ) != 0:
        sys.exit("dashboard: build failed")


def build_pyinstaller() -> None:
    if not have("pyinstaller"):
        sys.exit("pyinstaller not on PATH — install with `pip install pyinstaller`")
    if DIST.exists():
        shutil.rmtree(DIST)
    if run(["pyinstaller", str(SPEC), "--clean", "--noconfirm"], cwd=ROOT) != 0:
        sys.exit("pyinstaller failed")


def build_windows_installer() -> None:
    if not have("makensis"):
        log.warning("makensis not on PATH — skipping NSIS installer")
        return
    run(["makensis", f"/DVERSION={VERSION}", str(NSI)], cwd=ROOT / "packaging")


def build_macos_dmg() -> None:
    app = DIST / "Tickwise.app"
    if not app.exists():
        log.warning("dist/Tickwise.app missing — skipping DMG")
        return
    if not have("create-dmg"):
        log.warning("create-dmg not installed (`brew install create-dmg`) — skipping DMG")
        return
    out = DIST / f"Tickwise-{VERSION}.dmg"
    if out.exists():
        out.unlink()
    run([
        "create-dmg",
        "--volname", "Tickwise",
        "--window-size", "640", "400",
        "--icon-size", "96",
        "--app-drop-link", "480", "180",
        str(out),
        str(app),
    ])


def build_linux_appimage() -> None:
    bundle = DIST / "Tickwise"
    if not bundle.exists():
        log.warning("dist/Tickwise/ missing — skipping AppImage")
        return
    if not have("appimagetool"):
        log.warning("appimagetool not on PATH — skipping AppImage")
        return
    appdir = DIST / "Tickwise.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    shutil.copytree(bundle, appdir / "usr" / "bin")
    (appdir / "AppRun").write_text(
        "#!/bin/sh\nexec $(dirname $(readlink -f $0))/usr/bin/tickwise\n",
        encoding="utf-8",
    )
    (appdir / "AppRun").chmod(0o755)
    (appdir / "tickwise.desktop").write_text(
        "[Desktop Entry]\nName=Tickwise\nExec=tickwise\nIcon=tickwise\nType=Application\n"
        "Categories=Utility;\n",
        encoding="utf-8",
    )
    run(["appimagetool", str(appdir), str(DIST / f"Tickwise-{VERSION}.AppImage")])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-dashboard", action="store_true")
    parser.add_argument("--skip-installer", action="store_true")
    args = parser.parse_args()

    if not args.skip_dashboard:
        build_dashboard()
    build_pyinstaller()
    if args.skip_installer:
        return
    system = platform.system()
    if system == "Windows":
        build_windows_installer()
    elif system == "Darwin":
        build_macos_dmg()
    elif system == "Linux":
        build_linux_appimage()
    else:
        log.warning("unknown platform %s — skipping installer step", system)


if __name__ == "__main__":
    main()
