---
name: siyuan-kernel-ops
description: Safely search, read, create, edit, move, and batch-process a local SiYuan knowledge base from WorkBuddy through SiYuan's Kernel HTTP API. Use when the user mentions SiYuan/思源笔记, notebooks, documents, blocks, backlinks, attributes, SQL/full-text search, daily notes, or asks WorkBuddy to organize or write back knowledge. Prefer block-level, idempotent edits; protect block IDs, references, assets, and user data.
compatibility: WorkBuddy on Windows with Python 3 and local access to a running SiYuan desktop/kernel. The default workspace config is D:\MyData\Warehouse\siyuan-backup\conf\conf.json; SIYUAN_URL, SIYUAN_TOKEN, and SIYUAN_CONF may override it.
metadata:
  version: "2.3.0"
  target: "WorkBuddy + SiYuan"
---

# WorkBuddy × SiYuan — safe kernel operations

Treat SiYuan as a **block graph**, not a folder of Markdown files. Preserve stable block IDs, references, attributes, assets, and backlinks. Use the Kernel HTTP API for live work. Never write `.sy`, SQLite, index, or `conf.json` files directly.

## Operating contract

1. **Read narrowly, write minimally.** Resolve the exact notebook/document/block first. Update the smallest stable block that satisfies the request.
2. **No guessed target.** If a name/path matches multiple documents, show notebook + human path + ID and ask the user to choose.
3. **No guessed intent.** Search/read requests are read-only. Do not turn a summary, checklist, or suggested action into a write unless the user asked to change SiYuan.
4. **Idempotent by default.** Re-running a task must not duplicate documents, headings, or appended text. Compare normalized content or use a stable operation marker.
5. **Verify every mutation.** HTTP 200 is transport success only. Require `code == 0`, then read back the changed object and verify the intended postcondition.
6. **Stop on inconsistency.** Never retry an ambiguous write automatically. Re-read state first; retry only if the write provably did not apply.
7. **Protect secrets.** Never print, log, commit, or place the API token in generated files. Redact it as `<redacted>` in diagnostics.
8. **Destructive actions require explicit confirmation.** Confirm immediately before delete, bulk move/rename, whole-document replacement, or any operation that may regenerate block IDs.

## 1. Connect and validate

Use this precedence on every new WorkBuddy session:

1. `SIYUAN_URL` + `SIYUAN_TOKEN`, when both are set.
2. `SIYUAN_CONF`, when set.
3. `D:\MyData\Warehouse\siyuan-backup\conf\conf.json`.
4. Official default URL `http://127.0.0.1:6806`, with token from config or supplied securely by the user.

When reading `conf.json`, locate the token defensively (normally `api.token`) and collect loopback URLs from `serverAddrs` if present. Do not assume the port is always fixed or always dynamic. Reject non-loopback HTTP URLs unless the user explicitly configured a trusted remote kernel.

Probe **a real data endpoint**, not only `/api/system/version`:

- `POST /api/notebook/lsNotebooks` with `Authorization: Token <token>`
- `Content-Type: application/json`
- Accept only a JSON envelope with `code == 0` and `data.notebooks` present.

If several candidate URLs pass, prefer in order: explicit environment URL, config's current `127.0.0.1` URL, then `6806`. If none pass, report one concise diagnosis: SiYuan not running, bad token, unreachable URL, or malformed response. Do not launch or reset SiYuan unless the user asks.

### Client choice: language-agnostic HTTP/JSON

SiYuan's Kernel API is plain HTTP `POST` + JSON — **no language or SDK is required** (official `API.md` shows no client preference; community skills use `curl`). In this WorkBuddy sandbox we default to Python **only** because Git Bash mangles Chinese inside inline `curl -d '{"data":"中文"}'` JSON. Python with `ensure_ascii=False` + writing the body to a file avoids that. A `curl` variant is equally valid if you write the JSON to a file and use `-d @file`:

```bash
curl -s -X POST "$SIYUAN_URL/api/notebook/lsNotebooks" \
  -H "Authorization: Token $SIYUAN_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @/tmp/siyuan_req.json
```

Use one temporary script/file rather than many fragile one-line commands.

```python
import json, os, urllib.request, urllib.error
from pathlib import Path

DEFAULT_CONF = Path(r"D:\MyData\Warehouse\siyuan-backup\conf\conf.json")
CONF = Path(os.environ.get("SIYUAN_CONF", str(DEFAULT_CONF)))


def load_connection():
    env_url = os.environ.get("SIYUAN_URL", "").rstrip("/")
    env_token = os.environ.get("SIYUAN_TOKEN", "")
    conf = {}
    if CONF.is_file():
        conf = json.loads(CONF.read_text(encoding="utf-8-sig"))
    token = env_token or ((conf.get("api") or {}).get("token") or "")
    urls = []
    if env_url:
        urls.append(env_url)
    for value in conf.get("serverAddrs") or []:
        if isinstance(value, str) and value.startswith(("http://127.0.0.1:", "http://localhost:")):
            urls.append(value.rstrip("/"))
    urls.append("http://127.0.0.1:6806")
    urls = list(dict.fromkeys(urls))
    if not token:
        raise RuntimeError("SiYuan API token not found")
    return urls, token


def call(base, token, path, payload=None, timeout=30):
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"SiYuan request failed at {path}: {type(exc).__name__}") from exc
    if not isinstance(result, dict) or result.get("code") != 0:
        msg = result.get("msg", "malformed response") if isinstance(result, dict) else "malformed response"
        raise RuntimeError(f"SiYuan API error at {path}: {msg}")
    return result.get("data")


def connect():
    urls, token = load_connection()
    errors = []
    for base in urls:
        try:
            data = call(base, token, "/api/notebook/lsNotebooks", {}, 5)
            if isinstance(data, dict) and isinstance(data.get("notebooks"), list):
                return base, token
        except Exception as exc:
            errors.append(f"{base}: {type(exc).__name__}")
    raise RuntimeError("No authenticated SiYuan kernel found; " + "; ".join(errors))
```

Do not display `token`. Use longer timeouts only for exports/searches. Reads may be retried after reconnecting; writes may not.

