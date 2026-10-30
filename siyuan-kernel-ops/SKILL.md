---
name: siyuan-kernel-ops
description: Safely search, read, create, edit, move, and batch-process a local SiYuan knowledge base from WorkBuddy through SiYuan's Kernel HTTP API. Use when the user mentions SiYuan/思源笔记, notebooks, documents, blocks, backlinks, attributes, SQL/full-text search, daily notes, or asks WorkBuddy to organize or write back knowledge. Prefer block-level, idempotent edits; protect block IDs, references, assets, and user data.
compatibility: WorkBuddy on Windows with Python 3 and local access to a running SiYuan desktop/kernel. The default workspace config is D:\MyData\Warehouse\siyuan-backup\conf\conf.json; SIYUAN_URL, SIYUAN_TOKEN, and SIYUAN_CONF may override it.
metadata:
  version: "3.0.1"
  target: "WorkBuddy + SiYuan"
  changelog: "3.2.0 (2026-10-30) — added Q20: the user may edit the same doc while you operate on it; export the baseline immediately before surgery and verify both your markers and the user's markers afterwards. 3.1.0 (2026-10-27) — moved the 54-line connection helper into `scripts/sy.py` (tested, runnable smoke test); SKILL.md 291 → 245 lines. Q4 reduced to a pointer: formula detection/repair is owned solely by siyuan-markdown-formula-formatter, with a boundary note added there. 3.0.0 (2026-10-27) — length rewrite, 692 → 291 lines: removed the v3.7.3/v3.8.7 changelog sections, incident narratives, the duplicated endpoint list, project-internal gotcha IDs and the integration-map section; merged port/sandbox/loopback rules into §1; quirks renumbered Q1–Q19. Re-verified on v3.8.8."
---

# WorkBuddy × SiYuan — kernel operations

SiYuan is a **block graph**, not a folder of Markdown files. Block IDs, references, attributes, assets and backlinks are the user's data — protect them. Work through the Kernel HTTP API; never write `.sy`, SQLite, indexes or `conf.json`.

## Operating contract

1. **Resolve first.** Get the exact notebook/document/block ID before writing. Ambiguous match → show candidates and ask.
2. **Respect intent.** Search/read requests stay read-only — never turn a summary, checklist or suggested action into a write unless the user asked to change SiYuan.
3. **Read narrowly, write minimally.** Use the smallest stable block that satisfies the request.
4. **Be idempotent.** Re-running a task must not duplicate documents, headings or appended text.
5. **Verify every mutation.** `code:0` is not proof — read back and assert the postcondition (§5).
6. **Stop on inconsistency.** Never auto-retry an ambiguous write; re-read state, then decide.
7. **Confirm destructive actions immediately before doing them.** Never print, log or store the token.

## 1. Connect

Precedence: `SIYUAN_URL` + `SIYUAN_TOKEN` → `SIYUAN_CONF` → `D:\MyData\Warehouse\siyuan-backup\conf\conf.json` → `http://127.0.0.1:6806`.

The Kernel API is plain HTTP `POST` + JSON. Use Python with `ensure_ascii=False` — Git Bash mangles Chinese inside inline `curl -d '{"data":"中文"}'`.

**Use the tested helper shipped with this skill: `scripts/sy.py`.** `connect()` returns `(base, token)` after authenticating against a live kernel; `call(base, token, path, payload)` posts JSON and raises on `code != 0`. Both are already correct about port discovery, token rotation and encoding — do not re-implement them.

```python
import sys; sys.path.insert(0, r"<skill dir>/scripts")
from sy import connect, call
base, token = connect()
notebooks = call(base, token, "/api/notebook/lsNotebooks")["notebooks"]
```

Replace `<skill dir>` with the skill's base directory. Smoke test: `python scripts/sy.py` (prints kernel URL, version, notebooks).

**Connection rules — every one of these has silently eaten writes:**

