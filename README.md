# Kalastree Pulse

> Every day, the team reflects. The company learns. The tree grows.

Kalastree Pulse is a daily execution, reflection, and company-growth platform
for the Kalastree team. It is **not** a performance-monitoring tool — it
exists to build discipline, focus, and transparency around real company
progress, visualized as a tree that grows only when the company actually
moves forward.

This README is updated as each build phase lands. Current status: **Phase 12
— Polish (complete — all 12 phases done)**.

## Build phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Project setup — structure, FastAPI, Jinja2, static assets, config, logging, homepage | ✅ done |
| 2 | Authentication — name-only login, sessions | ✅ done |
| 3 | Home dashboard — tree visualization, mission progress | ✅ done |
| 4 | Daily reflection form | ✅ done |
| 5 | Submission experience — animations, confetti | ✅ done |
| 6 | Google Sheets integration | ✅ done |
| 7 | Admin dashboard | ✅ done |
| 8 | Business growth dashboard (configurable KPIs → tree rules) | ✅ done |
| 9 | Analytics — trends, heatmaps, export | ✅ done |
| 10 | AI insights | ✅ done |
| 11 | Mission dashboard (hero page) | ✅ done |
| 12 | Polish — dark mode, accessibility, micro-interactions | ✅ done |

Phases were built strictly in order; each one was fully functional before
the next began.

## Architecture