## 2. Resolve targets efficiently

Prefer stable IDs once known. Accept `siyuan://blocks/<id>` links and extract the block ID.

### Human path → document ID

Fast path:

1. List notebooks with `/api/notebook/lsNotebooks` and resolve the exact notebook name/ID.
2. Call `/api/filetree/getIDsByHPath` with `{"notebook": NBID, "path": "/human/path"}`.
3. Zero results: search. One result: use it. Multiple results: disambiguate; never select the first silently.

Use `/api/filetree/getHPathByID` to display or verify a resolved block/document. Do not recursively list the entire knowledge base unless path lookup and search both fail.

### Search router

- Exact known ID → fetch by ID.
- Exact known notebook + human path → `getIDsByHPath`.
- Natural-language or keyword lookup → `/api/search/fullTextSearchBlock`.
- Metadata, attributes, dates, types, or bulk candidate selection → read-only `/api/query/sql`.
- Backlinks/mentions → use SiYuan reference/backlink APIs when available; otherwise query refs metadata read-only.

For SQL:

- Allow only one `SELECT`/`WITH ... SELECT` statement generated from user intent.
- Always add a reasonable `LIMIT` (default 50; maximum 500 unless explicitly justified).
- Escape user text safely; do not concatenate untrusted text into SQL operators.
- Never use SQL to mutate SiYuan's database (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `PRAGMA`, `ATTACH`, etc.).
- Fetch full content only for selected candidates; do not dump the entire `blocks` table into model context.

Return compact search results: title/context, notebook, human path, block type, updated time when available, and ID/deep link.

## 3. Read with the least expensive endpoint

| Need | Preferred endpoint |
|---|---|
| Full document as Markdown | `/api/export/exportMdContent` |
| One block's source | `/api/block/getBlockKramdown` |
| Direct child blocks | `/api/block/getChildBlocks` |
| Human path | `/api/filetree/getHPathByID` |
| Attributes | `/api/attr/getBlockAttrs` |
| Structure/outline | outline or document-tree endpoint available in the running version |

For large documents, first inspect outline/children, then load only relevant blocks. Preserve exact asset links such as `assets/...`, block references, query embeds, IAL/Kramdown attributes, and code fences when preparing an edit.

Do not mistake an exported title for a duplicate body heading. Never delete a leading title solely because export output appears to repeat it.

## 4. Choose the safest mutation

Use the smallest applicable operation:

| Intent | Preferred operation |
|---|---|
| Edit one paragraph/heading/list/code block | `/api/block/updateBlock` on that block ID |
| Append content to a document/container | `/api/block/appendBlock` |
| Prepend content | `/api/block/prependBlock` |
| Insert near a known block | `/api/block/insertBlock` with `previousID` or `nextID` |
| Create document | `/api/filetree/createDocWithMd` after checking path |
| Rename document | `/api/filetree/renameDocByID` |
| Move document | `/api/filetree/moveDocsByID` after confirmation |
| Set custom attributes | `/api/attr/setBlockAttrs` |
| Delete one block/document | delete endpoint only after explicit confirmation |

Use `dataType: "markdown"` unless preserving exact DOM/Kramdown requires `dom`. Let the kernel generate IDs for genuinely new blocks.

### Whole-document replacement is exceptional

Updating a document root can rebuild descendants, change block IDs, break block references, detach attributes, and create large sync/history diffs. Use it only when the user explicitly requests a full rewrite and block-level editing is impractical.

Before a whole-document replacement:

1. Resolve and display the exact target.
2. Export the current Markdown and save a timestamped backup outside `data/`.
3. Record a SHA-256 hash of the exported content.
4. Inspect references/assets/attributes and preserve them or warn precisely.
5. Re-export immediately before writing; abort if the hash changed.
6. Ask for explicit confirmation with the impact summary.
7. Write once, then verify content and key links/assets.

Do **not** use “insert all new blocks, then delete all old blocks” as a safety pattern. It breaks stable IDs and can leave duplicates or partial deletion after failure.

## 5. Mutation protocol: preflight → write once → verify

For every write:

1. **Resolve** exact ID and human path.
2. **Read before state** using the appropriate endpoint.
3. **Preflight**:
   - Skip if desired state already exists.
   - Check the target still matches the state used to plan the change.
   - For create/append, detect duplicates by normalized content or a marker such as `custom-workbuddy-op=<stable-id>` where attributes are appropriate.
4. **Write exactly once.** Require `code == 0`.
5. **Read after state** from the canonical API.
6. **Assert the postcondition**, not merely that some text is present: correct block/path, exact intended content/attribute, preserved surrounding blocks/assets, and no duplicate insertion.
7. **Report** changed target(s), skipped unchanged target(s), and any failures. Never include the token.

If the postcondition fails:

- Reconnect by repeating connection discovery.
- Re-read the target and determine whether the write applied.
- If applied partially or ambiguously, stop and report. Do not issue a second write.
- If provably not applied, explain the failure; retry only with user approval for destructive/high-impact operations.

## 6. Batch work

For bulk clean-up, tagging, migration, or restructuring:

1. Build a read-only candidate list first. Enumerate explicit block IDs from `getChildBlocks` (live) and filter by type/parent/content — **never** select candidates by a timestamp-prefix glob, which can sweep up a document's real body blocks (see §12.7).
2. Show scope and representative changes when impact is non-trivial.
3. Require confirmation for destructive or structural batches.
4. Process deterministic chunks (default 20 items).
5. Keep an operation journal outside the SiYuan `data/` directory containing IDs, before-hashes, intended changes, status, and errors—never the token or full private note bodies.
6. Verify each item before continuing. Stop the batch on the first integrity failure.
7. Re-running the batch must skip verified completed items.

Never parallelize writes to the same document. Avoid high write concurrency across the workspace; sequential writes are the safe default.

## 7. Knowledge workflows that fit SiYuan

Exploit SiYuan's strengths instead of flattening it into plain files:

