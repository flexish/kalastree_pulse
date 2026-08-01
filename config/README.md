# config/

## tree_rules.json

Defines what makes the tree on the home dashboard grow. This is the file
the product spec means by "do not hardcode these rules" — edit it, no code
change or deploy needed; `app/services/tree_growth.py` re-reads it on
every request (through a short-lived cache, see below).

**Shape**: five arrays, one per tree element — `leaves`, `branches`,
`flowers`, `fruits`, `birds`. Each entry is:

```json
{ "kpi": "orders", "threshold": 25, "description": "25 orders completed" }
```

An entry unlocks (adds one of that element) once the named signal's
current value is `>=` its threshold. `description` is shown on the
Business Growth page ("why does the tree look like this") — keep it short
and human-readable.

**Available `kpi` signal names** (fixed set — this is what the app
actually measures, not a free-form field name):

| Signal | Source |
|---|---|
| `revenue` | `KPI_REVENUE` |
| `orders` | `KPI_ORDERS` |
| `women_artisans` | `KPI_WOMEN_ARTISANS` |
| `products_listed` | `KPI_PRODUCTS_LISTED` |
| `website_visitors` | `KPI_WEBSITE_VISITORS` |
| `repeat_customers` | `KPI_REPEAT_CUSTOMERS` |
| `partnerships` | `KPI_PARTNERSHIPS` |
| `social_followers` | `KPI_SOCIAL_FOLLOWERS` |
| `participation_today_pct` | Today's reflection participation %, from the admin dashboard's numbers |
| `mission_progress_pct` | Revenue progress toward the mission target (`MISSION_REVENUE_TARGET`) |

The KPI values themselves live in `.env` — see `.env.example`'s `KPI_*`
section — not in this file. This file only decides which *thresholds*
matter.

**Rendering caps**: the tree SVG only has room for a handful of each
element (currently up to 3 extra leaves, 2 branches, 4 flowers, 4 fruits,
2 birds — see `templates/partials/tree_svg.html`). Adding more rules than
that per element is fine — extra unlocked milestones still count toward
the Business Growth page's totals and the tree's overall "stage," they
just won't each get a unique visual slot.

**Invalid entries** (unknown `kpi` name, missing `threshold`) are skipped
with a warning in the logs rather than crashing the app — check there
first if a rule you added doesn't seem to be taking effect.

## team_roster.json

Restricts sign-in to a specific list of names. **Off by default** —
`TEAM_ROSTER_ENABLED=False` in `.env` means any correctly-formatted name
can still sign in, same as before this existed. This is deliberate: it
means populating this file can never accidentally lock everyone out
before it's ready.

**Shape**: a flat JSON array of full names, exactly as you want them to
appear everywhere the app shows a name (Sheets rows, admin dashboard,
analytics):

```json
["Asha Verma", "Rohan Mehta", "Priya Nair"]
```

**Matching**: case-insensitive and whitespace-collapsed — someone typing
`asha  verma` or `ASHA VERMA` still matches `"Asha Verma"`. Whoever signs
in gets recorded under the roster's exact spelling/casing, not however
they typed it, so the same person is never split into two different
"people" in Sheets/analytics because of casing.

**To turn it on**:

1. Fill in this file with your team's real names (replace the empty `[]`).
2. Set `TEAM_ROSTER_ENABLED=True` in `.env`.
3. Restart the server (env var changes need a restart; edits to the
   roster file itself after that don't — it's re-read on every login
   attempt, not cached).

**If this file is missing, empty, or invalid JSON while enabled**, nobody
can sign in via the name form — this is intentional (fail closed, not
fail open, once you've explicitly opted in) but worth testing with your
own name first before rolling it out. The fix is always available at the
filesystem level (edit the JSON file directly), even if the web UI itself
is inaccessible to everyone. A missing/invalid file logs a specific
warning explaining which problem it is.