```
kalastree-pulse/
├── app/
│   ├── core/            # Cross-cutting concerns: settings, logging, templating
│   ├── models/           # Internal data representations
│   ├── schemas/          # Pydantic request/response contracts
│   ├── services/          # Business logic & external integrations (Sheets, AI, tree rules)
│   ├── routers/          # FastAPI route modules: pages, auth, one per URL area
│   ├── static/            # css/, js/, img/
│   ├── templates/          # Jinja2 templates (+ partials/ for shared fragments)
│   └── main.py            # App entrypoint: wires config, logging, sessions, static, routers
├── config/                # Admin-editable rules — tree_rules.json, team_roster.json, not code
├── credentials/           # Google service account key goes here (git-ignored, not the folder)
├── scripts/               # One-off maintenance scripts (Sheets connectivity check, ...)
├── logs/                  # Rotating log files (git-ignored)
├── Dockerfile             # Container image for Cloud Run / any Docker host
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

**Why this shape:**

- **`core/config.py`** centralizes every environment-dependent value behind
  a single `Settings` object (via `pydantic-settings`), read through
  `get_settings()`. Nothing else touches `os.environ` directly, so settings
  stay testable (override in tests) and every later phase (Sheets
  credentials, AI keys, Postgres DSN, JWT secret) has exactly one place to
  add a field.
- **`core/logging_config.py`** configures the root logger once at startup
  with console + rotating file handlers, so any module logs with
  `logging.getLogger(__name__)` and inherits both automatically. Rotation
  matters because this app runs continuously, day after day.
- **`routers/` vs `services/` vs `models`/`schemas`** is a deliberate
  separation: routers stay thin (parse request → call service → render
  response), services hold the logic and integrations, models/schemas
  separate "what we store" from "what we send over HTTP". This is what lets
  Phase 6 (Sheets) or Phase 10 (AI) be added as new services without
  touching how existing pages render.
- **`core/templating.py`** wraps `Jinja2Templates` with a `render_template()`
  helper that injects shared context (app identity, environment, the
  signed-in user's name) once, so routers don't repeat that boilerplate on
  every render call — one less thing to keep in sync as pages multiply.
- **Auth (Phase 2) is name-only, session-based, no user table.** A visitor
  types their name; the server validates it, stores it in a signed session
  cookie via Starlette's `SessionMiddleware` (signed with `SECRET_KEY`, no
  server-side session store), and every page reads `request.session`
  through `render_template()`. This is deliberately the simplest thing that
  works today — it's what "future ready" architecture in the config module
  is for: swapping in Postgres-backed sessions or JWTs later doesn't
  require touching how routers render pages, only how the session is
  populated.
- **The team roster (`services/team_roster.py`) is an optional layer on
  top of that, not a second auth system.** `TEAM_ROSTER_ENABLED` is off by
  default — format-valid names still work — specifically so populating
  `config/team_roster.json` can never accidentally lock everyone out
  before it's ready. Matching is case-insensitive and whitespace-collapsed,
  and the session stores the *roster's* casing, not whatever the visitor
  typed — otherwise "Asha Verma" and "asha verma" would show up as two
  different people in Sheets/analytics, which key off the name string.
  Read fresh on every login attempt rather than cached, unlike the
  tree-growth signals: a teammate who was just added to the roster should
  be able to sign in immediately, not up to a minute later.
- **`services/mission.py`** holds company goal *targets* (revenue, deadline,
  orders, artisans, products, partnerships) as a dedicated `MISSION_*`
  settings model — configurable via environment, never hardcoded in a
  template, per the product spec. It's deliberately separate from
  `core.config.Settings` because these are business targets an admin will
  eventually edit at runtime (Phase 7's admin dashboard already exists;
  runtime editing is still future work), not app configuration.
  `get_mission_progress()` is the one place revenue-percent, days-left, and
  Indian-currency formatting are computed, so every page that needs mission
  data reads the same numbers. As of Phase 8, *current* values (how much
  revenue there actually is right now) moved out to `services/kpis.py` —
  see below — so there's exactly one place "current revenue" is configured,
  not two that could drift apart.
- **`services/quotes.py`** rotates a small curated quote set deterministically
  by day-of-year — unlike mission goals this isn't a company value an admin
  edits, so it stays in code rather than configuration.
- **The tree visualization (`templates/partials/tree_svg.html`)** is an
  inline SVG, not a static image, specifically so growth rules (Phase 8)
  could target its parts with server-rendered conditionals instead of
  needing a rewrite. It never fakes progress from form submissions — every
  extra leaf, branch, flower, fruit, and bird is driven by
  `services/tree_growth.py` evaluating real KPI/participation thresholds
  from `config/tree_rules.json`, per the product's core rule that the tree
  reflects real company progress only.
- **The reflection form (Phase 4) validates twice, deliberately.** The
  1-10 slider gets live emoji/color/label feedback in `static/js/reflection.js`
  purely for UX — the server never trusts it. `app/schemas/reflection.py`
  (`ReflectionForm`) is the single source of truth for validity (non-blank,
  length-bounded text fields, `rating` clamped 1-10), and
  `app/routers/reflections.py` re-renders the form with per-field errors
  and the user's entered values on failure, the same pattern as login.
- **`services/reflections.py`** logs every submission first — a cheap,
  reliable audit trail that never depends on an external API — then
  attempts a Google Sheets write via `services/google_sheets.py`. Nothing
  in the router or schema changed when Sheets landed in Phase 6; only this
  function's body grew a second step.
- **`services/google_sheets.py` fails soft, on purpose.** `is_sheets_configured()`
  gates everything: if `GOOGLE_SHEETS_ENABLED` is false (the default), the
  spreadsheet ID is blank, or the credentials file is missing, every
  function becomes a no-op that logs a warning instead of raising. A
  reflection a user already saw the success screen for should never be lost
  because Sheets hiccupped or a team hasn't finished setup — the log line
  from `services/reflections.py` is the fallback. Only this file needs to
  change when Phase 8+ moves to Postgres/Supabase; the router and schema
  won't.
- **"Already reflected today" lives in the session**, not a database
  (`last_reflection_date`, set on successful submit). There's no
  first-party persistence layer yet — Sheets is an external store the app
  writes to, not something it queries back from — so this remains the
  honest, minimal way to prevent double-submits and drive the dashboard's
  check-in/streak tiles. It resets naturally the next calendar day or on
  logout.
- **The submission experience (Phase 5) is a real page load, not an AJAX
  flow.** A loading overlay appears the instant the form's `submit` event
  fires (`static/js/reflection.js`) and covers the round-trip to the
  server — it never needs to be hidden manually, since the browser replaces
  the DOM when the success page arrives. That page then runs its own
  entrance animations (tree growing in, leaves popping with a stagger,
  DOM-based confetti) purely via `success.css` / `success.js`. Keeping this
  as a normal form POST instead of converting to `fetch()` meant zero
  changes to Phase 4's validation or routing — only a new template and two
  new static files.
- **`partials/tree_svg.html`** holds just the raw tree markup, shared by the
  dashboard's swaying "seedling" card and the success screen's grow-in
  animation. Each context wraps it in its own container and scopes its own
  CSS to that container, so the same SVG can have two entirely different
  animations without duplicating markup.
- **All Phase 5 animations respect `prefers-reduced-motion`** — confetti
  isn't generated at all, and the tree/loading animations jump straight to
  their end state, consistent with the reduced-motion handling already
  established for the dashboard's background blobs (Phase 3).
- **Admin access (Phase 7) is a single shared password, layered on the
  existing session** — you must already be signed in with your name, and
  `ADMIN_PASSWORD` then unlocks an `is_admin` flag in that same session
  (compared with `secrets.compare_digest` to avoid timing attacks; failed
  attempts are logged). This is not real per-admin auth or RBAC — those are
  explicitly future-ready work — it's the same "simplest thing that's
  actually a step up from no security at all" philosophy as Phase 2.
- **`services/reflection_analytics.py`** is the read path Phase 6 never
  needed (it only wrote to Sheets). It pulls every row back, parses it, and
  computes the admin dashboard's numbers — kept separate from
  `google_sheets.py` so Phase 9 (analytics/charts) and Phase 10 (AI
  insights) can reuse `get_all_reflections()` instead of re-parsing rows
  themselves. Like the write path, it fails soft: no Sheets configured or
  zero rows both return an explicit "no data" result the dashboard renders
  as an empty state, never a crash.
- **"Participation %" and "7-day completion %" are deliberately different
  numbers**, not the same stat shown twice: participation is *today's*
  unique check-ins over `TEAM_SIZE` (a snapshot), completion is the
  trailing 7-day *average* of that same ratio (how consistently, not just
  today). Both exist because there's still no team roster — `TEAM_SIZE` is
  a configured headcount, not a real membership list, so treat these as
  directional, not exact.
- **"Top Blockers / Wins / Priorities" (Phase 7) rank by exact-text
  frequency**, not real theme clustering — that's honest about what
  free-text matching can do without an LLM. Phase 10's "Recurring Issues"
  is a deliberately different, stricter metric on the same data: it counts
  *distinct days* a blocker text appears on, not raw mentions, so a
  blocker mentioned five times in one day (not recurring) is correctly
  told apart from one mentioned once a day for five days (genuinely
  recurring) — something a simple frequency count can't do.
- **`services/kpis.py`** (Phase 8) is the single source of truth for
  current business metrics (revenue, orders, women artisans, products
  listed, website visitors, repeat customers, partnerships, social
  followers) — a `KPI_*` settings model, configurable the same way as
  Mission goals. It feeds both `get_mission_progress()`'s revenue % and
  the tree-growth rules; nothing computes "current revenue" independently
  anywhere else.
- **`services/tree_growth.py` + `config/tree_rules.json`** is the rules
  engine the spec calls for: a fixed, documented vocabulary of *signals*
  (the 8 KPIs, plus today's participation % and mission progress %,
  computed in Python) and an admin-editable JSON file that decides which
  thresholds on those signals unlock a leaf, branch, flower, fruit, or
  bird — see `config/README.md`. The engine only evaluates rules; it never
  hardcodes what they are, so retuning "how many orders grows a fruit"
  is a one-line JSON edit, not a deploy. An invalid or missing rules file
  logs a warning and falls back to zero growth rather than crashing the
  app.
- **The tree-growth result is cached for 60 seconds**, not recomputed on
  every request, because one of its signals (today's participation %)
  comes from `reflection_analytics`, which reads Google Sheets — without
  the cache, every home-dashboard and every reflection-success page view
  would trigger a live Sheets call. A tree that's briefly stale is
  unnoticeable; a Sheets read on every page load is not free. Everywhere
  else in the app (the admin dashboard, the Business Growth page's KPI
  numbers) stays uncached, since those are checked deliberately and rarely,
  not loaded on every page view.
- **The dashboard's tree and the success screen's tree render the exact
  same growth state** — both include the same `partials/tree_svg.html`
  with the same `tree_state` context, just wrapped in different CSS
  (gentle sway vs. a staggered pop-in entrance). One SVG, one source of
  truth for "what the tree currently looks like," two presentations.
- **The Business Growth page (`/growth`) is visible to every signed-in team
  member, not admin-gated** — consistent with the mission card already
  being visible to everyone on the home dashboard. This is a transparency
  tool ("why does the tree look like this"), not an admin control panel;
  the admin dashboard (`/admin`, Phase 7) remains the password-gated one.
- **Analytics (`/admin/analytics`, Phase 9) is admin-gated**, unlike the
  Business Growth page — a deliberate, different call from Phase 8's
  "everyone can see it." The analytics table, search, and CSV export
  expose individual free-text reflection entries (not just aggregate KPI
  numbers), which is more sensitive and closer to the admin dashboard's
  existing "Need Help" / "Top Blockers" lists (Phase 7) than to the
  company-wide mission card. Same `is_admin` session gate as `/admin`.
- **The spec's "Department comparison" became "Member comparison."** There
  is no department/org-chart concept anywhere in this app's data model —
  reflections only ever captured a name, never a team or department — so
  building department comparison would mean inventing data that doesn't
  exist. Comparing by team member instead uses the one real dimension
  the data actually has, is honestly labeled, and gives a real signal
  (who's reflecting, how often, at what rating) without fabricating
  structure.
- **Trend charts (daily/weekly/monthly) are one reusable SVG line-chart
  renderer** (`build_line_segments()` in `reflection_analytics.py`) fed
  three different bucket granularities. The y-axis is a fixed 1-10 (rating's
  real range), not auto-scaled to the data — auto-scaling would visually
  exaggerate small week-to-week differences. Periods with zero reflections
  produce a gap in the line (split into a new polyline segment) rather than
  interpolating across missing data or drawing a fabricated flat line.
- **The trend chart, heatmap, distribution, member table, and CSV export
  all read the same filtered record set**, computed once per request from
  the `start`/`end`/`member`/`q` query params — not five independently
  filtered views. Changing the date range or searching updates every
  section consistently, and "export what I'm looking at" always matches
  what's on screen because the page and the CSV route resolve filters
  through the same `_load_filtered()` helper.
- **The participation heatmap uses a single-hue opacity ramp**
  (`rgba(34, 197, 94, opacity)`, 0.06 floor to 0.90 ceiling) rather than a
  multi-step color-ramp token system — a deliberately simplified but still
  correct "sequential = one hue, light→dark" encoding (per the dataviz
  skill's color formula) proportionate to one small internal heatmap, not
  a multi-chart branded dashboard.
- **`services/ai_insights.py` needs no AI provider to work, on purpose** —
  the spec says "no API keys required," so the executive summary,
  wins/blockers, recurring issues, trends, recommendations, sentiment, and
  momentum score are all computed directly from `reflection_analytics.py`
  primitives with plain Python (string templates and threshold rules), not
  an LLM call. `AI_PROVIDER` (`none` by default) and three `_generate_summary_via_*`
  functions exist as the OpenAI/Claude/Gemini placeholders the spec asks
  for — each is a real, finished function that raises `NotImplementedError`
  with a clear message, caught by `get_ai_insights()` and logged, falling
  back to the built-in summary. That fallback isn't a degraded mode; the
  heuristic engine *is* the deliverable. Wiring in a real provider later
  means implementing one function's body, not restructuring anything that
  calls it.
- **"Recurring Issues" counts distinct days, not raw mentions** — see the
  Phase 7 bullet above for why that's a meaningfully different, stricter
  signal than "top blockers by frequency."
- **The Company Momentum Score (0-100) is a transparent, documented
  formula, not a black-box AI number**: 40% this week's average rating +
  40% this week's participation consistency + 20% mission progress toward
  the revenue target. Rating and consistency are weighted equally and
  higher than mission progress deliberately — they're what actually moved
  *this week*, which is what "momentum" means, while mission progress is a
  slow-moving number that would otherwise flatten the score's ability to
  reflect a genuinely better or worse week. The breakdown is shown on the
  insights page itself, not hidden.
- **AI Insights (`/admin/insights`) is admin-gated**, same as `/admin` and
  `/admin/analytics` — it surfaces the same underlying blocker/help-request
  content at a more synthesized level, so it's exactly as sensitive as the
  analytics page it sits alongside, not as public as `/growth`.
- **The Mission Dashboard (`/mission`, Phase 11) is a new page, not a
  replacement for the home dashboard (`/`).** The spec calls it "the hero
  page" that should "motivate the team every morning," which could read as
  "make this the landing page" — but `/` already does real work (the
  reflection CTA, streak, daily quote) that a rewrite would have to
  preserve anyway, so this shipped as an additional, more prominent page
  linked from the header nav and from the home dashboard's mission card,
  the same "extend, don't rewrite" call already made for `/growth` and
  `/admin/analytics`. Visible to every signed-in team member, not
  admin-gated — same precedent as `/growth`.
- **"Forest Growth" is a new, distinct signal from the tree's KPI-driven
  growth**, not a re-skin of the same number. The tree (`tree_state`)
  grows from business KPI thresholds; the forest
  (`tree_growth.py::_forest_size()`) grows from cumulative team practice —
  one small tree icon per 5 reflections ever submitted, capped at 12. This
  maps directly to the app's founding line, "small improvements every day
  create extraordinary companies": the forest is literally built from the
  accumulation of daily reflections, not from any KPI. Computed inside the
  same cached `TreeGrowthState` as the tree (reusing the `admin_stats` call
  already being made for participation, not a second Sheets read).
- **The "Milestones" list reuses `tree_state.unlocked_descriptions`**
  (already computed by the Phase 8 rules engine for the Business Growth
  page's transparency section) rather than inventing a separate milestones
  data source — the same real, admin-configured thresholds are just
  presented as achievements here instead of as growth-rule explanations.
- **Count-up numbers and the animated progress-bar fill
  (`static/js/mission.js`)** are the "everything should animate
  beautifully" ask for this page specifically — a small, generic
  `[data-countup]` / `[data-progress-fill]` attribute pattern rather than
  bespoke animation code per number, and both jump straight to their final
  value (not skipped) under `prefers-reduced-motion`, consistent with
  every other animation in the app.
- **Dark mode (Phase 12) is an explicit `[data-theme]` attribute, not a
  `prefers-color-scheme` media query alone** — the spec asks for both
  "Dark Mode" and "Light Mode" as user choices, not just an OS-driven
  default. An inline script in `base.html`'s `<head>` (before any CSS
  paints, to avoid a flash of the wrong theme) reads `localStorage`,
  falling back to system preference only on a first visit; the toggle
  button and `static/js/theme.js` just flip the attribute and persist it.
  Every color the app uses was already a CSS custom property from Phase 1
  onward — dark mode is a second value for each token
  (`[data-theme="dark"]` in `base.css`), not a restyle of any component.
  The one real piece of work was hunting down ~19 places across
  `auth.css`/`reflection.css`/`analytics.css`/`admin.css`/`dashboard.css`/
  `insights.css` where a border or input background had been hardcoded as
  `rgba(24, 24, 40, ...)` instead of using a token — those became three new
  shared variables (`--color-border`, `--color-border-strong`,
  `--color-input-bg`) so dark mode didn't need a second pass later.
- **Keyboard shortcuts (`static/js/shortcuts.js`)** — `d`/`r`/`m`/`g`/`a`
  navigate to the dashboard/reflection/mission/growth/admin pages, `?`
  opens a help overlay listing them, `Esc` closes it. Ignored while
  focus is in a form field (checked via `document.activeElement`) so
  typing a reflection never accidentally navigates away. Only loaded for
  signed-in users — `base.html` gates the `<script>` tag itself rather
  than have the script check session state client-side.
- **Accessibility additions**: a skip-to-content link (visually hidden
  until focused, jumps past the header nav — a standard, cheap win for
  keyboard users), a global `:focus-visible` outline (glass/gradient
  backgrounds can make default browser focus rings hard to see), and
  `main` given an explicit `id="main-content"` as the skip target.
- **The header nav wraps on narrow viewports** (`flex-wrap` + a
  `flex-direction: column` breakpoint) rather than a hamburger-menu
  component — with `Mission`/`Growth`/`Admin`/username/logout/theme-toggle
  all in one row, a full mobile-menu widget would be more machinery than
  five text links actually need; wrapping keeps every link visible and
  tappable without new JS.
- **Hover micro-interactions** (a lift + deeper shadow on `.stat-card`/
  `.tree-card`, a shadow-only hover on `.admin__card` since those often
  contain scrollable tables where a translate would feel odd, and a row
  highlight on the analytics tables) were added where earlier phases had
  static cards — everything else (buttons, links, form fields) already had
  a hover/focus state from the phase that built it.
- **"Loading screens" (Phase 12's item) is Phase 5's reflection-submission
  overlay, not a new one.** This is a server-rendered app with fast SSR
  page loads throughout; the one place a wait was ever noticeable — saving
  a reflection — already got a real loading state in Phase 5. Inventing a
  generic page-transition spinner for otherwise-instant navigations would
  be motion for its own sake, not polish.
- **Performance**: static assets (`/static/...`) get a `Cache-Control:
  public, max-age=86400` header in production, via a small `StaticFiles`
  subclass in `main.py` — skipped when `DEBUG=True` specifically so local
  CSS/JS edits during development are never masked by a stale cached
  asset in the browser.
- **Server-rendered Jinja2 + vanilla JS**, not a JS framework — this is an
  internal daily-use tool, not a public product; SSR keeps it fast, simple
  to deploy, and easy for one team to maintain.
- **`static/css/base.css`** defines design tokens (colors, radii, shadows,
  spacing) as CSS custom properties up front. Phase 12's dark mode only
  needs to add a `[data-theme="dark"]` override block, not restyle every
  component.

## Setup

Requires Python 3.11+.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate    # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env          # macOS/Linux
# Edit .env if you need non-default values.

# 4. Run the development server
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` — you should see the Kalastree Pulse homepage.