- Prefer block references/backlinks over duplicated quotations.
- Use custom attributes for machine-managed state, provenance, and workflow markers.
- Use SQL/full-text search for candidate discovery, then operate on stable IDs.
- Preserve document hierarchy and human paths, but treat IDs as canonical after resolution.
- For research ingestion: create a source note, store source URL/date as attributes, summarize in blocks, and reference those blocks from topic notes rather than copying repeatedly.
- For daily capture: resolve the actual daily-note path/template first; never invent a parallel daily-note structure.
- For databases/attribute views, use documented database/attribute APIs; never mutate underlying SQLite tables.

## 8. Filesystem and sync safety

- Direct `.sy` access is diagnostic/read-only and a last resort when the API is unavailable. The JSON format is internal, and direct edits can corrupt indexes or lose changes.
- Never modify `data/`, `storage/`, SQLite databases, indexes, history, or sync metadata behind a running kernel.
- Never place the SiYuan workspace inside a third-party sync drive. Use SiYuan's supported sync/export mechanisms.
- For backups, prefer SiYuan snapshot/history/export or copy the workspace only with a consistent procedure. A Git commit is not a substitute for a live consistent backup.
- Preserve `assets/` references and upload new resources through `/api/asset/upload`.
- Do not start Git commit/push, repository reset, sync reset, or data-repository maintenance unless the user explicitly asks and the relevant dedicated workflow is available.

## 9. Response style

After read-only work, answer with concise findings and clickable `siyuan://blocks/<id>` deep links where useful.

After writes, report:

- `Changed`: exact document/block paths and IDs
- `Skipped`: already-correct items
- `Verified`: the postcondition checked
- `Warning`: only if something remains uncertain

Do not narrate raw API traffic unless debugging was requested.

## Endpoint quick reference

```text
POST /api/notebook/lsNotebooks
POST /api/filetree/getIDsByHPath
POST /api/filetree/getHPathByID
POST /api/export/exportMdContent
POST /api/block/getBlockKramdown
POST /api/block/getChildBlocks
POST /api/search/fullTextSearchBlock
POST /api/query/sql
POST /api/attr/getBlockAttrs
POST /api/attr/setBlockAttrs
POST /api/block/updateBlock
POST /api/block/insertBlock
POST /api/block/appendBlock
POST /api/block/prependBlock
POST /api/block/deleteBlock
POST /api/filetree/createDocWithMd
POST /api/filetree/renameDocByID
POST /api/filetree/moveDocsByID
POST /api/filetree/removeDocByID
POST /api/asset/upload
```

## Endpoint quick reference (extended)

Export & conversion:
POST /api/export/exportMd            # Markdown (Lute renderer)
POST /api/export/exportHTML          # self-contained HTML bundle (assets + theme)
POST /api/export/exportMdHTML        # HTML for DOCX pipeline
POST /api/export/exportPreviewHTML   # HTML preview (Electron print-to-PDF)
POST /api/export/exportDocx          # Word .docx (Pandoc)
POST /api/export/exportEPUB          # EPUB (Pandoc)
POST /api/export/exportAttributeView # database / attribute view -> CSV
POST /api/export/exportSY            # native .sy.zip package
POST /api/export/exportData          # entire data/ archive
POST /api/convert/pandoc             # arbitrary Pandoc conversion

Daily notes & templates:
POST /api/filetree/createDailyNote   # create today's daily note
POST /api/template/render            # render a SiYuan template
POST /api/template/renderSprig       # render a Sprig template string

Assets & capture:
POST /api/asset/upload               # upload image/resource -> assets/
POST /api/network/forwardProxy       # fetch a URL through the kernel (web clip)
POST /api/storage/getRecentDocs      # recent documents

Databases / attribute views (v3.7.3, /api/av/):
POST /api/av/getAttributeView          # read a database / attribute view by id (rows + key schema)
POST /api/av/searchAttributeView       # search rows within a view
POST /api/av/getAttributeViewKeys      # list the view's key (column) definitions

Import engine (v3.7.3 migration: Obsidian + data archive; file uploads are multipart/form-data):
POST /api/import/importStdMd            # import standard Markdown into a notebook (returns new doc id)
POST /api/import/importSY               # upload a .sy.zip package (multipart, field "file")
POST /api/import/importData             # upload a data/ archive (multipart, field "file")

Bookmarks (v3.7.3 drag to/from bookmark panel):
POST /api/bookmark/getBookmark          # list bookmarks
POST /api/bookmark/removeBookmark       # remove a bookmark (requires "bookmark" field)

File tree & doc block order (v3.8.0):
POST /api/filetree/setSort             # set file-tree sort order (fields: notebookSorts, docSorts)
POST /api/block/getDocBlocksOrders     # full AST depth-first block-ID order of a doc (field: id = doc block id; excludes doc root & inline nodes; [] for empty doc)

## 10. Markdown authoring & publishing workflow (primary use case)

Most WorkBuddy ↔ SiYuan work is: generate/refine Markdown → write it into SiYuan → optionally export for publishing. Recommended order:

1. **Dedup first.** Before creating a new doc, run `/api/search/fullTextSearchBlock` (or `/api/query/sql`) to see if a related note already exists. Prefer updating/appending to it or using a block reference, instead of duplicating.
2. **Create or update.** New doc → `/api/filetree/createDocWithMd` (notebook + human path + markdown). **Response shape:** the call returns `code==0` with `data` being the new **doc id as a plain string** (e.g. `"20260720xxxx-yyyyy"`) — NOT a dict, so read `result["data"]` directly, do not do `result["data"].get("id")`. Edit → `/api/block/updateBlock` on the smallest block, or `/api/block/appendBlock` to add a section. For a full rewrite the user explicitly requested, `/api/block/updateBlock` on the document root is acceptable (see §4).
   - **Child-document trap:** when appending a child title to a parent path, resolve the parent with `/api/filetree/getHPathByID` (the human-readable path such as `/笔记本/父文档`) and append `/子文档标题`. Do **not** use the SQL `path` column (it returns the internal file-system path like `/2026xxxxx-yyyyy/2026xxxxx-zzzzz.sy`) as the `path` argument — that will create the child at the wrong level or under an ID-only branch in the sidebar.
