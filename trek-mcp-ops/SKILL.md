---
name: trek-mcp-ops
description: "Run and operate the self-hosted TREK travel planner (Docker + built-in MCP server, 135 tools) on this machine. Use this whenever a travel-planning task needs a real itinerary stored in TREK: starting Docker and the auth-proxy, creating or editing trips, days, places, timelines, budgets, packing lists and reservations, and shutting everything down afterwards to free RAM and CPU. Also covers the TREK field-naming traps where a mistyped key is silently ignored."
agent_created: true
---

# TREK MCP Operations

TREK is a self-hosted travel planner running in Docker on this machine. It exposes an
MCP server with **135 tools** (trips, days, places, itinerary timing, budgets, packing,
reservations, transit, maps). This skill is the complete runbook: **start it, drive it,
shut it down.**

**Skill folder:** `C:\Users\qilin\.workbuddy\skills\trek-mcp-ops`
Run every command from that folder. The two `.cmd` launchers find Node themselves, so
you never need a Node path and `node` does not have to be on PATH.

---

## Quick start (3 commands)

```
cd C:\Users\qilin\.workbuddy\skills\trek-mcp-ops
trek.cmd start                                  # brings up Docker + TREK + proxy, then self-tests
trek-call.cmd --list trip                       # see what you can do
trek.cmd stop                                   # when finished — frees all resources
```

`trek.cmd start` is **idempotent and safe to re-run**. When it finishes it prints
`OK — 135 MCP tools reachable` (to the log) only when the whole chain really works,
so if it succeeds you can trust the system is up.

> **No black window.** `trek.cmd start` runs **hidden by default** — the 26 s–2 min
> actual work (Docker boot, compose, proxy, self-test) runs windowless. Only a *brief*
> console window flashes to print "started in background, check the log", then closes.
> Progress is written to `trek-start.log` / `trek-start.err` next to `trek.cmd`. Check
> readiness any time with `trek.cmd status`. If you *want* the live progress window,
> use `trek.cmd start --show`.

---

## 1. START

```
trek.cmd doctor     # optional: verify every path/dependency, changes nothing
trek.cmd status     # is it already running?
trek.cmd start      # hidden, no window — then poll trek.cmd status
trek.cmd start --show   # same, but in a visible window (live progress)
```

`start` performs: launch Docker Desktop headlessly if the daemon is down (waits up to
4 min on a cold boot) → `docker compose up -d` → wait for `/api/health` → start the
auth-proxy supervisor (detached, survives a WorkBuddy restart) → **run a real MCP
handshake as a self-test**. Any failure stops with an actionable message.

If something is wrong, `trek.cmd doctor` prints every resolved path plus a concrete fix
for each problem. Start there before debugging anything by hand.

---

## 2. USE

### Calling tools

```
trek-call.cmd --list                     # all 135 tools
trek-call.cmd --list budget              # filter by keyword
trek-call.cmd --schema create_and_assign_place   # exact accepted arguments
trek-call.cmd create_trip @args.json     # call a tool
```

**Always pass arguments through an `@file.json`.** Write the JSON to a file first, then
reference it with `@`. Inline JSON gets mangled by cmd.exe quoting and is unusable for
Chinese text or long descriptions.

```
:: args.json
{ "title": "上海周末一日游", "currency": "CNY", "description": "..." }

trek-call.cmd create_trip @C:\Users\qilin\AppData\Local\Temp\args.json
```

This bridge talks to the local proxy directly, so it works **in any conversation with no
WorkBuddy restart**. Native `mcp__trek__*` functions only appear if the proxy was
already listening when WorkBuddy started — do not count on them; `trek-call.cmd` always works.

### The one trap that matters

**TREK silently ignores unknown argument keys and still returns success.** A typo like
`durationMinutes` (correct: `duration_minutes`) looks like it worked while nothing changed.
`trek-call.cmd` guards against this: it validates your arguments against the tool's own
schema and aborts with a "did you mean" hint before sending anything. Do not use `--force`
to get around it — fix the key name instead.

