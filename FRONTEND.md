# BidGuard AI — Frontend Prototype

A static, dependency-free HTML/CSS/JS frontend for an AI-powered bid
compliance verification platform for GeM procurement. No build tools, no
framework, no backend — open it directly in a browser or plug your team's
backend into the JS files marked with `TODO (backend)` comments.

Single-role product: every tender, bidder record, verification, and final
decision is entered and validated by the **Procurement Officer**. There is
no separate login for other roles.

## How to run

1. Open the folder in VS Code.
2. Right-click `index.html` → **Open with Live Server** (recommended, so
   relative links and fonts behave correctly), or just double-click
   `index.html` to open it in a browser.
3. Walk the flow in order: **Login → Dashboard → Tender Detail → Upload
   Bidder → Processing → Comparison → Investigation → Decision.**

No `npm install`, no bundler, nothing to compile.

## Folder structure

```
gem-compliance/
├── index.html               Login (single Procurement Officer role)
├── dashboard.html            Tender dashboard (stats, tender list)
├── tender-detail.html        Tender requirements + bidder list
├── upload-bidder.html        Drag-and-drop bidder document upload
├── processing.html           Animated verification pipeline
├── comparison.html           Sortable/filterable bidder comparison + Previous Performance
├── investigation.html        Score, evidence viewer, what-if simulator, AI copilot, audit trail, Previous Performance
├── decision.html             Officer approve / reject / send-for-review
├── css/
│   ├── tokens.css            Chromatic design tokens: colour, type, spacing, shadow, radius
│   ├── components.css        Buttons, cards, badges, status chips, forms, tables, chat, modal, side drawer
│   ├── layout.css            Grid + responsive utilities
│   ├── login.css             Login page only
│   ├── dashboard.css         Dashboard + comparison search/filter row
│   ├── tender-detail.css     Tender detail page only
│   ├── upload.css            Upload page only
│   ├── processing.css        Processing page only
│   ├── investigation.css     Investigation page only
│   ├── decision.css          Decision page only
│   └── previous-performance.css   "Previous performance" trigger button styling
├── js/
│   ├── main.js               Shared: officer menu, toast, modal helper
│   ├── login.js              Fake sign-in redirect (single role)
│   ├── dashboard.js          Tender search/status filter
│   ├── upload.js             Drag-and-drop + document checklist matching
│   ├── processing.js         Animated pipeline simulation
│   ├── comparison.js         Sortable/filterable bidder table
│   ├── investigation.js      Subtabs, what-if simulator, AI copilot (canned)
│   ├── file-viewer.js        "Open file" — mock certificate preview in a new tab
│   ├── previous-performance.js  "Previous Performance" side drawer — data + states
│   └── decision.js           Confirmation modal + decision recording
└── assets/                   (empty — drop real logos/exports here if needed)
```

## Design system — Chromatic theme