3. **Assets.** If the Markdown references local images, upload each via `/api/asset/upload` and rewrite links to `assets/<name>`. Never leave broken `file://` or absolute paths.
4. **Verify.** Re-export via `/api/export/exportMdContent` and assert the intended content/headings/links are present (HTTP 200 ≠ success; require `code == 0` and read-back).
5. **Publish (optional).** Export the finished note to the target format and hand off:
   - 公众号 / 知乎 / 语雀: copy Markdown or HTML from `/api/export/exportMd` / `/api/export/exportHTML`.
   - Word / 毕业论文 / 报告: `/api/export/exportDocx` (Pandoc).
   - 电子书 / 长文: `/api/export/exportEPUB`.
   - Static site / 个人站: `/api/export/exportHTML` bundle.
   The user's multi-platform distribution (公众号/CSDN/小红书/个人站) maps directly onto these endpoints.

## 11. WorkBuddy × SiYuan integration map

Features worth wiring into WorkBuddy flows (ranked for a Markdown-authoring user):

- **Multi-format export** (`/api/export/*`, `/api/convert/pandoc`) — turn notes into publish-ready Markdown/HTML/Word/EPUB. Highest value given the publishing workflow.
- **Asset upload** (`/api/asset/upload`) — manage images in generated docs automatically.
- **Daily notes** (`/api/filetree/createDailyNote`) — auto-capture meeting notes, daily summaries, quick logs.
- **Pre-write dedup search** (`/api/search/fullTextSearchBlock`, `/api/query/sql`) — "what do I already have on X?" before creating; avoids duplicates, enables block refs.
- **Templates** (`/api/template/render`, `/api/template/renderSprig`) — fill consistent structures (meeting notes, reviews).
- **Block references / backlinks** (`/api/block/transferBlockRef`, `/api/block/getBlockKramdown`) — reference instead of copy; keeps a single source of truth.
- **SQL over the KB** (`/api/query/sql`) — lightweight RAG: retrieve relevant notes to ground WorkBuddy answers.
- **Databases / attribute views** (`/api/av/getAttributeView`, `/api/av/searchAttributeView`, `/api/export/exportAttributeView`) — read structured rows by key for RAG/retrieval, and export a view as CSV. v3.7.3 made DB entries deep-linkable and added reverse-links / in-editor properties (§13.1); prefer this over free-text SQL when the data is already a database.
- **Import engine** (`/api/import/importStdMd`, `/api/import/importSY`) — programmatically bring external Markdown or a `.sy.zip` package into a notebook; underlies the v3.7.3 Obsidian-import and unified data-migration UI (§13.2).
- **Web clip** (`/api/network/forwardProxy`) — fetch a URL and save as a note.
- **Bookmarks** (`/api/bookmark/getBookmark`) — surface or manage the user's saved blocks; v3.7.3 lets blocks be dragged to/from the bookmark panel (§13.3).
- **File-tree ordering** (`/api/filetree/setSort`) — programmatically sort notebooks and docs in the sidebar (v3.8.0, §13.6).
- **Document block order** (`/api/block/getDocBlocksOrders`) — get every content block ID of a doc in true on-screen (AST depth-first) order, containers included; ideal for re-ordering search/backlink results to match the page, or for TOC/bulk operations (v3.8.0, §13.7).

Do not over-index on block-graph theory for a Markdown-authoring user; the Markdown write → verify → export pipeline is the default path.

When an endpoint is unavailable in the installed SiYuan version, inspect that version's official API/CLI help and choose the closest documented endpoint. Do not guess request fields or fall back to direct data-file mutation.

## 12. Known kernel quirks (verified on v3.8.0 — running instance confirmed 3.8.0, the latest release as of 2026-08-13; new v3.8.0 capabilities documented in §13.6–13.8 — cost real debugging, save these)

### 12.1 `updateBlock(rootId, dataType:"markdown")` MERGES, it does not replace
When you call `updateBlock` on a document **root** with markdown, SiYuan **merges** the new markdown into the existing child-block tree. Old child blocks (e.g. stale copies carrying zero-width chars or a duplicate title) **survive** the write. Symptoms: `code==0` returns, the re-export looks unchanged, and a second `getChildBlocks` shows BOTH old + new blocks co-existing.
- **Fix A (minimal):** first `getChildBlocks(rootId)`, `deleteBlock` every returned child ID, THEN `updateBlock(rootId, markdown)` → fresh clean children are created from the markdown (no merge target remains).
- **Fix B (nuclear, ID changes):** `/api/filetree/removeDocByID` the whole doc, then `/api/filetree/createDocWithMd` with `notebook` + `path` + clean `markdown`. A brand-new doc cannot merge with a non-existent old one. Preserve the human path so the doc reappears in the same place; note the new doc ID for any deep links.
- **Finding the stale blocks:** in a `getBlockKramdown` render, each block line is followed by `{: id="..." updated="<ts>"}`. Old blocks carry the document's *original* creation timestamp; new ones carry the rewrite timestamp. Parsing `updated="<orig-ts>"` collects the stale IDs to delete surgically (Fix A variant).

### 12.2 `getBlockKramdown` and on-disk `.sy` are STALE; `getChildBlocks` is LIVE
After a write, `getBlockKramdown` (and grepping the `.sy` file under `data/<nb>/<folder>/<docId>.sy`) can return a **cached** render that does NOT reflect the write — even 13 s later, and even a sentinel `appendBlock` won't show up. This makes verification lie ("still 151 zero-width chars" when the doc is actually clean).
- **Verify with `/api/block/getChildBlocks`** on the doc root. It reads the **live** kernel block store, not the kramdown cache. Concatenate each child's `markdown` (or `content`) field and assert on that (e.g. `re.findall(zero_width_regex, blob)` returns 0). This is the authoritative postcondition check.
- `.sy` direct read is a valid last-resort diagnostic (read-only) when the API is unhelpful, but do NOT write `.sy`.
- Zero-width chars to strip when cleaning pasted content: `\u200b \u200c \u200d \u200e \u200f \u202a-\u202e \u2060-\u2064 \ufeff \u061c \u034f`. Build the regex with a **normal** Python string (`"[\u200b...]"`), NOT a raw string `r"[...]"` — in a raw string `\u200b` is literal backslash-text and will never match the real char.

