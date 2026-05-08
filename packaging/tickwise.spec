# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Tickwise desktop app.

Produces a one-folder bundle:
- Windows  → dist/Tickwise/Tickwise.exe   (windowed, no console)
- macOS    → dist/Tickwise.app
- Linux    → dist/Tickwise/tickwise         (executable)

Bundles the dashboard build, the mobile PWA, the invoice templates,
and the cloudflared binary if it has been pre-downloaded into
packaging/vendor/. Heavyweight optional dependencies (PaddleOCR
models) are NOT bundled — they download lazily on first OCR call so
the installer stays under ~80 MB.

Run from the project root:
    pyinstaller packaging/tickwise.spec --clean --noconfirm
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path.cwd()
VENDOR = ROOT / "packaging" / "vendor"
DASHBOARD_BUILD = ROOT / "tickwise" / "static"
MOBILE_DIR = ROOT / "mobile"
INVOICE_TEMPLATES = ROOT / "tickwise" / "invoices" / "templates"

# Files copied into the bundle's data tree.
datas = [
    (str(INVOICE_TEMPLATES / "default.html"), "tickwise/invoices/templates"),
    (str(INVOICE_TEMPLATES / "default.css"),  "tickwise/invoices/templates"),
    (str(MOBILE_DIR), "mobile"),
]
if DASHBOARD_BUILD.is_dir():
    datas.append((str(DASHBOARD_BUILD), "tickwise/static"))
if VENDOR.is_dir():
    datas.append((str(VENDOR), "vendor"))

# RapidOCR ships its ONNX detection / recognition / classification models
# as data files inside the wheel. PyInstaller's default analysis misses
# them — collect_data_files walks the package and grabs the models, the
# default config.yaml, and the dictionary text files.
try:
    datas.extend(collect_data_files("rapidocr_onnxruntime", include_py_files=False))
except Exception:  # noqa: BLE001 — OCR is optional at packaging time
    pass

# Force-include modules PyInstaller can't see through dynamic imports.
hiddenimports = [
    "uvicorn.lifespan.on",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.loops.auto",
    *collect_submodules("tickwise"),
]

# Optional native deps — not always present, only ride along when installed.
for opt in ("weasyprint", "icalendar", "caldav", "qrcode", "rapidocr_onnxruntime", "onnxruntime"):
    try:
        hiddenimports.extend(collect_submodules(opt))
    except Exception:  # noqa: BLE001
        pass

excludes = [
    "tkinter",
    "matplotlib",
    "PyQt5",
    "PyQt6",
    "PySide6",
    "test",
]

a = Analysis(
    ["../tickwise/__main__.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Tickwise",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "packaging" / "icons" / "tickwise.ico") if (ROOT / "packaging" / "icons" / "tickwise.ico").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Tickwise",
)

# macOS bundle wrapper.
import sys

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Tickwise.app",
        icon=str(ROOT / "packaging" / "icons" / "tickwise.icns") if (ROOT / "packaging" / "icons" / "tickwise.icns").is_file() else None,
        bundle_identifier="io.code-lodge.tickwise",
        info_plist={
            "CFBundleName": "Tickwise",
            "CFBundleDisplayName": "Tickwise",
            "CFBundleShortVersionString": "1.0.0",
            "LSUIElement": True,  # menu-bar only, no Dock icon
            "NSAccessibilityUsageDescription": "Tickwise reads window titles to classify your activity.",
            "NSAppleEventsUsageDescription": "Tickwise observes the active application.",
        },
    )
