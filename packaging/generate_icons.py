"""Render the Tickwise clock-face icon at every size we need.

Used by the Electron build (build/icon.ico, build/icon.png) and the
PyInstaller spec (packaging/icons/tickwise.ico). Re-run whenever the
brand evolves.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = ROOT / "packaging" / "icons"
ELECTRON_BUILD = ROOT / "electron" / "build"

# Brand gradient endpoints (teal → cyan)
TEAL = (45, 212, 191, 255)   # #2dd4bf
CYAN = (56, 189, 248, 255)   # #38bdf8
INK = (12, 15, 28, 255)      # #0c0f1c
WHITE = (255, 255, 255, 255)


def _gradient_circle(size: int) -> Image.Image:
    """Diagonal teal→cyan gradient masked to a circle."""
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size - 2)
            r = int(TEAL[0] + (CYAN[0] - TEAL[0]) * t)
            g = int(TEAL[1] + (CYAN[1] - TEAL[1]) * t)
            b = int(TEAL[2] + (CYAN[2] - TEAL[2]) * t)
            base.putpixel((x, y), (r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    pad = max(1, size // 32)
    md.ellipse((pad, pad, size - pad, size - pad), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def _draw_icon(size: int) -> Image.Image:
    img = _gradient_circle(size)
    d = ImageDraw.Draw(img)
    cx = cy = size // 2

    # Inner ring (subtle, ink at low alpha)
    ring_pad = size // 8
    d.ellipse(
        (ring_pad, ring_pad, size - ring_pad, size - ring_pad),
        outline=(INK[0], INK[1], INK[2], 80),
        width=max(1, size // 40),
    )

    # Hour hand (pointing up)
    hand_w = max(2, size // 14)
    hour_len = size // 4
    d.line(
        [(cx, cy), (cx, cy - hour_len)],
        fill=INK,
        width=hand_w,
    )

    # Minute hand (pointing right)
    min_w = max(1, size // 18)
    min_len = int(size * 0.32)
    d.line(
        [(cx, cy), (cx + min_len, cy)],
        fill=INK,
        width=min_w,
    )

    # Center pin
    pin_r = max(2, size // 24)
    d.ellipse(
        (cx - pin_r, cy - pin_r, cx + pin_r, cy + pin_r),
        fill=INK,
    )
    return img


def main() -> None:
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    icons = {s: _draw_icon(s) for s in sizes}

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    ELECTRON_BUILD.mkdir(parents=True, exist_ok=True)

    # Per-size PNGs (used by Linux AppImage + dashboard favicons)
    for s, img in icons.items():
        out = ELECTRON_BUILD / f"icon-{s}.png"
        img.save(out)
        print(f"  wrote {out}")

    # Master 512×512 for electron-builder
    icons[512].save(ELECTRON_BUILD / "icon.png")
    print(f"  wrote {ELECTRON_BUILD / 'icon.png'}")

    # Multi-size ICO for Windows installer + tray
    ico_sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256)]
    icons[256].save(
        ICONS_DIR / "tickwise.ico",
        format="ICO",
        sizes=ico_sizes,
    )
    icons[256].save(
        ELECTRON_BUILD / "icon.ico",
        format="ICO",
        sizes=ico_sizes,
    )
    print(f"  wrote {ICONS_DIR / 'tickwise.ico'}")
    print(f"  wrote {ELECTRON_BUILD / 'icon.ico'}")


if __name__ == "__main__":
    main()
