# GymsharkNexus — UI Design System

> Internal operations console for the Gymshark AI influencer pipeline.
> Built with Next.js 16 + Tailwind CSS v4 + shadcn/ui. Dark-only, no light mode.

---

## 1. Brand Identity

| Property | Value |
|----------|-------|
| Product name | **GymsharkNexus** |
| Wordmark style | `GYMSHARK` (white) + `NEXUS` (lime) |
| Aesthetic | Military ops console · dark industrial · precision fitness |
| Tagline pattern | `● LIVE` prefix on active page labels |
| Font personality | Heavy black numerics, mono labels, regular body — never light/thin |

---

## 2. Design Tokens

### 2.1 Colour Palette

#### Surfaces (dark → light)
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg` | `#0A0A0A` | Page background |
| `--panel` | `#121414` | Primary panel / card background |
| `--panel-2` | `#16191A` | Elevated panel (section headers) |
| `--panel-3` | `#0C0F0F` | Recessed input / dropdown background |
| `--panel-h` | `#1A1D1E` | Panel hover state |

#### Borders
| Token | Value | Usage |
|-------|-------|-------|
| `--border` | `#1F2937` | Default border |
| `--border-2` | `rgba(255,255,255,0.10)` | Subtle border (images, avatars) |
| `--border-3` | `rgba(255,255,255,0.16)` | Medium-emphasis border |

#### Text
| Token | Hex | Usage |
|-------|-----|-------|
| `--t1` | `#F4F4F5` | Primary text — headings, values, handles |
| `--t2` | `#9CA0A6` | Secondary text — descriptions, subtitles |
| `--t3` | `#5B5F66` | Tertiary text — labels, mono metadata |
| `--t4` | `#3A3D43` | Muted text — timestamps, separators |

#### Brand Accent — Neon Lime
| Token | Value | Usage |
|-------|-------|-------|
| `--lime` | `#95FF00` | Primary accent: CTAs, active states, key numbers |
| `--lime-2` | `#B6FF3D` | Lime hover |
| `--lime-bg` | `rgba(149,255,0,0.10)` | Lime tinted background |
| `--lime-glow` | `rgba(149,255,0,0.32)` | Box-shadow glow colour |

#### Semantic Status
| Token | Hex | Meaning |
|-------|-----|---------|
| `--amber` | `#FFB800` | Warning · human review needed · borderline |
| `--orange` | `#FF6B35` | Destructive / error |

### 2.2 Typography

| Role | Font | Weight | Size | Tracking |
|------|------|--------|------|----------|
| Display numeral | Inter | 900 (Black) | 52–64px | -0.03em |
| Page title | Inter | 900 (Black) | 32–48px | -0.025em |
| Section heading | Inter | 700 (Bold) | 11–13.5px | 0.08–0.14em UPPER |
| Body | Inter | 400 | 13–14px | normal |
| Meta / label | JetBrains Mono | 400–600 | 9–11px | 0.06–0.22em UPPER |

> **Rule:** All metadata, timestamps, units, status labels, and KPI subtitles use `font-mono` (JetBrains Mono). All headings and numerics use Inter.

### 2.3 Spacing

The layout uses a strict **4px grid**. Common values: `2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 32, 40`.

### 2.4 Border Radius

| Scale | Value | Usage |
|-------|-------|-------|
| `rounded` | `4px` | Badges, small chips |
| `rounded-md` | `6px` | Cards, panels, textareas |
| `rounded-lg` | `8px` | Section cards, queue items |
| `rounded-full` | `9999px` | CTA buttons, avatar, badges |

---

## 3. Shell Layout

### 3.1 Overall Grid

```
┌─────────────────────────────────────────────────────┐
│                   TOPBAR (52px)                     │  ← sticky, z-10
├────────────┬────────────────────────────────────────┤
│            │                                        │
│  SIDEBAR   │           PAGE CONTENT                 │
│ 260px      │           fills remaining              │
│ (collapses │           viewport                     │
│  to 72px)  │                                        │
│            │                                        │
└────────────┴────────────────────────────────────────┘
```

### 3.2 Topbar (height: 52px)

```
[ ■ Logo ] [ GYMSHARK NEXUS ] [ / ] [ ● LIVE  Page Name ]  ···  [ 🔍 ] [ ? ] [ 🔔● ] [ DK ]
```