| Rule | Why |
|---|---|
| Read the port from `conf.json` `serverAddrs` every session; never hardcode `6806` or a saved port | Port drifts on every launch. A stale port returns `200`/`code:0` for **everything** — including writes that are then dropped. |
| Validate with a data endpoint (`lsNotebooks` → `data.notebooks`), not `/api/system/version` | `version` answers on a dead/stale kernel. |
| Write only through `127.0.0.1` | A LAN entry in `serverAddrs` reads fine but silently discards writes. |
| Read `api.token` in full each time | The token rotates on reset; a truncated value yields misleading 401/404. |
| Pass `dangerouslyDisableSandbox: true` on kernel calls | The Bash sandbox blocks localhost and fails **silently**. |
| Never try to launch SiYuan | The sandbox cannot headless-start it; API access needs the desktop client already running. |
| Never restart/reset SiYuan, and close it before any git op on the workspace | SQLite write conflicts; the user closes it, not you. |

If no URL authenticates, report one diagnosis (not running / bad token / unreachable / malformed response). Reads may be retried after reconnecting; writes may not.

## 2. Resolve targets

Accept `siyuan://blocks/<id>` links and extract the ID.

| Need | Endpoint |
|---|---|
| Notebook list | `/api/notebook/lsNotebooks` |
| Notebook + human path → doc ID | `/api/filetree/getIDsByHPath` `{notebook, path}` |
| ID → human path (display/verify) | `/api/filetree/getHPathByID` |
| Keyword / natural language | `/api/search/fullTextSearchBlock` |
| Metadata, attributes, dates, bulk candidates | read-only `/api/query/sql` |

Zero results → search. One → use it. Several → disambiguate; never silently pick the first. Don't recursively walk the whole KB unless path lookup and search both fail.