## Environment variables

All variables are documented and defaulted in `app/core/config.py`. See
`.env.example` for the current list (app identity fields like `APP_NAME`
have sensible built-in defaults and don't need to be set).

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | `development` \| `staging` \| `production` |
| `DEBUG` | Enables FastAPI debug mode |
| `HOST` / `PORT` | Bind address for the dev server |
| `SECRET_KEY` | Session/cookie signing key — must be overridden in production |
| `SESSION_COOKIE_NAME` | Cookie name used once auth lands (Phase 2) |
| `TEAM_ROSTER_ENABLED` | Off by default. Once `True`, only names listed in `config/team_roster.json` can sign in — see `config/README.md` |
| `LOG_LEVEL` | Root logger level |
| `MISSION_*` | Company goal *targets* (revenue, deadline, orders, artisans, products, partnerships) shown on the home dashboard's mission card — see `.env.example` for the full list and `app/services/mission.py` |
| `KPI_*` | Current business metrics (revenue, orders, women artisans, products listed, website visitors, repeat customers, partnerships, social followers) — drives mission progress %, the Business Growth page, and tree-growth rules. See `app/services/kpis.py` |
| `AI_PROVIDER` | `none` (default) \| `openai` \| `claude` \| `gemini` — a value other than `none` without a real provider implementation falls back to the built-in insights automatically |
| `AI_OPENAI_API_KEY` / `AI_CLAUDE_API_KEY` / `AI_GEMINI_API_KEY` | Placeholders for a future real integration — not read by anything yet |
| `GOOGLE_SHEETS_ENABLED` | Off (`False`) by default — the app fully works without Sheets set up, reflections just stay log-only |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Path to the service account JSON key, relative to the project root unless absolute. Default `credentials/service-account.json` |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | The long ID in your Sheet's URL (`.../d/<this-part>/edit`) |
| `GOOGLE_SHEETS_WORKSHEET_NAME` | Tab name to write to; created automatically (with a header row) if it doesn't exist. Default `Reflections` |
| `ADMIN_PASSWORD` | Shared password that unlocks `/admin` for anyone already signed in — change this from the default |
| `TEAM_SIZE` | Configured headcount used to compute participation/completion % on the admin dashboard (no real roster exists yet) |

## Setting up Google Sheets

Reflections work perfectly well without this — they're always logged
locally. This section is for turning on the durable Sheets copy.

**1. Create a Google Cloud project** (skip if you already have one) at
[console.cloud.google.com](https://console.cloud.google.com). Any project
works; this doesn't need to be dedicated to Kalastree Pulse.

**2. Enable the Google Sheets API** for that project: APIs & Services →
Library → search "Google Sheets API" → Enable. (The Drive API is *not*
needed — see "Permissions" below.)

**3. Create a service account**: APIs & Services → Credentials → Create
Credentials → Service Account. Give it any name (e.g.
`kalastree-pulse-sheets`); it doesn't need any project-level IAM role.

**4. Create a JSON key for it**: open the service account → Keys → Add Key
→ Create new key → JSON. This downloads a file — save it as
`credentials/service-account.json` in this repo (that path is
`.gitignore`d; never commit it).

**5. Create your Google Sheet** and copy its ID out of the URL:
`https://docs.google.com/spreadsheets/d/`**`<SPREADSHEET_ID>`**`/edit`.

**6. Share the Sheet with the service account.** Open the downloaded JSON
key and copy the `client_email` value (looks like
`kalastree-pulse-sheets@your-project.iam.gserviceaccount.com`). In the
Sheet, click Share and add that email with **Editor** access — this is the
only permission the service account gets; it can't touch anything else in
your Google account. This step is the one people most often forget, and
it's the most common cause of "connected but can't write" errors.

**7. Configure `.env`**:

```
GOOGLE_SHEETS_ENABLED=True
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials/service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=<the ID from step 5>
GOOGLE_SHEETS_WORKSHEET_NAME=Reflections
```

### Testing

Run the standalone connectivity check before trusting it from the app —
it authenticates, opens the spreadsheet, and confirms the worksheet is
reachable, without touching the reflection flow:

```bash
python scripts/check_google_sheets.py
```

A successful run prints the worksheet title and row count. If it fails,
the log line above the error tells you which of the three settings (or the
sharing step) is wrong. Once that passes, submit a real reflection through
the app and confirm the row appears in the Sheet — the header row
(`Timestamp, Name, Rating, Reason, Biggest Win, Biggest Blocker, Tomorrow
Priority, Need Help, Suggestions`) is created automatically on the first
write if the tab is empty.

### Permissions

The service account is granted **only** `spreadsheets` API scope (not
`drive`), and only has access to the one Sheet you explicitly shared with
it — not your whole Drive, and not any other Sheet. There is no
project-level IAM role attached to it. If a write ever fails with a
permission error, the fix is almost always re-checking step 6 (the Sheet
share), not the Cloud project's IAM settings.

## Logs

Logs are written to `logs/kalastree_pulse.log`, rotating at 5 MB with 5
backups kept, plus mirrored to the console. `uvicorn.access` is set to
`WARNING` to keep routine request logs out of the way.

## Deploying to Google Cloud Run

The `Dockerfile` in the repo root runs the app exactly as it runs
locally (`uvicorn app.main:app`) — no code changes needed. Cloud Run's
free tier is generous for a low-traffic internal tool, and mounting the
Google service account key via Secret Manager fits this app's existing
`GOOGLE_SHEETS_CREDENTIALS_FILE` setting with zero code changes (it
already resolves absolute paths as-is).

**Prerequisites**: the [gcloud CLI](https://cloud.google.com/sdk/docs/install),
authenticated (`gcloud auth login`) with a project selected
(`gcloud config set project YOUR_PROJECT_ID`) that has billing enabled —
Cloud Run's free tier still requires a billing account on file, even
though typical usage here won't be charged.

**1. Enable the APIs you'll need** (one-time per project):

```bash
gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
```

**2. Store the Google service account key in Secret Manager** — never
bake it into the image or pass it as a plain env var:

```bash
gcloud secrets create kalastree-sheets-credentials --data-file=credentials/service-account.json
```

**3. Create `.env.yaml`** in the project root (add it to `.gitignore` —
it holds real secrets) mirroring your local `.env`, with `ENVIRONMENT` /
`DEBUG` switched for production and `GOOGLE_SHEETS_CREDENTIALS_FILE`
pointed at where the secret gets mounted in step 4:

```yaml
ENVIRONMENT: "production"
DEBUG: "False"
SECRET_KEY: "<generate a real one — see below>"
SESSION_COOKIE_NAME: "kalastree_session"
ADMIN_PASSWORD: "<your real admin password>"
LOG_LEVEL: "INFO"
TEAM_ROSTER_ENABLED: "True"
GOOGLE_SHEETS_ENABLED: "True"
GOOGLE_SHEETS_CREDENTIALS_FILE: "/secrets/service-account.json"
GOOGLE_SHEETS_SPREADSHEET_ID: "<your spreadsheet ID>"
GOOGLE_SHEETS_WORKSHEET_NAME: "Reflections"
```

Generate a real `SECRET_KEY` with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

If you've customized any `MISSION_*`, `KPI_*`, or `AI_*` values locally,
add those here too — Cloud Run only knows about env vars you explicitly
set; it never reads your local `.env` file.

**4. Deploy**, building straight from source (Cloud Build uses the
`Dockerfile` automatically) and mounting the secret from step 2 as a file
at the path referenced in step 3:

```bash
gcloud run deploy kalastree-pulse \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --set-secrets /secrets/service-account.json=kalastree-sheets-credentials:latest
```

The first deploy takes a few minutes (builds the image via Cloud Build,
then deploys) and prints a `*.run.app` URL when done — that's your app,
already on HTTPS.

**To redeploy** after code changes, just re-run the same `gcloud run
deploy` command — it rebuilds from your current source and rolls out a
new revision with zero downtime.

### Notes specific to this app

- **Logs**: the existing rotating file handler still works inside the
  container (Cloud Run's filesystem is writable, just ephemeral), but
  won't persist across restarts or aggregate across instances. Console
  output (already dual-logged) is captured automatically into Cloud
  Logging — that's the one to actually rely on in production.
- **The 60-second tree-growth cache** (`tree_growth.py`) is per-instance
  and in-memory. If Cloud Run scales to multiple instances under load,
  each keeps its own cache — mildly more Sheets calls than a single
  instance would make, never a correctness problem.
- **For stronger secret hygiene**, `SECRET_KEY` and `ADMIN_PASSWORD` can
  also live in Secret Manager instead of `.env.yaml`, mounted the same
  way as the credentials file (`--set-secrets` accepts multiple
  `ENV_VAR=secret:version` pairs) — worth doing before sharing this
  beyond a trusted local team.
- **`--allow-unauthenticated`** makes the URL publicly reachable, gated by
  this app's own login same as anywhere else. Omit it for Cloud Run's own
  IAM-based access control on top.

## Common issues

- **`ModuleNotFoundError: No module named 'app'`** — run `uvicorn` from the
  project root (`kalastree-pulse/`), not from inside `app/`.
- **Static files 404** — confirm you're hitting `/static/...` (the app
  mounts `app/static` there) and that `.env`'s paths haven't been
  overridden; `STATIC_DIR`/`TEMPLATES_DIR` are derived, not meant to be set
  via environment.
- **A form field that's submitted blank raises a raw 422 instead of your
  validator's error** — FastAPI treats an empty-string `Form()` value as
  "not provided," not as an empty value, so a required `Annotated[str,
  Form()]` parameter fails before your handler even runs. Give text-form
  parameters a `= ""` default (see `app/routers/reflections.py`) so blank
  submissions reach your own validation instead of FastAPI's generic error.
- **Reflections submit fine but never show up in the Sheet** — run
  `python scripts/check_google_sheets.py` first; it isolates whether the
  problem is configuration (`GOOGLE_SHEETS_*` in `.env`) or sharing (the
  service account's `client_email` needs Editor access on the Sheet
  itself — see "Setting up Google Sheets" above). The app never raises on
  a Sheets failure by design, so check the logs for a `Failed to
  append reflection row` or `not persisted to Google Sheets` line rather
  than expecting an error in the browser.
- **`/admin` shows the empty state even though reflections have been
  submitted** — the admin dashboard reads from Google Sheets, not the
  local log; if Sheets isn't configured (see above), there's genuinely
  nothing for it to read yet, by design.
- **The tree doesn't visibly grow right after changing a `KPI_*` value or
  editing `config/tree_rules.json`** — restart the dev server (env vars are
  read once at startup) and give it up to 60 seconds either way, since
  `tree_growth.py` caches the computed state for a minute to avoid hitting
  Google Sheets on every page load. A rule that never seems to fire is
  usually a typo in the `kpi` name — check the logs for a `Skipping invalid
  tree growth rule` warning, and cross-reference `config/README.md`'s list
  of valid signal names.
- **Nobody can sign in anymore** — check `TEAM_ROSTER_ENABLED` in `.env`.
  If it's `True`, sign-in is restricted to names in
  `config/team_roster.json`; an empty, missing, or invalid-JSON roster
  file means nobody matches. Fix it directly on disk (no login required to
  edit a file) and it takes effect on the next login attempt, no restart
  needed. Logs show exactly which of those three problems it is.

## Future-ready, not yet implemented

Architecture leaves room for, but does not yet include: Supabase/PostgreSQL,
JWT-based auth with role-based access, Slack/WhatsApp/Telegram/email
notifications, push notifications, a mobile app, and AI agents. These land
only when their respective phase is reached.