- Background: `--panel`, bottom border: `--border`
- Brand mark: 20×20px icon + wordmark
- Page breadcrumb: mono text, lime dot + "LIVE" prefix
- Right actions: 32×32px icon buttons with `hover:bg-panel-h`
- Avatar: 30×30px circle, gradient fill, lime initials

### 3.3 Sidebar (width: 260px · collapsed: 72px)

- Background: `--panel`, right border
- Each nav item: `grid-cols-[36px_1fr_12px]`, 36×36px icon box, phase label + desc + Live badge
- Active state: `bg-lime/12 border-lime card-glow-active`
- Hover state: `bg-lime/10 border-lime translate-x-[2px]`
- Collapse toggle: chevron button top-right, state persisted to `localStorage`
- Footer: operator name + settings icon

### 3.4 Page Content Area

All pages scroll independently inside `main`. The topbar and sidebar are sticky.

---

## 4. Global Effects & Animations

### 4.1 Glow Effects

```css
/* Active card / selected queue item */
.card-glow-active {
  box-shadow: 0 0 0 1px var(--lime), 0 0 24px -8px var(--lime-glow);
}

/* Primary CTA buttons */
.cta-glow {
  box-shadow: 0 12px 32px -10px var(--lime-glow);
}
```

### 4.2 Animations

| Class | Behaviour |
|-------|-----------|
| `animate-pulse-dot` | 2s ease-in-out opacity pulse (1 → 0.35 → 1) — live indicator dots |
| `animate-fill` | 1.2s cubic-bezier bar fill from 0% to target width — progress bars |

### 4.3 Hover Patterns

- **Card hover:** `hover:-translate-y-[3px]` + `hover:shadow-[0_24px_60px_-20px_var(--lime-glow)]`
- **Top accent bar:** `h-[3px] bg-lime scale-x-0 → group-hover:scale-x-100` (origin-left, 350ms)
- **CTA button:** `hover:-translate-y-0.5` lift
- **Sidebar items:** `hover:translate-x-[2px]` nudge right
- **Queue items:** `border-border → hover:border-t3`

### 4.4 Transitions

All transitions use either `duration-200` (fast UI) or `duration-300` (layout) with default `ease` unless specified.

---

## 5. Screens

### 5.1 Master Console (Dashboard `/`)

**Layout:** Single scrollable column, max-width 1440px, `p-10`

**Sections:**
1. **Hero block** — `grid-cols-[1fr_auto]`: left = eyebrow label + display title, right = session metadata (mono, right-aligned)
2. **KPI Strip** — `grid-cols-3` panel, each cell has: pulse dot + mono label, 52px black numeral + unit, lime delta line
3. **Platform Modules** — `grid-cols-3` portal cards, min-height 360px each. Contains: number, large title (48px black), description, Live badge, lime CTA button. Hover = card lift + top accent bar
4. **Activity Feed** — bordered panel, header row, divided list. Each row: timestamp · status dot · rich text with lime-coloured target handle

**KPI numeral pattern:** Split on `.` — integer part in white, decimal in lime italic.

---

### 5.2 Discovery (`/discovery`)

**Layout:** Three-column fixed grid `grid-cols-[280px_1fr_340px]`, full viewport height, no scroll on outer container.

```
┌─────────────────┬────────────────────────┬──────────────────────┐
│ Creator         │ Content Theater        │ Creator Insights     │
│ Shortlist Queue │                        │                      │
│ 280px           │ flex-1 (scrollable)    │ 340px (scrollable)   │
│                 │                        │                      │
│ Header          │ Handle + name          │ Avatar + stats card  │
│ Niche/Status    │ Cover image + play btn │ GFS score circle     │
│ filters         │ Video meta row         │ AI context signals   │
│                 │ Feed tabs              │ Social profiles      │
│ Scrollable      │ Tab content            │ CRM ladder dropdown  │
│ queue list      │                        │                      │
│                 │                        ├──────────────────────┤
│                 │                        │ Move to Outreach CTA │
└─────────────────┴────────────────────────┴──────────────────────┘
```

**Queue Item:** Avatar (40×40 rounded-full) + handle + niche/follower mono label + GFS badge (lime/amber)

**GFS Score Circle:** 80×80px, `border-4 border-lime` (or amber), 28px black score numeral inside. Tier badge pill below.

**AI Context Signals:** Lime-on-lime-bg chip tags: `#NICHE`, `GFS: X.X`, `AUTH: XX`, `SENTIMENT: XX%`, `RISK: LEVEL`

**Cover image:** 16:9 aspect ratio with crosshair overlay (lime/20 lines + corner brackets), centred lime play button

