# 🖌️ UI/UX Design Specification

## Design Direction

**Theme:** "Artist's sketchbook on a sunlit desk"
**Mood:** Calm, creative, analog-feeling but clean
**Palette:** Off-white paper base, warm ink tones, watercolor accent splashes
**Texture:** Subtle paper grain overlay (CSS noise or SVG filter)

---

## Typography

| Role         | Font                  | Source         |
|---|---|---|
| Display/Hero | `Playfair Display`    | Google Fonts   |
| Body/UI      | `DM Sans`             | Google Fonts   |
| Monospace    | `JetBrains Mono`      | Google Fonts (for word counter, metadata) |

---

## Color Palette (CSS Variables)

```css
:root {
  --color-bg:         #faf8f4;   /* warm off-white paper */
  --color-surface:    #f3efe8;   /* slightly deeper card bg */
  --color-border:     #ddd5c8;   /* soft warm border */
  --color-ink:        #2c2416;   /* near-black warm ink */
  --color-ink-muted:  #7a6f61;   /* muted secondary text */
  --color-accent:     #c0714b;   /* warm terracotta accent */
  --color-accent-2:   #6b9fb5;   /* soft watercolor blue */
  --color-success:    #5a8a6a;   /* muted green */
  --color-error:      #b85555;   /* muted red */
  --color-toast-bg:   #2c2416e6; /* semi-transparent ink */
}
```

---

## Texture

Apply a subtle paper texture using a CSS pseudo-element with an SVG noise filter or a base64 PNG overlay at ~4% opacity on `body`:

```css
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url('/static/images/paper-texture.jpg');
  opacity: 0.04;
  pointer-events: none;
  z-index: 9999;
}
```

---

## Page Designs

### `/` — Prompt Entry

```
┌─────────────────────────────────────┐
│  🎨  Watercolor AI         [Gallery]│  ← navbar, minimal
├─────────────────────────────────────┤
│                                     │
│   [Large display heading]           │
│   "Describe a scene."               │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  Textarea (4 rows)          │   │
│   │  placeholder: "a fox sit..."│   │
│   └─────────────────────────────┘   │
│   12 / 50 words  ←── live counter   │
│                                     │
│        [ Generate →  ]              │  ← accent button
│                                     │
└─────────────────────────────────────┘
```

- Word counter turns red and disables submit if > 50 words
- Button shows loading spinner on submit (before redirect fires)
- Subtle watercolor splash decorative SVG in background corner

---

### `/generating/<job_id>` — Status Page

```
┌─────────────────────────────────────┐
│  🎨  Watercolor AI         [Gallery]│
├─────────────────────────────────────┤
│                                     │
│        [Animated paint stroke]      │
│        "Painting your scene…"       │
│                                     │
│   Prompt: "a fox sitting by..."     │
│                                     │
│   [Elapsed timer: 0:04]             │
│                                     │
└─────────────────────────────────────┘
```

- Animated CSS paint-stroke loader (no GIFs)
- Elapsed time counts up every second
- Polls `/api/status/<job_id>` silently

---

### `/result/<job_id>` — Result Page

**Success:**
```
┌─────────────────────────────────────┐
│  🎨  Watercolor AI         [Gallery]│
├─────────────────────────────────────┤
│                                     │
│   ┌──────────────────────────────┐  │
│   │   [Generated image]          │  │← blurred by default
│   │   (blurred overlay)          │  │
│   └──────────────────────────────┘  │
│                                     │
│   [Reveal]  [Download]  [New →]     │
│                                     │
│   Prompt: "a fox sitting..."        │
│   Generated in 4.2s                 │
│                                     │
│   ╔════════════════════════════╗    │
│   ║ ✓ Done in 4.2s             ║    │← toast (auto-dismisses 5s)
│   ╚════════════════════════════╝    │
└─────────────────────────────────────┘
```

**Failure:**
```
│   ┌──────────────────────────────┐  │
│   │  💧 Couldn't paint this one  │  │
│   │  Reason: [error text]        │  │
│   └──────────────────────────────┘  │
│   [Try Again]                       │
│                                     │
│   ╔════════════════════════════╗    │
│   ║ ✗ Failed: Content blocked  ║    │← toast
│   ╚════════════════════════════╝    │
```

---

### `/gallery` — Gallery Page

```
┌─────────────────────────────────────┐
│  🎨  Watercolor AI         [Gallery]│
├─────────────────────────────────────┤
│  Past Works                         │
│                                     │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐   │
│  │img │  │img │  │ ✗  │  │... │   │  ← 4-col masonry/grid
│  │    │  │    │  │fail│  │    │   │
│  └────┘  └────┘  └────┘  └────┘   │
│  "a fox…" "sunset…" "ERROR" "tree" │
│  4.2s    3.8s    –        –        │
│                                     │
└─────────────────────────────────────┘
```

- Responsive Bootstrap grid (4 cols → 2 → 1)
- Each card: blurred thumbnail, prompt snippet, status badge, time
- Click → `/result/<job_id>`
- Failed cards shown with a muted error state card

---

## Toast Behavior

- Bootstrap 5 Toast component, custom styled
- Position: bottom-right
- Success: dark ink background, white text, checkmark icon
- Error: muted red background
- Auto-dismiss: 5 seconds
- Shows immediately on result page load via JS

---

## Responsive Breakpoints

| Breakpoint | Layout |
|---|---|
| `< 576px` | Single column, full-width textarea |
| `576–992px` | Centered container, 2-col gallery |
| `> 992px` | Max-width container, 4-col gallery |