SQL: one `SELECT`/`WITH … SELECT` only, always `LIMIT` (default 50, max 500), escape user text, never `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`PRAGMA`/`ATTACH`, and fetch full content only for selected candidates. Return compact results: title/context, notebook, hpath, block type, updated time, ID.

## 3. Read

| Need | Endpoint |
|---|---|
| Whole doc as Markdown | `/api/export/exportMdContent` |
| One block's source | `/api/block/getBlockKramdown` (stale — see Q2) |
| Direct children | `/api/block/getChildBlocks` (live) |
| Human path | `/api/filetree/getHPathByID` |
| Type / parent | `/api/block/getBlockInfo` |
| Attributes | `/api/attr/getBlockAttrs` |
| On-screen block order | `/api/block/getDocBlocksOrders` |

For a large doc, read the outline/children first, then only the relevant blocks. Preserve `assets/...` links, block refs, query embeds, IAL attributes and code fences. An exported title that repeats the doc title is not a duplicate body heading — never delete it for that reason.

## 4. Write

| Intent | Operation |
|---|---|
| Edit one paragraph/heading/list/code block | `/api/block/updateBlock` with `id` |
| Append to a document/container | `/api/block/appendBlock` with **`parentID`** (not `id`, Q18) |
| Prepend | `/api/block/prependBlock` with **`parentID`** |
| Insert near a known block | `/api/block/insertBlock` with `previousID`/`nextID`/`parentID` |
| Create document | `/api/filetree/createDocWithMd` (returns the new doc id as a **plain string**) |
| Rename / move document | `/api/filetree/renameDocByID` / `moveDocsByID` (confirm first) |
| Set custom attributes | `/api/attr/setBlockAttrs` |
| Delete | only after explicit confirmation |

Use `dataType: "markdown"` unless you need exact DOM. Let the kernel mint IDs for genuinely new blocks.

**Whole-document replacement is exceptional** — it can rebuild descendants, change block IDs, break refs and detach attributes. Only when the user explicitly asks for a full rewrite: export + timestamped backup outside `data/`, hash it, inspect refs/assets, re-export and abort if the hash moved, get explicit confirmation, write once, verify. Never use "insert all new, then delete all old" as a safety pattern.

## 5. Verify

1. Resolve the exact ID and hpath.
2. Read the before-state.
3. Preflight: skip if already correct; detect duplicates by normalized content or a `custom-workbuddy-op=<id>` attribute.
4. Write **exactly once**, require `code == 0`.
5. Read the after-state from `getChildBlocks` (live) and assert the postcondition — correct block/path, exact content, neighbours intact, no duplicate.

On failure: reconnect, re-read, decide whether it applied. Partially or ambiguously applied → stop and report; never issue a second write. Provably not applied → explain, retry only with approval.

## 6. Batch

1. Build a read-only candidate list from `getChildBlocks`; filter by type/parent/content. **Never** select by timestamp prefix (Q6).
2. Show scope when impact is non-trivial; get confirmation for destructive or structural batches.
3. Chunk deterministically (default 20), sequential only — never parallel writes to one document.
4. Journal outside `data/`: IDs, before-hashes, intent, status, errors. No token, no note bodies.
5. Verify each item; stop on the first integrity failure; re-runs skip completed items.

## 7. Filesystem & sync safety

- `.sy` access is read-only diagnostics of last resort. Never modify `data/`, `storage/`, SQLite, indexes, history or sync metadata behind a running kernel.
- Never put the workspace inside a third-party sync drive. Backups: SiYuan snapshot/history/export, not ad-hoc file copies; a Git commit is not a consistent backup.
- Preserve `assets/` references; upload new files via `/api/asset/upload`.
- Don't start git commit/push, repo reset or data-repo maintenance unless asked.
- **Disaster recovery (read-only):** history snapshots sit at `<workspace>/history/<ts>-update|delete/<nb>/…/<doc>.sy` (~10 min cadence). In the v3 `.sy` format nodes are `{ID, Type, Properties, Children}`. Re-inserting a snapshot's kramdown **with its original `{: id=…}` lines restores the original block IDs**.
- **Companion skills — don't duplicate them here:** the `robocopy /MIR` + git backup routine lives in `siyuan-backup-sync`; LaTeX/KaTeX cleanup and 公式入库 in `siyuan-markdown-formula-formatter`.

## 8. Quirks — read the index before writing

Every entry below cost real debugging or real data loss. Each is a **still-current behaviour**, not a changelog.

| Symptom | Entry |
|---|---|
| `code:0` but nothing changed | Q1, Q3, Q12, Q13 |
| Multi-paragraph markdown → only first paragraph landed | Q12 |
| Added table rows / edited list item → rest vanished | Q3 |
| Deleted a heading, orphan children remain | Q3 |
| Formula renders blank or shows raw LaTeX | Q4 |
| "看不到" but data is on disk | Q7 |
| Blocks landed at doc top or wrong order | Q5, Q11 |
| Bulk delete wiped real body blocks | Q6 |
| Child doc created one level too deep | Q9 |
| Whole callout / pasted article vanished | Q10 |
| Hand-built table has extra empty columns | Q14 |
| Verification count is double the truth | Q16 |
| Request times out right after a reload | Q17 |
| `Field [parentID] is required` | Q18 |
| Fresh doc still starts with a blank line | Q19 |

**Q1 · `updateBlock(rootId, markdown)` MERGES, it does not replace.** Old children survive alongside the new ones — re-export looks unchanged, `getChildBlocks` shows both. Fix A: delete every child ID first, then `updateBlock(rootId, markdown)`. Fix B (nuclear, changes the doc ID): `removeDocByID` + `createDocWithMd`. Stale blocks are the ones whose `updated="<ts>"` equals the doc's original creation timestamp.

**Q2 · `getBlockKramdown` and `.sy` are stale caches; `getChildBlocks` is live.** Kramdown can lag a write by 13 s+ and makes verification lie. Always assert against `getChildBlocks` children `markdown`. Direct `.sy` reads are a read-only last resort. Zero-width set to strip: `\u200b \u200c \u200d \u200e \u200f \u202a-\u202e \u2060-\u2064 \ufeff \u061c \u034f` — build the regex from a **normal** string, not a raw string, or `\u200b` never matches.

**Q3 · Three partial-write traps, all `code:0`.**
- `updateBlock` on a `table` with added rows silently keeps the old table → build a new sibling table instead, or delete + insert.
- `deleteBlock` on a heading does **not** cascade — children orphan and still match searches → collect and delete each child ID too.
- `updateBlock` on an `l` list container **replaces the whole list**; pass the complete item set or lose the rest.

**Q4 · Formulas render only as `$$…$$` / `$…$`.** `\[…\]` and `\(…\)` show up as literal text. Spacing macros (`\;` `\:` `\,` `\quad` `\qquad`) and two equations crammed into one block render blank — **one equation per `$$`**, mirroring an existing `m` block's style. Detection, conversion and batch repair live in `siyuan-markdown-formula-formatter`; don't re-derive them here.

**Q5 · `insertBlock` with `nextID` can be ignored** when the neighbouring blocks lack a `---` separator — the block lands after the anchor instead of between. Verify order immediately; on misplacement delete and re-insert, don't try to move it.

**Q6 · Never bulk-delete by timestamp prefix.** A doc's body and an appended section can share a minute-prefix, so `2026…-*` deletes legitimate blocks. Enumerate exact IDs from `getChildBlocks`, filter by type + content + parent containment, print the list and count, delete one ID at a time, then assert the deleted count matches exactly and no lead-in lost its body block.

**Q7 · A kernel write does not refresh the desktop UI.** An open tab keeps its in-memory render; the tree may miss a new doc. This is display, never a reason to re-write. `POST /api/ui/reloadUI` fixes a stale tab; `closeNotebook` + `openNotebook` refreshes the tree. Verify with `getChildBlocks` first, then reload.

**Q8 · `prependBlock` on a document root can eat the title block** and drop the content while returning `code:0`. Don't use it to "add a note at the top" — edit the source and rebuild (Q1 Fix A), then assert exactly one H1.

**Q9 · A `/` inside a title creates nested empty docs.** `createDocWithMd` treats the final path segment's `/` as a separator, producing an empty parent plus a child. Strip `/` from titles (use `与`, `&`, `／`); if it already happened, `removeDocByID` both and recreate.

**Q10 · Endpoint names and the container-delete trap.**
- Children are `/api/block/getChildBlocks`, **not** `/api/filetree/getChildBlocks` (404).
- `/api/filetree/getDocInfo` is 404 — use `getHPathByID` + `getBlockInfo`.
- `/api/filetree/listDocsByPath` requires `{notebook, path}`.
- `asset/upload` is multipart with field **`file[]`**.
- **`getChildBlocks` returns a container's `markdown` including all nested children**, so a content/asset substring can match the *container* — and deleting it wipes the whole pasted article. Before any `deleteBlock`, assert `type` is a leaf (`p`/`t`/`l`/`h`/`c`/`m`).

**Q11 · Moving and ordering.** `moveBlock` (camelCase — `move_block` is 404) takes `{id, parentID, previousID}` and places the block after `previousID`; move a run block-by-block, feeding each previous ID forward. `exportMdContent` can briefly return `data: None` after a move burst — transient index rebuild, retry (4 × 3 s) instead of reporting failure. A U+200B in exported Markdown is usually Lute's inline-node guard, not dirty data: if the stored markdown has none, don't "clean" it.

**Q12 · `updateBlock` keeps only the FIRST block** of multi-block markdown, silently. One block per call; anything larger goes through `insertBlock` (which splits headings/code/tables/lists) or `appendBlock`. Editing an `h` needs the `#`-prefix and an `m` needs `$$` wrapping. Every heading level reports `type == "h"` — the level lives only in the `#` count — and headings are siblings under the root, so level shifts mean rewriting each one.