- **Palette:** a light, flat neutral background (`--paper`) with white
  cards, a vivid indigo primary (`--navy`, #3452FF) and a violet secondary
  accent (`--brass`, #7C4DFF), plus clear green/amber/red for risk status.
  All colours live in `css/tokens.css` — change them there and the whole
  app follows.
- **Shape:** rounded corners (`--radius: 14px`), soft drop shadows instead
  of hard borders, and simple underline tabs — a clean, modern,
  professional look appropriate for a government-enterprise tool without
  being decorative.
- **Type:** IBM Plex Sans (body), IBM Plex Sans Condensed (labels/tabs),
  IBM Plex Mono (every ID, code, score and timestamp).
- **Status chips:** the old rubber-stamp motif is now a simple colour-coded
  pill (`.stamp`) — Verified / Discrepancy / Review / Approved / Rejected —
  easy to scan across busy tables and dashboards.

## New in this revision

**1. Single login, single role.** The Officer/Auditor/Admin role picker was
removed. `index.html` signs in one Procurement Officer only, and the
dashboard's "Trust principle" card states plainly that all bidder data
entry, verification and final decisions are performed and validated by
that officer.

**2. "Open file" on every requirement.** On `investigation.html`, under
**Transparent compliance score**, each requirement row now has an
**Open file** button. It opens a generated mock certificate preview in a
new browser tab via `js/file-viewer.js`. Replace `generateMockDocument()` /
the Blob URL there with a real document-fetch endpoint when available —
the calling code (`data-open-file="<label>"` on any button) doesn't need
to change.

**3. Previous Performance drawer.** A secondary, non-primary button —
**📊 Previous performance** — appears next to each bidder on
`comparison.html` (table column) and on the bidder header of
`investigation.html`. Clicking it slides in a right-side drawer
(~460px, backdrop, ESC-to-close, scrollable, doesn't navigate away)
showing:
- Performance summary (previous/completed/delayed/active contracts, major
  defaults, quality acceptance %, historical compliance issues)
- Performance Insight
- Advisory
- Watch For
- A fixed footer: *"Historical performance is advisory only. Final
  procurement decisions remain with the Procurement Officer."*

This is **decision-support only** — it never modifies the compliance
score, risk level, requirement statuses, or auto-selects a bidder.

Implementation notes:
- All logic lives in `js/previous-performance.js`, in one reusable
  drawer (`#ppOverlay`/`#ppBody`) driven by `data-pp-open` +
  `data-pp-bidder="<key>"` + `data-pp-name="<fallback label>"` attributes
  on any trigger button — nothing is duplicated per bidder.
- Temporary synthetic demo data for three bidders (`A` = ABC Technologies,
  `B` = XYZ Enterprises, `C` = LMN Corp) lives in the `PERFORMANCE_DATA`
  object at the top of the file, isolated from assessment/scoring data.
- Any bidder key not in `PERFORMANCE_DATA` (e.g. `PQR`, `DEF` in the demo)
  resolves to the **No data** state, so that state is demonstrable too.
- States implemented: **Loading** (skeleton), **Success**, **No data**,
  **Error** (with Retry) — see `fetchPerformance()`, which currently
  resolves from the local object on a short delay. Replace it with a real
  `fetch('/api/bidders/:id/previous-performance')` call later; keep the
  same response shape and the render functions won't need to change.

## What's wired up vs. what's mock

This is a **frontend-only** prototype:

- Login "authenticates" anything and redirects to the dashboard.
- Tender/bidder data, evidence, scores and audit trail entries are static
  sample data in the HTML.
- Drag-and-drop upload accepts real files and matches them to a checklist
  by filename keyword (no OCR — that's a backend job).
- The verification pipeline on `processing.html` is a timed animation, not
  a real job queue.
- The AI Copilot on `investigation.html` answers from a small set of
  canned responses matched by keyword.
- The What-If Simulator recalculates a score client-side from fixed point
  values.
- "Open file" opens a generated placeholder document, not a real file.
- Previous Performance uses fixed demo data for three bidders.

## Handing off to backend

- `js/login.js` → replace the `setTimeout` redirect with a real auth call.
- `js/upload.js` → replace `addFiles()`'s checklist matcher with a real
  OCR/classification API response.
- `js/processing.js` → drive `setRowState()` from real job-status events
  instead of the fixed timer.
- `js/investigation.js` → replace the `responses` array with a call to
  your RAG/LLM copilot endpoint; replace the what-if math with a call to
  the risk engine.
- `js/file-viewer.js` → replace `generateMockDocument()` with a fetch of
  the bidder's actual stored document and open/render that instead.
- `js/previous-performance.js` → replace `PERFORMANCE_DATA` +
  `fetchPerformance()` with a real
  `GET /api/bidders/:bidder_id/previous-performance` call, keeping the
  same response shape.
- `js/decision.js` → replace the toast/local state with a POST to your
  audit-log + decision-recording endpoint.

**Do not change on the backend side without coordinating:** the assessment
API contract, scoring/risk logic, compliance rules, or any existing
validated bidder scores. Previous Performance and Open File are additive,
advisory panels only — they must never modify or auto-decide anything in
the core assessment pipeline.