### 12.3 `updateBlock` on a `table` node & `deleteBlock` on a heading (both silently partial)
Two more write pitfalls that return `code:0` yet don't do what you expect:

- **`updateBlock` on a `table` block with a changed row count / extra rows is silently dropped.** If you `updateBlock` a table node with markdown that *adds* rows, SiYuan keeps the **old** table and discards your new rows (re-export still shows the original). Symptom: `code:0`, but the new rows never appear. **Fix:** do NOT edit table contents via `updateBlock`. Instead `insertBlock` a *new* subsection/table as a sibling (with kramdown `{: id=...}` markers), or replace the whole table by `deleteBlock`-ing the table node then `insertBlock`-ing a fresh one.
- **`deleteBlock` on a heading does NOT cascade to its children.** The heading node is removed, but its child blocks (paragraphs, list items, table rows beneath it) become **orphans** that stay in the doc with their old IDs. They still render and still match string searches — so a re-export "looks fine" but a later `getChildBlocks` shows duplicate/ghost blocks. **Fix:** when deleting a subtree, collect the heading's child IDs (via `getChildBlocks`) and `deleteBlock` **each child ID** too — not just the heading. When cleaning up a misplaced insert, delete the heading AND every bullet/row ID it created.
- **`updateBlock` on an `l` (list container) block REPLACES the whole list — partial items are DELETED.** Verified 2026-08-24: calling `updateBlock` on a list container with markdown containing only ONE of the original four bullets silently deleted the other three (`code:0`, no error). The list container's markdown must always be the **complete** list — pass every item you want to keep. Same principle as table rows: give the full content or don't touch it. **Fix:** read the container via `getChildBlocks` first, build the full-item markdown (kept items unchanged + edits + additions), then `updateBlock` once with all of it; verify item count afterwards.

### 12.4 Writing KaTeX math blocks: mirror the doc's already-rendering formulas

When you `appendBlock` / `insertBlock` / `updateBlock` Markdown containing `$$ ... $$` formula blocks, SiYuan renders them with its **bundled KaTeX**. A formula that "looks valid" in raw LaTeX can still **render blank or throw an error** in SiYuan's KaTeX config — verified the hard way (an appended section showed every formula as blank, all at once).

**SiYuan math delimiters are `$$…$$` (block) and `$…$` (inline) ONLY.** Standard LaTeX delimiters `\[…\]` and `\(…\)` are **not** recognized by SiYuan's Markdown parser and render as literal raw text — a doc that "shows the LaTeX source instead of rendered formulas" almost always has these. The fix is a pure delimiter conversion (same math, no content change): `\[`→`$$`, `\]`→`$$`, `\(`→`$`, `\)`→`$`. Watch for HTML-corruption artifacts inside formulas (e.g. `<sup>2</sup>` where `^{2}` was intended); convert `<sup>`/`</sup>` back to `^{…}`/`}` only when the intended superscript is unambiguous, and surface ambiguous cases to the user. (Full pattern demonstrated in the 2026-07-31 `大模型数学计算解析` recovery — 147 `\[`+29 `\(` → 147 `m` blocks + inline `$`.)

Pitfalls that break rendering in SiYuan's KaTeX (these are NOT present in the doc's own already-working `m` blocks):
- **Spacing macros `\;` `\:` `\,` `\!`** — SiYuan's KaTeX may not recognize them; a block containing them can render blank/error.
- **`\qquad` / `\quad` cramming two equations onto one line** inside a single `$$` block. SiYuan expects **one equation per `$$` block** — its own formulas never put two on one line.
- Any other macro the doc's verified-rendering formulas do not already use.

**Rule (do this every time you write a formula):**
1. Before writing, fetch ONE existing working `m` block in the **same document** (`getChildBlocks` on the doc root → filter `type == "m"` → read its `markdown`).
2. **Mirror its LaTeX style exactly**: same spacing (plain ASCII spaces, NOT `\;`/`\,`), same one-equation-per-block convention, same command set. If you must show two related equations, split them into **two separate `$$` blocks** (two `m` blocks), exactly like the doc's own style.
3. After the write, re-export or `getChildBlocks` and grep **every `m` block** for the forbidden tokens (`\;`, `\,`, `\qquad`, `\quad`). **0 matches is the postcondition**; any match = a block that will not render. One missed `\,` in a single block was enough to break that block — fix it in place with `updateBlock` on that block ID (keep `type` as `m`).

### 12.5 Stale-port silent-write-failure trap

SiYuan's kernel port **drifts on every launch** — it is recorded in `conf.json` top-level `serverAddrs` as a `127.0.0.1:<port>` entry; the well-known `6806` is only one historical default and is frequently **stale**. Connecting to an OLD/stale port fails *silently and dangerously*:

- `POST /api/system/version` still returns `200` + `code:0`.
- `getBlockKramdown` / `getChildBlocks` still return **old (stale) content** from a previous session.
- Even `insertBlock` / `appendBlock` return `code:0` — **but the writes are silently dropped and never persisted.** Re-reading the doc shows your new content absent.

This is indistinguishable from success, so verification lies: "200 OK but nothing saved."

**Fix:**
1. **Always read the LIVE port from `conf.json`** top-level `serverAddrs` at the start of every session — never hardcode `6806` or any saved port. The §1 connection helper already does this; use it, don't bypass it.
2. After any write, **verify by reading back via `getChildBlocks`** (the live store), not by re-reading kramdown. Confirm the new blocks carry the *current* timestamp, not the document's original creation timestamp.
3. If a write "succeeds" but `getChildBlocks` shows it missing → you are almost certainly on a stale port. Re-resolve the port from `conf.json` and retry.

### 12.6 `insertBlock` ignores `nextID` without a `---` separator

When inserting "between" two existing blocks via `insertBlock` with a `nextID`, the position can be **ignored** if the surrounding blocks lack a markdown `---` (horizontal-rule) separator in the source. The inserted block then lands **after** the intended anchor instead of between the two targets.

**Symptom:** block appears, `code:0`, but in the wrong order (e.g. a new `§3.4.1` ends up after `§3.5` instead of right after `§3.4`).