**Q13 · Batch rebuild degrades above ~20 children.** Fix A's delete loop partially fails at scale (every call `code:0`, 56–85 % of blocks survive). Above ~20 children go straight to Fix B, or chunk with a live re-read between chunks. Never write `while getChildBlocks(): delete…` — SiYuan regenerates one empty `p` and the loop never ends. Persist any new doc ID; a lost ID makes a successful rebuild look like a vanished document.

**Q14 · Hand-built tables: the pipe is both separator and attribute prefix.** Cells carry `|{: style="…"}cell`; naive concatenation yields `||`, parsed as an extra empty column. Build as `"|" + "|".join(S + c for c in cells) + "|"`, separator row `"|" + "|".join(" :---: " for _ in cells) + "|"`. Blank lines between rows make each row a separate paragraph — the doc then reports zero table blocks. Assert the table-block count matches the source.

**Q15 · Round-tripping kramdown carries block attributes back.** `getBlockKramdown` returns `{: id="…" updated="…"}` with the source; feeding it to `updateBlock` risks writing attributes into the body. Read content from `getChildBlocks(...)[i]["markdown"]`, or strip a leading `{: … }`. Those `updated` values are how you tell stale blocks from fresh ones (Q1).

**Q16 · Container vs leaf reads.** `getChildBlocks(leafId)` returns the leaf's *children*, never the leaf itself — read a block from its parent's list or build an `id → markdown` index from the doc root. Containers (callout, `b` quote, superblock) return nested content too, so counting occurrences over-counts; count only leaves whose markdown `fullmatch`es. The walk can also visit the same list item twice — never treat traversal count as block count.

