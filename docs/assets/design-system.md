# Code Lodge — Design System

Single CSS file (`design-system.css`) with the canonical Code Lodge brand
tokens and a small set of composable component classes. Drop it into any
Code Lodge product's marketing site or in-app shell to stay on-brand.

## Use it

```html
<link rel="stylesheet" href="assets/design-system.css" />
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

All tokens live on `:root` under the `--cl-*` namespace, all component
classes are prefixed `cl-` — collisions with app-specific styles are not
possible by accident.

## Tokens

| Token group | Examples |
| ----------- | -------- |
| Surface | `--cl-bg` `#08131d`, `--cl-bg-2` `#0c1d2a`, `--cl-panel`, `--cl-panel-strong` |
| Text | `--cl-text` `#e9f2f8`, `--cl-muted` `#9fb4c3`, `--cl-dim` |
| Brand accents | `--cl-accent` `#2dd4bf` (teal), `--cl-accent-2` `#38bdf8` (cyan), `--cl-violet` `#7c6af7` |
| Status | `--cl-good` `#22c55e`, `--cl-accent-warm` `#fb923c`, `--cl-critical` `#ef4444` |
| Geometry | `--cl-radius-sm` 8px, `--cl-radius` 14px, `--cl-radius-lg` 22px, `--cl-radius-pill` 999px |
| Shadows | `--cl-shadow-sm`, `--cl-shadow-md`, `--cl-shadow-lg` |
| Type | `--cl-font-display` (Space Grotesk), `--cl-font-body` (IBM Plex Sans), `--cl-font-mono` (JetBrains Mono) |
| Layout | `--cl-content-width` 1100px |
| Motion | `--cl-ease`, `--cl-focus-ring` |

## Components

| Class | Purpose |
| ----- | ------- |
| `.cl-shell` | Centered max-width container with side gutters |
| `.cl-nav`, `.cl-nav-inner`, `.cl-brand`, `.cl-brand-mark`, `.cl-nav-links`, `.cl-nav-cta` | Sticky blurred top nav + brand mark + GitHub CTA |
| `.cl-btn`, `.cl-btn-primary`, `.cl-btn-secondary`, `.cl-btn-ghost` | Three button variants — gradient, outline, ghost |
| `.cl-card`, `.cl-panel-strong` | Translucent card surfaces with stroke + shadow |
| `.cl-pill`, `.cl-pill-good`, `.cl-pill-warn`, `.cl-pill-critical`, `.cl-pill-dot` | Status pills with colored dot |
| `.cl-section`, `.cl-section-header`, `.cl-section-label`, `.cl-section-sub` | Section scaffolding with eyebrow label and centered intro |
| `.cl-accent-text` | Gradient (teal → cyan) text fill |
| `.cl-code-inline`, `.cl-codeblock`, `.cl-codeblock-head` | Inline + block code styling, with `.c`/`.k`/`.s` for highlighting |
| `.cl-footer`, `.cl-sep`, `.cl-made` | Centered marketing-site footer |
| `.cl-skip-link` | A11y skip-to-content for keyboard users |

## Per-product customization

Override the brand mark per app (`<span class="cl-brand-mark">T</span>`)
and the page-level radial gradients in body styles. Otherwise components
should compose unchanged across products.

For app-specific accents (e.g. shellwright's window-tile orange), define
new `--app-*` tokens *next to* the `--cl-*` ones and use both — never
overwrite the canonical `--cl-*` palette.
