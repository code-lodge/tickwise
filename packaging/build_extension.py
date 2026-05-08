"""Bundle the browser extension for store submission.

Produces:
    dist/tickwise-extension-chrome-{ver}.zip   (Chrome Web Store)
    dist/tickwise-extension-firefox-{ver}.xpi  (Firefox AMO)

Each archive contains exactly the files listed in `_INCLUDE`, with the
correct manifest swapped in. We strip the README, .DS_Store, and any
platform-specific manifest from the wrong target.

Run from the project root:
    python packaging/build_extension.py
"""

from __future__ import annotations

import logging
import shutil
import sys
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("ext")

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "browser-extension"
DIST = ROOT / "dist"
VERSION = "1.0.0"

_INCLUDE = (
    "background.js",
    "content.js",
    "popup",
    "options",
    "icons",
)


def _copy_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _stage(target_dir: Path, manifest_src: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)
    for name in _INCLUDE:
        _copy_tree(EXT / name, target_dir / name)
    shutil.copy2(manifest_src, target_dir / "manifest.json")


def _zip(src: Path, out: Path) -> None:
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in src.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(src))
    log.info("wrote %s (%.0f KB)", out.name, out.stat().st_size / 1024)


def main() -> int:
    if not EXT.is_dir():
        sys.exit("browser-extension/ not found")
    DIST.mkdir(exist_ok=True)

    chrome_dir = DIST / "ext-chrome"
    firefox_dir = DIST / "ext-firefox"

    _stage(chrome_dir, EXT / "manifest.json")
    _zip(chrome_dir, DIST / f"tickwise-extension-chrome-{VERSION}.zip")

    _stage(firefox_dir, EXT / "manifest.firefox.json")
    _zip(firefox_dir, DIST / f"tickwise-extension-firefox-{VERSION}.xpi")

    shutil.rmtree(chrome_dir)
    shutil.rmtree(firefox_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