**Q17 · The kernel goes unresponsive for a few seconds after `reloadUI`** (`WinError 10060`). Retry (3 × 2 s) around anything that follows a reload instead of reporting a write failure.

**Q18 · Write-endpoint parameters are not uniform.** `appendBlock`/`prependBlock` require **`parentID`**; `id` is not an alias (`Field [parentID] is required`). `insertBlock` needs one of `parentID`/`previousID`/`nextID`. `updateBlock`/`moveBlock` take `id`. **Probe instead of guessing** — POST `{}` and read the `Field [...] is required` message; validation runs before the write, so the probe is free and survives version upgrades that rename a parameter. `appendBlock` does split multi-block markdown correctly (one call took 130 blocks: 23 headings, 6 tables, 39 lists, a quote, a code fence).

**Q19 · A new document holds a zero-length `p` that regenerates if you delete it early.** Order: `appendBlock` → `getChildBlocks` → if `children[0]` is an empty `p`, delete that one ID → re-read to confirm the real first block leads. Same for `createDocWithMd` output.

**Q20 · The user may be editing the same doc while you operate on it.** A manual edit that lands between your `exportMdContent` baseline and the delete+rebuild gets overwritten, and the user's client can then sync its newer tree back — end state can mix both. Export the baseline immediately before surgery, not at session start; afterwards verify a fresh export for BOTH your marker strings and the user's content markers (their newest note, their added sections). Missing user markers = the client version was newer than your baseline; redo from a fresh export. Also `> [!NOTE]` blockquotes round-trip through `createDocWithMd`/`updateBlock` as callout blocks, so whole-doc rebuilds preserve SiYuan's `/note` annotations.

> Renumbered in v3.0.0: older notes citing §12.x map to Q1–Q19 in order (§12.5/§12.20 merged into §1, §12.12 into Q10).

## 9. Authoring workflow (primary use case)

1. **Dedup first** — search before creating; prefer append or a block reference over a duplicate doc.
2. **Create or update** — `createDocWithMd` for a new doc (its `data` is the doc id as a plain string, not a dict); `updateBlock` on the smallest block, or `appendBlock` for a new section.
   - **Child-doc trap:** build the child path from `getHPathByID`'s human path + `/子文档标题`. Never pass the SQL `path` column (an internal `.sy` path) — it nests the doc under an ID-only branch.