---

### 5.3 Outreach War Room (`/outreach`)

**Layout:** Three-column fixed grid `grid-cols-[280px_1fr_380px]`, full viewport height.

```
┌─────────────────┬────────────────────────┬──────────────────────┐
│ Outreach Queue  │ Data Dossier           │ Action Execution     │
│ 280px           │ flex-1 (scrollable)    │ 380px                │
│                 │                        │                      │
│ Creator cards   │ Large avatar + handle  │ CRM Ladder dropdown  │
│ with status     │ 4-col KPI grid         │                      │
│ badges          │ Score breakdown bars   │ Email textarea       │
│                 │ Campaign projections   │ (editable, 256px)    │
│                 │ Social presence list   │                      │
│                 │                        │ Word count + source  │
│                 │                        ├──────────────────────┤
│                 │                        │ Send CTA button      │
└─────────────────┴────────────────────────┴──────────────────────┘
```

**Status Badges (queue items):**
| Status | Background | Text | Dot |
|--------|-----------|------|-----|
| Ready to Contact | `bg-lime/15 border-lime/25` | lime | lime pulse |
| Human Review | `bg-amber/15 border-amber/25` | amber | amber static |
| Drafting | `bg-t3/15 border-t3/25` | t2 | t3 static |

**Score Breakdown:** Labelled progress bars — `h-1.5 bg-panel-h` track, `bg-lime` fill with `animate-fill`. Three metrics: Authenticity, Niche Alignment, Engagement (0–100).

**Campaign Projections:** `grid-cols-3` mini-stat cards, Est. Reach + Proj. Conversions + ROI Multiple (lime).

**Email Composer:** `bg-panel-3 border-border-2` textarea, `focus:border-lime focus:ring-2 focus:ring-lime/10`. Below: mono metadata line `Tier X · Deal Type · N words` + `LLM Generated / Template Draft` source tag.

**Send Button (states):**
- Default: `bg-lime text-[#0A0A0A] cta-glow hover:-translate-y-0.5`
- Sending: dimmed, disabled
- Sent: `bg-lime/15 border-lime/30 text-lime` with ✓ checkmark

---

## 6. Reusable Component Patterns

### 6.1 Section Header Row
```
[mono label 10–11px UPPER]    [mono secondary 10px t4 UPPER]
```

### 6.2 Panel Card
- `bg-panel border border-border rounded-md` (or `rounded-lg` for inner cards)
- Optional top accent bar: `absolute top-0 left-0 right-0 h-0.5 bg-lime scale-x-0 group-hover:scale-x-100`

### 6.3 Stat Block (KPI cell)
```
[● mono label]
[52px black numeral] [unit mono]
[delta mono — lime or amber]
```

### 6.4 Avatar
- `rounded-full bg-cover bg-center`
- Standard sizes: 40×40px (queue), 56×56px (insight panel), 80×80px (dossier header)
- Border: `border border-border-2` (default) · `border-2 border-lime` (active/selected)

### 6.5 Status Pill / Badge
```
[dot 6×6px rounded-full] [LABEL MONO 9px]
```
- Padded: `px-2 py-1 rounded-full border`
- Always uppercase tracking-[0.06–0.1em]

### 6.6 CTA Button (primary full-width)
```css
px-4 py-3.5 rounded-full
bg-lime text-[#0A0A0A]
font-black text-[12–13px] tracking-[0.12–0.14em] uppercase
cta-glow
hover:bg-lime-2 hover:-translate-y-0.5
```

### 6.7 Dropdown / Collapsible (CRM Ladder)
- Trigger: `bg-panel-3 hover:bg-panel-h`, chevron rotates 180° when open
- Items: full-width buttons, `border-b border-border`, active = `text-lime bg-lime-bg`

### 6.8 Progress Bar
```
h-1.5 bg-panel-h rounded-full overflow-hidden
  → div: h-full bg-lime animate-fill
```

### 6.9 Tab Row
```
border-b border-border
  → buttons: px-4 py-2.5, border-b-2 -mb-px
  → active: text-lime border-lime
  → inactive: text-t3 border-transparent hover:text-t1
```

### 6.10 Icon Button (topbar / sidebar)
```
w-8 h-8 rounded-md
text-t2 hover:bg-panel-h hover:text-t1
transition-all duration-150
```

---

## 7. Iconography

All icons are inline SVG React components in `components/icons.tsx`.

