# TREK MCP Tool Map (135 tools) + Field Reference

Full inventory of the TREK MCP server tools, grouped by domain, plus the exact input-field conventions discovered empirically (TREK is inconsistent about snake/camel casing — follow this exactly to avoid validation errors).

> **Never guess a field name.** Run `trek-call.cmd --schema <tool>` — it prints TREK's own
> JSON Schema and settles every casing question in one call. `trek-call.cmd` also blocks
> calls containing unknown keys before they are sent, because TREK accepts and silently
> discards them while still answering "success".

## ⚠️ Field-naming conventions (critical)
- **Dates are snake_case**: `update_trip` → `start_date`, `end_date` (pattern `YYYY-MM-DD`). `startDate`/`endDate` are silently ignored.
- **Durations are snake_case**: `update_place` → `duration_minutes` (NOT `durationMinutes`).
- **Times are snake_case**: `place_time`, `end_time` (format `"09:30"`). Set on a place via `update_place` OR on an assignment via `update_assignment_time`.
- **IDs are camelCase**: `tripId`, `dayId`, `placeId`, `assignmentId`, `itemId`, `categoryId`, `memberIds`, `userIds`.
- **`create_trip` auto-generates the days.** With `start_date` + `end_date` it creates exactly one day per calendar date, already dated. Without them it creates 7 placeholder days with `date: null`, and there is no way to date them afterwards (`update_day` only sets a title) — you would have to `delete_day` and `create_day` each one. **Always pass the dates to `create_trip`.**
- `create_and_assign_place` needs `tripId` + `dayId` (numbers). **Read the real `dayId` from the `create_trip` response or `get_trip_summary`** — a guessed id is what causes `Day not found`.
- `create_day` accepts `tripId`, `date` (`YYYY-MM-DD`, optional) and `notes`. Use it only to append a day beyond the generated range.
- `update_day` accepts ONLY `tripId`, `dayId`, `title` (may be null). It cannot change a date; use `create_day_note` / `update_day_note` for notes.
- `create_budget_item` requires `tripId`, `name`, `total_price`; optional `category`, `currency`, `member_ids`, `payers`, `expense_date`, `note`. **Do not guess `payers`** — omit to split across all members.
- `delete_budget_item` takes `tripId` + `itemId` and returns `{"success": true}`.
- There is **no** `get_budget` / `list_budget_items`. Read the budget out of `get_trip_summary`.

## Verify after writing
`get_trip_summary {tripId}` returns metadata, members, days, assignments, day notes and
budget in a single call — use it as the confirmation step after any batch of edits.

## Recommended creation order
`create_trip` (**with `start_date` + `end_date`**) → `get_trip_summary` to collect the generated `dayId`s → `create_and_assign_place` (×N) → `update_place` (×N) → `update_assignment_time` (×N) → `create_budget_item` (×N) → `get_trip_summary` to verify

## Tool inventory

### Trip (core)
`create_trip` `update_trip` `delete_trip` `list_trips` `get_trip_summary` `copy_trip` `export_trip_ics`
`list_trip_members` `add_trip_member` `remove_trip_member`
`get_share_link` `create_share_link` `delete_share_link`

### Place
`create_place` `create_and_assign_place` `update_place` `delete_place` `list_places` `list_categories` `search_place` `import_places_from_url` `bulk_delete_places` `bulk_update_places`
`assign_place_to_day` `unassign_place` `reorder_day_assignments` `move_assignment` `set_assignment_participants` `get_assignment_participants` `update_assignment_time`

### Day / Notes
`create_day` `update_day` `delete_day` `create_day_note` `update_day_note` `delete_day_note`

### Budget / Settlement
`create_budget_item` `update_budget_item` `delete_budget_item` `create_budget_item_with_members` `set_budget_item_members` `toggle_budget_member_paid`
`get_settlement_summary` `list_settlements` `create_settlement` `update_settlement` `delete_settlement`

### Packing
`create_packing_item` `update_packing_item` `delete_packing_item` `toggle_packing_item` `reorder_packing_items` `create_packing_bag` `update_packing_bag` `delete_packing_bag` `set_bag_members` `list_packing_bags` `apply_packing_template` `save_packing_template` `delete_packing_template` `list_packing_templates` `bulk_import_packing` `set_packing_category_assignees` `get_packing_category_assignees`