Naming is genuinely inconsistent, so **check `--schema` rather than guessing**:
- IDs are camelCase: `tripId`, `dayId`, `placeId`, `assignmentId`, `itemId`
- Data fields are snake_case: `start_date`, `end_date`, `duration_minutes`, `place_time`,
  `end_time`, `total_price`, `category_id`

### Tool quirks worth knowing

- **Pass `start_date` + `end_date` to `create_trip`.** TREK then auto-generates exactly
  the right number of days, already dated (a 20–22 Nov trip yields 3 days dated
  20/21/22). Omit the dates and you get 7 undated placeholder days instead — and
  `update_day` **cannot** add a date afterwards, so you would have to delete and rebuild.
  Getting this right in the first call saves the whole mess.
- **Never invent a `dayId`.** Read the real ids from the `create_trip` response or
  `get_trip_summary`; a guessed id is what produces `Day not found`.
- `create_day` only matters when you need to append an extra day later (it does accept
  `date` and `notes`). `update_day` accepts **only** `title`. Day notes go through
  `create_day_note` / `update_day_note`.
- `update_assignment_time {tripId, assignmentId, place_time, end_time}` builds the
  timeline. Get `assignmentId` from the `create_and_assign_place` response.
- `create_budget_item` needs `tripId`, `name`, `total_price`. Omit `member_ids` to split
  across everyone. There is no `get_budget` — read the budget from `get_trip_summary`.
- **Verify writes by reading back** with `get_trip_summary {tripId}` — one call returns
  metadata, days, assignments, notes and budget.
- **Coordinates live on the `place` object, not the `assignment`.** `get_trip_summary`
  does not echo `lat`/`lng` onto assignments, so verify geocoding at the place level or
  you will get a false "0 places have coordinates".
- **No map pins or route = places have no `lat`/`lng`.** TREK draws the map purely from
  place coordinates. Always geocode after creating places, or the map stays blank.
- **`create_packing_item` has no dedupe.** Never blind-recreate a list; `get_trip_summary`
  first. If you do end up with duplicates, remove them with `delete_packing_item {tripId, itemId}`.
- `d.packing` is an object `{items, total, checked}` — not an array. Same for `d.budget`
  (`{items, ...}`). Reading `.length` off them silently yields `undefined`.
- `update_reservation` requires only `tripId` + `reservationId`; `status` is
  `pending|confirmed|cancelled`. Hotel reservations additionally need
  `place_id` + `start_day_id` + `end_day_id` **all three** at creation time.

### Geocoding places (do this or the map is empty)

`search_place` works (OpenStreetMap, no Google key) but is fuzzy — `"Akihabara Tokyo"`
once returned **Honolulu**. Two rules:

1. **Query in Japanese/local script with the prefecture**, e.g. `城ヶ崎海岸 伊東市`,
   not the romanised name. Then sanity-check the returned lat/lng is in the right country.
2. **Query the building or POI name, not the street number.** Japanese *banchi*
   addresses like `外神田1-18-18` return nothing; the building name
   (`Bito Akiba Plaza`) hits exactly. Hotels usually resolve from their full name
   (`亀の井ホテル伊豆高原` → hotel POI).

When TREK is flaky, **geocode without it** by calling Nominatim directly — this has no
dependency on the container being alive:

```bash
curl -s -A "your-app/1.0" --get "https://nominatim.openstreetmap.org/search" \
  --data-urlencode "q=亀の井ホテル伊豆高原" --data-urlencode "format=json" --data-urlencode "limit=2"
```

Then write the result back with `update_place {tripId, placeId, lat, lng, address}`.
Cross-check plausibility: two places that should be a 10-minute walk apart must land
~300–800 m apart.

### Recommended build order

1. `create_trip` **with `start_date`, `end_date`, `currency`, `description`**
2. `get_trip_summary` → collect the generated `dayId`s
3. `create_and_assign_place` per place (`tripId` + the real `dayId`) → note each `placeId` and `assignmentId`
4. `update_place` → `duration_minutes`, `lat`/`lng`, `address`, `description`
5. `update_assignment_time` → `place_time` / `end_time` for the timeline
6. `create_budget_item` per cost
7. `get_trip_summary` again to verify, then show the user http://localhost:3000