**Fix:**
1. Insert using the correct `nextID` (the ID of the block that should *follow* the new one).
2. Immediately `getChildBlocks` and assert ordering is `... < newBlock < nextID`.
3. If misplaced, `deleteBlock` the misplaced block, then re-insert with the corrected `nextID`. Do NOT try to "move" it — delete + re-insert is the safe path (and see §12.3 about orphaned children when deleting a heading).

### 12.7 Never bulk-delete by timestamp prefix — enumerate exact block IDs

SiYuan block IDs embed the creation/modify timestamp as the leading prefix (e.g. `20260721203021-zpqj8ie`). When cleaning up "orphan" or "duplicate" blocks, it is tempting to `deleteBlock` everything matching a prefix like `20260721203021-*`. **This has caused irrecoverable data loss and must never be done.**

**The trap.** A document's **body** and an agent's **appended section** can share the same timestamp prefix when they were created or last modified within the same minute. A prefix match then deletes the legitimate body blocks — including `m` formula blocks — right alongside the intended orphans. In the 2026-07-21 incident, deleting `20260721203021-*` to remove a duplicate appendix wiped 15 real body formulas from `20260721202502-wzlx73c`; the only surviving signal was each lead-in sentence ("公式为：") left with no formula after it. No backup existed: the git mirror predated the doc, SiYuan's `temp/history.db` strips `$$` math from snapshots, and no `data/.history` was present — so recovery meant reconstructing every formula from the lead-in text.

**Rule (every time you delete more than one block):**
1. **Build the candidate list from `getChildBlocks` (live), never from a prefix.** Collect every child ID of the target doc/section.
2. **Filter by exact, verifiable criteria** — block `type` (`m`, `p`, `h`, …), a content substring, and *parent containment* (does the block descend from the section you intend to remove?). A shared timestamp prefix is **not** a valid filter.
3. **Print the filtered ID list and its count**, and for non-trivial scope show representative IDs/content to the user before deleting.
4. **Delete only the explicit ID list**, one `deleteBlock` per ID, sequentially (never parallel writes to the same doc, §6).
5. **After deletion, `getChildBlocks` (live) and assert**: each body lead-in still has its expected `m` block (no orphaned lead-ins), and the deleted count equals the candidate list length exactly — no more, no less.
6. **Prefer surgical subtree deletion over bulk.** If the target is a duplicate appendix, identify its heading/root ID and delete the subtree (heading + every child ID via `getChildBlocks`), not a prefix glob.

This compounds the other verification rules: a stale port (§12.5) makes deletion verification lie, and `getBlockKramdown`/`.sy` reads are stale caches (§12.2) — so always confirm deletions against the live `getChildBlocks` store.

### 12.9 Kernel-API writes do NOT push to the open SiYuan UI (user reports "看不到 / 内容没变")After a successful kernel write (`code:0`, verified via `getChildBlocks`), the SiYuan **desktop UI does not automatically re-read** the change. Two symptoms:
- A document already open in an editor **tab** still shows the old in-memory render (the tab caches the doc it loaded at open time).
- The **file tree** (left sidebar) may not show a newly created / renamed / moved doc until the tree is re-queried.

So even though the data is correctly persisted on disk **and** in the live kernel, the user opens SiYuan and sees nothing new. This is a *display* problem, not a write failure — **do NOT "fix" it by re-writing**, that duplicates content (§5 preflight; §12.7).

Fix (call via the connected kernel, `Authorization: Token <token>`):
1. **Refresh the whole UI:** `POST /api/ui/reloadUI` → `code:0`. Reloads the frontend; open document tabs are re-restored and re-pull from the kernel. This alone fixes a stale open tab.
2. **Refresh the file tree:** `POST /api/notebook/closeNotebook {"notebook": NBID}` then `POST /api/notebook/openNotebook {"notebook": NBID}` (both `code:0`). Forces the sidebar to re-list the notebook's docs.
3. **User-side fallback:** in the open tab press `F5` / `Ctrl+Shift+R`, or close & reopen the document; right-click the notebook in the sidebar → 刷新.

Rule: after any kernel write the user must *see*, proactively call `/api/ui/reloadUI` (and `closeNotebook`/`openNotebook` if a new doc must appear in the tree). Verify the write first with `getChildBlocks`, then reload. This was the root cause of two separate "思源里看不到" reports (2026-07-23: GRPO doc + Relax doc) where the content was confirmed present on disk + in the kernel but invisible in the UI.

### 12.10 `prependBlock` on a document root can eat the title block and silently drop content

Verified 2026-08-13: calling `POST /api/block/prependBlock` with `{"dataType":"markdown","data":"...","id": <docRoot>}` to add a note at the top of a document returned `code:0`, but the live `getChildBlocks` afterwards showed **the first heading (H1/title) block gone** and **the prepended content absent** — child count dropped by one, note nowhere in the doc. Do NOT use `prependBlock` on a document root for "add a note at the top".

**Fix (reliable):** edit the local Markdown source so the new block is in the right position (e.g. right after the H1), then do the full clean rebuild — loop-delete all root children (until `getChildBlocks` returns empty), then `updateBlock(rootId, dataType:"markdown")` with the full edited Markdown (see §12.1 Fix A). Verify H1 count == 1 and the new block position afterwards.

### 12.11 Titles containing `/` in `createDocWithMd` become nested empty docs