3. **Assets** — upload local images and rewrite links to `assets/<name>`; never leave `file://` or absolute paths.
4. **Verify** — re-export and assert headings/links/content.
5. **Publish** — `exportMd`/`exportHTML` for 公众号/知乎/CSDN/个人站, `exportDocx` for Word/报告, `exportEPUB` for long-form.

The Markdown write → verify → export pipeline is the default path. Don't over-index on block-graph theory. When an endpoint is missing in the installed version, check that version's API help — never guess fields or fall back to mutating data files.

## 10. Response style

Read-only work: concise findings with `siyuan://blocks/<id>` deep links.
Writes: `Changed` (paths + IDs) / `Skipped` (already correct) / `Verified` (postcondition) / `Warning` (only if genuinely uncertain). Don't narrate raw API traffic unless debugging was asked.

## Appendix · Endpoints

| Purpose | Endpoint | Note |
|---|---|---|
| Notebooks | `/api/notebook/lsNotebooks` | connection probe |
| Open/close notebook | `/api/notebook/openNotebook` · `closeNotebook` | tree refresh |
| Path ↔ ID | `/api/filetree/getIDsByHPath` · `getHPathByID` | `{notebook, path}` |
| List docs | `/api/filetree/listDocsByPath` | requires `notebook` |
| Create / rename / move / remove doc | `/api/filetree/createDocWithMd` · `renameDocByID` · `moveDocsByID` · `removeDocByID` | |
| Daily note | `/api/filetree/createDailyNote` | |
| Search | `/api/search/fullTextSearchBlock` · `/api/query/sql` | read-only SQL |
| Read block | `/api/block/getBlockKramdown` · `getChildBlocks` · `getBlockInfo` · `getDocBlocksOrders` | |
| Write block | `/api/block/updateBlock` · `appendBlock` · `prependBlock` · `insertBlock` · `moveBlock` · `deleteBlock` | see Q18 for parent fields |
| Attributes | `/api/attr/getBlockAttrs` · `setBlockAttrs` | |
| Assets | `/api/asset/upload` | multipart field `file[]` |
| Web clip | `/api/network/forwardProxy` | |
| Export | `/api/export/exportMdContent` · `exportMd` · `exportHTML` · `exportDocx` · `exportEPUB` · `exportAttributeView` · `exportSY` · `exportData` | |
| Convert | `/api/convert/pandoc` | |
| Templates | `/api/template/render` · `renderSprig` | |
| Databases (AV) | `/api/av/getAttributeView` · `searchAttributeView` · `getAttributeViewKeys` | read rows by key; never `updateBlock` a DB root (Q1) |
| Import | `/api/import/importStdMd` · `importSY` · `importData` | uploads are multipart, field `file`; there is no `importObsidian` endpoint |
| Bookmarks | `/api/bookmark/getBookmark` · `removeBookmark` | `removeBookmark` needs `bookmark` |
| File-tree sort | `/api/filetree/setSort` | `notebookSorts` / `docSorts`, not both empty |
| UI | `/api/ui/reloadUI` | then expect Q17 |
| System | `/api/system/version` | not a valid liveness probe |

**v3.8.8:** every endpoint above is live. AI/MCP/OIDC are **config-layer only** — there is no `/api/ai/*`, `/api/mcp/*` or `/api/auth/*` (all 404), and MCP is client-side, so exposing SiYuan to an external AI still needs a community plugin. Never edit `conf.json` while the kernel runs.

**Inline formatting traps:** `~text~` is SiYuan's subscript syntax — paired `~` in a page range (`112~216`) silently subscripts everything between them; use `-` instead, and don't try to "fix" it back to `~` (it re-parses). The double space after `**bold**` is normal serialization, not garbage. Rapid block-by-block `updateBlock` bursts lose or cross-contaminate writes — prefer one whole-document write for a full rewrite, and `exportMdContent` to a local file before touching an article.