A fully worked example and the 135 tools grouped by domain are in
`references/toolmap.md`. Read it when you need a tool you have not used before.

The web UI is at **http://localhost:3000** — offer it to the user to view the result on a map.

---

## 3. CLOSE — always do this

```
trek.cmd stop
```

Stops the proxy supervisor → `docker compose down` (trip data is preserved on bind
mounts) → **quits Docker Desktop and its backend helpers**, then verifies and prints the
final state.

Docker Desktop keeps a WSL2 VM warm and eats RAM/CPU even when idle, so **run `stop` as
soon as travel planning is finished.** Skip the Docker quit only if the user has other
containers or WSL distros running — in that case run `docker compose down` alone.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Anything unexpected | `trek.cmd doctor` — resolves and reports every path, dependency and runtime state |
| `Cannot reach the TREK MCP proxy` | TREK is down: `trek.cmd start` |
| `Day not found` | Create the day first with `create_day` |
| Tool call "succeeds" but nothing changed | Wrong key name — `trek-call.cmd --schema <tool>` and re-check camelCase vs snake_case |
| `Argument check failed` | Intended. Read the "did you mean" line and fix the key |
| `mcp__trek__*` functions missing | Normal. Use `trek-call.cmd`; it needs no restart |
| Docker will not start | Open Docker Desktop manually once, then `trek.cmd start` |
| Proxy keeps dying | Read `proxy.log` in the proxy folder shown by `trek.cmd doctor` |
| A node **black console window keeps reappearing** after you close it | That is the auth-proxy's console. The supervisor self-heals and respawns it 2s after any exit, so closing the window just loops. **Never close it by hand** — run `trek.cmd stop` to shut the whole stack down cleanly. (The proxy is launched windowless via `windowsHide`; if a window ever shows, re-run `trek.cmd stop` then `trek.cmd start`.) |
| Tool calls **hang forever**, write 0-byte output files and print nothing to stderr; `curl http://127.0.0.1:3001/mcp` never returns | Stale upstream MCP session — the proxy is alive but wedged. Killing the proxy child alone does **not** help (the supervisor respawns the same bad session). Only a full `trek.cmd stop` then `trek.cmd start` rebuilds it. |
| `trek.cmd stop` prints `cannot stop container: ... did not receive an exit event` | Harmless as long as the next line shows Docker Desktop quit. Continue to `start`. |
| `trek.cmd start` produces no output for minutes | The script can block on its final verification long after the stack is actually up. **Do not wait on it** — check independently with `docker ps` (container `trek` should be `healthy`) and `netstat -ano \| grep -E ":(3000\|3001)"`. If both are good, just start calling tools. |

### Shell environment gotchas (Windows / Git Bash)

- **`sleep` does not exist** (`sleep: command not found`). Do not put rate-limit sleeps in
  loops — either drop them or space calls out across separate commands.
- **`rm` needs absolute paths.** The safe-delete wrapper rejects relative ones
  (`relative path rejected (must be absolute)`), so `rm -f _tmp.json` silently fails.
  Use `rm -f "C:/full/path/_tmp.json"`.
- **Shell functions run in the default cwd**, not the directory you `cd`'d into earlier in
  the pipeline — temp files land in the workspace root. Write scratch files with explicit
  absolute paths, and clean them up the same way.
- Prefer a small temp `.mjs` file over a complex inline `node -e "..."`; nested quotes in
  `node -e` are a reliable source of `SyntaxError: Unexpected token ')'`.

## Setup / portability notes

Paths are resolved at runtime — no Node version, Docker path or deploy folder is
hardcoded. Override any of them with `TREK_DEPLOY_DIR`, `TREK_PROXY_CONFIG`,
`TREK_DOCKER_CLI`, `TREK_DOCKER_DESKTOP`, or with
`C:\Users\qilin\.workbuddy\trek-mcp-ops.json`.

OAuth credentials live **outside** this skill in `proxy-config.json` (inside the TREK
deploy folder) and are deliberately never bundled here. On a fresh machine copy
`scripts/proxy/proxy-config.example.json` to `~/.workbuddy/trek-proxy-config.json` and
fill in a Machine client id/secret from TREK → Settings → Integrations.