Verified 2026-08-13: calling `/api/filetree/createDocWithMd` with a `path` whose final segment contains `/` (e.g. a title like `卖期权前先看基本面（CSP / Covered Call 决策第一步）`) makes SiYuan treat the `/` as a **path separator**: it creates an *empty* parent doc named `卖期权前先看基本面（CSP` and nests the real content as a child `Covered Call 决策第一步）`. The tree shows a two-level structure where the first level is empty and the title is split. `getHPathByID` on the content confirms the unexpected nesting. This applies to both the `path` argument and the `title` argument (both feed the doc's name/hpath).

**Fix:** strip `/` from any human-readable title (use `与` / `&` / ` ` / `／` instead), and ensure the `path` argument you build has no `/` inside the final segment. If you already created the nested pair, remove both with `removeDocByID` and recreate with a `/`-free title.

### 12.8 Golden rules distilled (cross-cutting)

1. **Port is live, not cached.** Read it from `conf.json` every session; never trust a hardcoded port. A stale port silently eats writes (§12.5).
2. **Verify with `getChildBlocks` (live), not `getBlockKramdown` / `.sy` (stale cache).** The latter can lie 13s+ after a write (§12.2).
3. **`code:0` ≠ applied.** Always read back and assert the exact postcondition (correct block/path/content, no duplicate, correct ordering).
4. **Inspect before you assume it's missing.** When the user says "you didn't write X", first `getBlockKramdown`/`getChildBlocks` to see the *real current state* — content may already exist (pre-seeded or user-added). A blind re-write duplicates (§5 preflight).
5. **Don't edit table contents or headings in place.** `updateBlock` on a `table` drops changed rows; `deleteBlock` on a heading orphans children. Insert/replace as sibling subsections instead (§12.3).
6. **Mirror the doc's working style for formulas.** Match existing `m` blocks' LaTeX exactly — no spacing macros, one equation per `$$` block (§12.4).
7. **Never parallelize writes to the same document.** Sequential writes only (§6).
8. **Never bulk-delete by timestamp prefix.** A doc's body and an agent's appended section can share a creation-prefix; a prefix glob deletes legitimate blocks (e.g. body `m` formulas) along with the orphans. Enumerate exact IDs from `getChildBlocks`, filter by type/parent, delete only that list sequentially, then live-verify the count and that no lead-in lost its `m` block (§12.7).
9. **Reload the UI after a write the user must see.** A kernel write does not auto-refresh the desktop UI; an open tab keeps its old render and the file tree may not show new docs. After verifying the write with `getChildBlocks`, call `/api/ui/reloadUI` (and `closeNotebook`/`openNotebook` to refresh the tree). Otherwise the user reports "看不到" even though the data is correct (§12.9).

## 13. Recent-version capabilities (running instance confirmed v3.8.0, latest as of 2026-08-13; v3.7.3 in §13.1–13.5, v3.8.0 in §13.6–13.8)

The SiYuan instance this skill runs against was upgraded to **v3.8.0** (major release, published 2026-08-12; prior baselines this skill was verified on: v3.7.2 → v3.7.3 → v3.8.0). Each v3.8.0 change below was **verified against the live running kernel or the instance's own `conf.json`** — do not assume the same paths exist on older/newer builds; re-probe if the instance is upgraded again.

### 13.1 Databases / attribute views via `/api/av/*`
v3.7.3 substantially enhanced databases: column alignment, reverse-links in the attribute panel, per-entry templates, **deep-linkable entries** (#12022), and in-editor DB properties. They are now readable through the kernel:
- `POST /api/av/getAttributeView` — fetch a view (its rows + key/column schema) by view id.
- `POST /api/av/searchAttributeView` — search rows within a view.
- `POST /api/av/getAttributeViewKeys` — list the view's key (column) definitions.
Use these for **structured RAG/retrieval**: pull a database's rows by key instead of free-text SQL, then ground WorkBuddy answers. A DB entry is deep-linkable (v3.7.3 #12022) — resolve the entry row id from `getAttributeView` and link via `siyuan://blocks/<entryId>`.
- **Write caution:** editing DB cell values is best done through the dedicated `av` write endpoints or the UI. Do **NOT** blast a database by `updateBlock(rootId)` — that triggers the merge/survival quirk (§12.1) and can mangle the view. Treat a database as a first-class block: edit its smallest cell/row block, not the doc root.

### 13.2 Import engine (migration: Obsidian, data archive)
v3.7.3 added a unified data-migration UI (#13728) and **Obsidian Vault import (#18172)**. The underlying kernel import engine (probe-confirmed):
- `POST /api/import/importStdMd` — import standard Markdown into a notebook (useful when you want SiYuan's importer normalization instead of a raw `createDocWithMd`). Returns `code:0` with the new doc id.
- `POST /api/import/importSY` / `POST /api/import/importData` — upload a `.sy.zip` package or a `data/` archive. **These require `Content-Type: multipart/form-data`** (a bare JSON POST returns `request Content-Type isn't multipart/form-data`). Upload the file as the form field `file`.
The literal path `/api/import/importObsidian` does **NOT** exist as a standalone endpoint — Obsidian import is driven through this same engine from the UI. Prefer `importStdMd` / `importSY` for programmatic migration.

### 13.3 Bookmarks via `/api/bookmark/*`
v3.7.3 lets you drag blocks to/from the bookmark panel (#9340). Kernel endpoints (probe-confirmed):
- `POST /api/bookmark/getBookmark` — list the user's bookmarks.
- `POST /api/bookmark/removeBookmark` — remove one; requires a `bookmark` field (the bookmark id). Returns `code:-1 Field [bookmark] is required` if omitted.
Use to surface the user's saved blocks or to manage bookmarks programmatically (e.g. auto-bookmark docs WorkBuddy just created).

### 13.4 Web-clipper path template (#16507) — workflow tip, not a kernel endpoint
The SiYuan web clipper can now be configured with a **new-document path template**, so clipped pages land in a predictable location. This pairs with the kernel web-clip path (`/api/network/forwardProxy`, §11): decide the target notebook/path up front, clip via the proxy, then the clipped doc appears where the template says. No new kernel API — it is clipper-side config.

### 13.5 v3.7.3 bugfixes that affect this skill
- **Heading creation via `#` (#18221) was broken in older builds and fixed in 3.7.3.** Our pipeline writes headings as Markdown (`## ` syntax) inside `updateBlock`/`insertBlock`, which works regardless; but if a future version regresses, keep using Markdown heading syntax rather than the `#` shortcut.
- **`.sy.zip` export lost database data (#18248) — fixed in 3.7.3.** Our backup guidance (§8, `exportSY`/`exportData`) is now safe for databases; you can rely on `.sy.zip` snapshots without DB data loss.
- **Security fixes (#18219).** Prefer the loopback kernel (§1) and never expose the token; no skill-level change needed beyond the existing redaction rules (§1.7).

### 13.6 File-tree sort via `/api/filetree/setSort` (v3.8.0, #15776)
Programmatically set the file-tree sort order. Live probe confirms the endpoint exists; it returns `code:-1 Fields [notebookSorts] and [docSorts] must not both be empty` when called with an empty payload — so at least one of `notebookSorts` / `docSorts` is required. Send the full desired ordering (e.g. an array of notebook ids, or per-doc sort entries) rather than a single move; think of it as "set the whole order", not "move one item".

### 13.7 Doc block order via `/api/block/getDocBlocksOrders` (v3.8.0, #18416)
Returns every content block ID of a single document in **true on-screen order** — a full AST depth-first pre-order traversal, including list, list-item, quote, super-block containers (unlike `getBlockIndex`/`getBlocksIndexes`, which collapse nested blocks to their top-level ancestor index for scrollbar use). Live probe confirms: requires `{"id": <doc block id>}` (non-doc id or missing doc → error), returns `data` as an ordered id array, excludes the doc root itself, inline nodes and attribute nodes, and returns `[]` for an empty doc. Use it to re-order search/backlink/query results to match the page, or for TOC/export/batch processing.

### 13.8 v3.8.0 config-layer capabilities — AI, MCP, OIDC (NOT kernel HTTP APIs)
v3.8.0 added semantic search, an AI Agent, MCP support and OIDC auth. These are **configuration / UI-layer features** — there is no new `/api/ai/*`, `/api/mcp/*` or `/api/auth/*` HTTP endpoint (verified by live probing: all such candidates return 404). They are configured in the instance's `conf.json`:
- `ai.embedding` (baseURL/apiKey/dimensions, `enabled:false`) + `ai.rerank` (endpoint/candidateCount, `enabled:false`) — the semantic-search stack; the `ai.providers[]` list holds OpenAI-compatible provider configs.
- `ai.agent` (modelId, maxToolCallRounds, capabilityPolicy/approvalPolicy) — the built-in AI Agent.
- `ai.mcp.servers` + `mcpOAuth` — MCP **client** support: SiYuan can connect to external MCP servers for its built-in AI, with OAuth for the servers. **This is client-side only**: there is NO built-in "SiYuan-as-MCP-server" endpoint that WorkBuddy could connect to. If the user wants SiYuan exposed to an external AI via MCP, that is still a community/plugin solution (e.g. `siyuan-mcp-server` or `syplugin-anMCPServer`) — do not claim native support.
- `oidc` (enabled:false, issuerURL/clientID/scopes/claimRules) — OIDC authentication for the kernel/API access, again a config-layer concern.
Implication for WorkBuddy flows: these features are not directly scriptable through the kernel HTTP API today. WorkBuddy's own integration continues to use the documented `/api/*` endpoints; the `ai.mcp.servers` list is only relevant if the user asks us to configure MCP servers for SiYuan's built-in AI by editing `conf.json` (remember: never edit `conf.json` while SiYuan is running — stop the kernel, edit, restart).

### 13.9 行内格式坑实录（2026-08-23 半导体投资文档修复实战）

- **`~` 是思源的下标语法**：成对 `~text~` 保存时会被解析为真正的下标节点，导出时变成 `<sub>text</sub>` HTML。引用页码范围（如 `【3(112~216)】`）里成对的 `~` 会跨引用配对，把中间大段文字变下标——这是"引用乱码"的常见根因。**修复：把范围分隔符换成 `-`**（`digit~digit` → `digit-digit`）。若存储层已是字面 `<sub>` 标签，直接字符串替换为 `-` 即可；改成 `~` 无效（保存时又会被解析回下标节点，形成死循环）。
- **加粗边界双空格是思源规范化填充，不要对抗**：`**粗体**  后文` 的双空格是行内节点的规范序列化格式；updateBlock 写入单空格后存储层会自动变回。渲染显示正常间距，非垃圾。
- **批量逐块 updateBlock 会静默丢写/错乱**：连续快速对多个块 updateBlock + 立即 getChildBlocks 复访，部分写入不生效、甚至后续用旧快照覆盖新值（实测同一块日志出现 3 次、加粗闭合符丢失）。**整篇改写优先用 `/api/block/updateBlock` + `id=文档根ID`（dataType=markdown 写全文）**：一次事务原子生效；写后 sleep 2s 再 export 校验，失败重试（≤3 次）。逐块方式只用于少量块。
- **改前必须 exportMdContent 备份到本地文件**：本次靠备份整篇回滚，救回了中途误伤的加粗标记。
- **校验清单模板**：残留 `<sub>`/`</sub>`=0、`digit~digit`=0、零宽字符(U+200B/C/D,FEFF)=0、引用格式 `【[\w./()\-]+】` 全匹配、关键数字逐一 assert 存在、标题/表格/引用块数量与改前一致。


## 移动块与插入定位的坑（2026-08-25 实测）
- **移动块端点是 `/api/block/moveBlock`（驼峰）**，写成 `move_block` 会 404。参数：`{id, parentID, previousID}`，把块移到 previousID 之后；整段搬移时逐块按顺序移动、每次把上一块的 id 作为下一个的 previousID。
- **`insertBlock` 带 `previousID` 可能静默失效，内容落到文档开头**——插入后必须重新 `getChildBlocks`/导出复核位置；错位时用 moveBlock 逐块搬回。
- **moveBlock 搬移后立即 `exportMdContent` 可能短暂返回 `data: None`**（code=0 但 data 为空）——是内核索引重建中的瞬态，等几秒重试即恢复，不是写失败。批量导出校验脚本必须带重试（如 4 次 × 3s），否则误判失败（2026-08-25 实测：5 次 moveBlock 后连续两次导出 None，sleep 5s 后恢复正常）。
- **导出 Markdown 里的 U+200B 不一定是脏数据**：Lute 导出渲染器会在行内节点（`` `code` ``、加粗等）边界插入零宽空格作保护符。判断方法：对同一文档跑 `getChildBlocks` 统计存储层 markdown 的 U+200B 数量——存储为 0 而导出有值 = 渲染器行为，勿清理（清理也不可能，源里没有）。
