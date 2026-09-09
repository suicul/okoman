# ОКО БОД Manager UI 2.0 Design System

## 1. Atmosphere & Identity

Полевой сервисный пульт: спокойный, технический и читаемый при плохом освещении и на старом ноутбуке. Интерфейс должен помогать наладчику быстро понять состояние платы, подключиться, выполнить диагностику и безопасно применить настройки. Фирменный приём — тонкая бирюзовая линия состояния на фоне нейтральных графитовых поверхностей.

## 2. Color

### Palette

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Surface/primary | BG_PRIMARY | #0D1117 | Main application background |
| Surface/secondary | BG_SECONDARY | #161B22 | Sidebar, panels, cards |
| Surface/tertiary | BG_TERTIARY | #21262D | Inputs, hover, inactive controls |
| Text/primary | TEXT_PRIMARY | #E6EDF3 | Main text and values |
| Text/secondary | TEXT_SECONDARY | #A0AAB4 | Labels, hints, metadata |
| Border/default | BORDER | #30363D | Dividers and controls |
| Accent/primary | ACCENT | #00D4AA | Focus, active navigation, primary actions |
| Accent/hover | ACCENT_HOVER | #00F0C0 | Hover and emphasis |
| Status/success | SUCCESS | #44FF88 | Connected and passed |
| Status/warning | WARNING | #FFBB33 | Caution and pending |
| Status/error | DANGER | #FF5555 | Error and destructive actions |
| LED/off | LED_OFF | #333333 | Inactive hardware indicators |

Rules: one accent family, no gradients, no pure black, no decorative accent blobs. Status colors are semantic only.

## 3. Typography

| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| Page title | 20px | 700 | Window and primary page title |
| Section title | 16px | 600 | Card and screen headings |
| Body | 13px | 400 | Default desktop text |
| Body large | 14px | 500 | Primary actions and connection status |
| Caption | 11px | 400 | Hints, metadata, secondary labels |
| Data | 13px | 600 | Device values and diagnostic output |
| Terminal | 12px | 400 | Raw device output |

Font stack: Segoe UI, Arial, sans-serif. Terminal/data: Consolas, Courier New, monospace. Body text never below 11px because devices are field-used.

## 4. Spacing & Layout

Base unit: 4px.

| Token | Value | Usage |
|-------|-------|-------|
| space-1 | 4px | Icon and label gap |
| space-2 | 8px | Compact control group |
| space-3 | 12px | Input and row padding |
| space-4 | 16px | Standard panel padding |
| space-5 | 20px | Card content separation |
| space-6 | 24px | Page gutter and major panel padding |
| space-8 | 32px | Screen section separation |

Desktop minimum: 860x560 for 1024x600 field laptops. Default: 1100x700. Sidebar: 208px, collapsible only if a future compact mode is required. Content uses a single scrollable page per module; no horizontal scrolling.

Mobile uses 16dp page gutters, 12dp card spacing, portrait-first layout and touch targets of at least 44dp.

## 5. Components

### Navigation item
- Structure: icon, sentence-case label, active indicator.
- States: default, hover, active, focus, disabled.
- Active state uses ACCENT text and a 3px left rule; no filled pill.

### Service card
- BG_SECONDARY surface, BORDER 1px outline, 8px radius, 16px padding.
- Used for connection, device identity, diagnostics, and configuration groups.
- Never nest service cards inside each other.

### Status indicator
- 12px dot plus text label; color is semantic.
- Connected/success, pending/warning, error/disconnected.
- Status text always explains the state; color alone is insufficient.

### Field control
- Minimum 36px desktop height and 44dp mobile height.
- Visible focus border in ACCENT.
- Invalid/error text is inline and actionable.

### Primary action
- ACCENT fill, dark text, 36px desktop height, 44dp mobile height.
- Hover uses ACCENT_HOVER; pressed state darkens; disabled uses BG_PRIMARY and TEXT_SECONDARY.

## 6. Motion & Interaction

Micro interactions: 100–150ms ease-out. Panel and page changes: 200ms ease-in-out. No layout animation. All controls expose hover, pressed, focus and disabled states. Hardware LED flashes are event-driven and limited to 300ms. Respect reduced-motion where the platform exposes it.

## 7. Depth & Surface

Strategy: mixed but restrained. Service cards use BORDER with tonal BG_SECONDARY separation; no large shadows. Dropdowns and dialogs may use a subtle tinted shadow. Radius is 8px for cards and controls, 4px for compact status elements. Surfaces are functional, not decorative.