| Icon | Usage |
|------|-------|
| `BrandLogo` | Topbar brand mark |
| `DashboardIcon` | Sidebar — Master Console |
| `DiscoveryIcon` | Sidebar + portal card — Discovery |
| `OutreachIcon` | Sidebar + portal card — Outreach |
| `GarmentIcon` | Sidebar + portal card — Garment |
| `PlayIcon` | Content theater play button |
| `SendIcon` | Outreach send CTA |
| `ArrowRightIcon` | Discovery → Outreach CTA |
| `ArrowUpRightIcon` | Portal card external link |
| `YouTubeIcon` | Social profile row |
| `InstagramIcon` | Social profile row |
| `TikTokIcon` | Social profile row |
| `SearchIcon` | Topbar |
| `HelpIcon` | Topbar |
| `NotificationIcon` | Topbar (with lime dot badge) |
| `SettingsIcon` | Sidebar footer |
| `ChevronLeft / Right` | Sidebar collapse, CRM navigation |

---

## 8. Loading & Empty States

**Page loading:**
```
Centred: [● lime pulse dot] "Loading pipeline data…" mono uppercase
```

**Activity feed empty:**
```
px-6 py-8 text-center
font-mono text-[11px] text-t4 tracking-[0.1em] uppercase
"Loading pipeline activity…"
```

**Draft generating:**
```
Inline next to label: [● lime pulse] "Generating…" lime mono
Textarea: disabled + opacity-60
```

---

## 9. Navigation Structure

```
/ ─────────────────── Master Console (dashboard)
/discovery ─────────── Discovery Matrix
/outreach ──────────── Outreach War Room
/garment ───────────── Garment Tech (coming soon)
```

Navigation lives in the sidebar. The topbar shows the current page name. Both are always visible; only page content scrolls.

---

## 10. Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Plain HTML + vanilla JS (no build step) |
| Styling | Custom CSS variables (dark design tokens, 5 CSS files) |
| Fonts | Inter (display) · JetBrains Mono (meta) via Google Fonts |
| Backend (primary) | FastAPI (Python) — `ui/api/main.py`, port 8001, also serves frontend |
| Backend (extended) | FastAPI (Python) — `ui/backend/main.py`, port 8000, full skill integration |
| LLM | TritonAI proxy (`api-llama-4-scout`) via `utils/connect.py` |
| RAG | `rag/retrieval.py` — cosine similarity over embedded brand documents |
| Data | Real CSVs in `data/` — 14 AI-scored creator profiles, campaign history, CRM |
| YouTube | YouTube Data API v3 (`googleapiclient`) — live video fetch |
| Reference prototype | Next.js 16 + Tailwind v4 + shadcn/ui in `design-system-reference/` (not production) |

---

## 11. File Map

```
ui/
├── frontend/                     ← Production single-page app
│   ├── index.html                ← All screens (scoring, profile, outreach,
│   │                                brief, analytics, leaderboard) in one file
│   └── css/
│       ├── styles.css            ← Design tokens + base reset
│       ├── styles-layout.css     ← Sidebar, topbar, shell grid
│       ├── styles-pages.css      ← Page-level layout
│       ├── styles-outreach.css   ← Outreach 3-panel layout
│       └── styles-theater.css    ← Video content theater
├── api/
│   ├── __init__.py
│   └── main.py                   ← FastAPI: REST endpoints + serves frontend at /
├── backend/
│   ├── main.py                   ← FastAPI: richer endpoints with full skill helpers
│   └── start.sh                  ← uv run uvicorn ui.backend.main:app --port 8000
├── design-system-reference/      ← Next.js reference prototype (not production)
│   ├── app/
│   │   ├── globals.css           ← Design tokens as Tailwind CSS variables
│   │   ├── layout.tsx            ← Root layout (fonts, theme)
│   │   ├── page.tsx              ← Master Console
│   │   ├── discovery/page.tsx    ← Discovery screen
│   │   └── outreach/page.tsx     ← Outreach War Room
│   ├── components/
│   │   ├── app-shell.tsx         ← Topbar + Sidebar wrapper
│   │   ├── topbar.tsx
│   │   ├── sidebar.tsx
│   │   ├── icons.tsx             ← Inline SVG icon components
│   │   └── ui/                   ← shadcn/ui primitives
│   └── next.config.mjs           ← Rewrites /api/* → FastAPI :8000
├── DESIGN.md                     ← This file
└── README.md                     ← Setup and screen reference
```