### Todo
`create_todo` `update_todo` `delete_todo` `toggle_todo` `reorder_todos` `list_todos` `set_todo_category_assignees` `get_todo_category_assignees`

### Transport / Reservation / Accommodation
`create_transport` `update_transport` `delete_transport`
`create_reservation` `update_reservation` `delete_reservation` `reorder_reservations`
`create_accommodation` `update_accommodation` `delete_accommodation` `create_place_accommodation` `link_hotel_accommodation`

### Maps / Geo / Weather
`search_place` `reverse_geocode` `resolve_maps_url` `get_weather` `get_detailed_weather`
`get_atlas_stats` `get_country_atlas_places` `list_visited_regions` `mark_country_visited` `unmark_country_visited` `mark_region_visited` `unmark_region_visited`
`search_airports` `get_airport` `search_transit_routes` `search_transit_stops` `create_transit_journey`

### Vacay / Holiday
`add_vacay_year` `list_vacay_years` `delete_vacay_year` `get_vacay_plan` `update_vacay_plan` `dissolve_vacay_plan` `set_vacay_color` `get_vacay_entries` `toggle_vacay_entry` `get_vacay_stats` `update_vacay_stats` `send_vacay_invite` `accept_vacay_invite` `decline_vacay_invite` `cancel_vacay_invite` `get_available_vacay_users`
`add_holiday_calendar` `update_holiday_calendar` `delete_holiday_calendar` `list_holidays` `list_holiday_countries` `toggle_company_holiday`

### Tags / Bucket list
`create_tag` `update_tag` `delete_tag` `list_tags`
`create_bucket_list_item` `update_bucket_list_item` `delete_bucket_list_item`

### Notification
`list_notifications` `get_unread_notification_count` `mark_notification_read` `mark_notification_unread` `mark_all_notifications_read`

## Worked example (verified end-to-end)

A complete one-day trip: dates, two places with descriptions and coordinates, per-place
durations, a timeline and a budget. Write each payload to a `.json` file and pass it with
`@` — this is the only quoting-safe way to send Chinese text through cmd.exe.

```
:: 1) trip — ALWAYS include the dates, TREK then builds correctly dated days for you
trek-call.cmd create_trip @trip.json
   trip.json  { "title": "上海周末一日游", "currency": "CNY",
                "start_date": "2026-08-02", "end_date": "2026-08-02",
                "description": "上海经典地标快闪一日游" }
   -> tripId 2, and one generated day already dated 2026-08-02

:: 2) read back the REAL dayId (never guess it)
trek-call.cmd get_trip_summary @s.json
   s.json     { "tripId": 2 }
   -> dayId 15

:: 3) places, assigned to the day in one call
trek-call.cmd create_and_assign_place @p1.json
   p1.json    { "tripId": 2, "dayId": 15, "name": "外滩" }
   -> placeId 2, assignmentId 2
trek-call.cmd create_and_assign_place @p2.json
   p2.json    { "tripId": 2, "dayId": 15, "name": "豫园" }
   -> placeId 3, assignmentId 3

:: 4) (only if something changed later) adjust trip-level fields
trek-call.cmd update_trip @t2.json
   t2.json    { "tripId": 2, "start_date": "2026-08-02", "end_date": "2026-08-02" }

:: 5) flesh out each place (snake_case duration!)
trek-call.cmd update_place @up1.json
   up1.json   { "tripId": 2, "placeId": 2, "duration_minutes": 90,
                "lat": 31.2397, "lng": 121.4905,
                "address": "中山东一路, 上海市黄浦区",
                "description": "黄浦江西岸万国建筑博览群，对岸是陆家嘴天际线。" }

:: 6) timeline
trek-call.cmd update_assignment_time @a1.json
   a1.json    { "tripId": 2, "assignmentId": 2, "place_time": "09:30", "end_time": "11:00" }

:: 7) budget
trek-call.cmd create_budget_item @b1.json
   b1.json    { "tripId": 2, "name": "豫园门票", "category": "Attractions",
                "total_price": 40, "currency": "CNY" }

:: 8) verify everything landed
trek-call.cmd get_trip_summary @s.json
   s.json     { "tripId": 2 }
```

Then point the user at **http://localhost:3000** to see it on the map, and run
`trek.cmd stop` when the planning session is over.
