---
name: siyuan-backup-sync
description: Git backup/sync workflow for the SiYuan data repository
  (70asunflower/siyuan-backup). Covers the gh-credential push command, LFS quota
  awareness, the mandatory "close SiYuan before git" rule, the
  temp/install/*.exe .gitignore, and the plumbing-based history cleanup when a
  large installer accidentally got committed and blocks the push (GitHub GH001
  >100MB). Use when committing/pushing the siyuan data repo or fixing a blocked
  push.
agent_created: true
---

# SiYuan Backup / Git Sync

Repo: `D:\MyData\Warehouse\siyuan-backup` → remote `https://github.com/70asunflower/siyuan-backup.git`.
This is the user's personal note backup — treat it as precious. Least-surprise, never force-push published history.

## 0. MANDATORY before ANY git operation
**Close SiYuan first.** It holds a SQLite write lock; committing while it's open risks a corrupted snapshot. Wait for the user to close it (don't kill it yourself — that's a state-changing op needing explicit consent).

## 1. Safe commit scope
Commit only:
- `data/` (notes + attached assets)
- `history/` (snapshots)
- `conf/conf.json`

Exclude (add to `.gitignore`):
- `.lock`
- `temp/queue/`
- `temp/*.db-shm`, `temp/*.db-wal`
- `temp/*.db` (mutates live; skip to avoid an inconsistent in-flight snapshot)

## 2. Push command (interactive creds are disabled in this env)
```bash
git -c credential.helper="!gh auth git-credential" push
```
`gh` is already logged in as `70asunflower`. Plain `git push` fails because terminal credential prompts are blocked.

## 3. LFS awareness
- LFS quota: **1 GB** (was ~927 MB used — near limit). Watch it.
- `.sy` data files are **NOT** LFS-tracked → safe to commit freely.
- Only `temp/*.exe` and `*.db` are LFS. A fresh SiYuan installer (`siyuan-3.7.x-win.exe`, ~200 MB) is NOT auto-LFS and will blow GitHub's 100 MB hard limit.

## 4. Prevent installer commits (`.gitignore`)
```
temp/install/*.exe
!temp/install/siyuan-3.7.0-win.exe   # keep the LFS-tracked one
```
SiYuan's own backup script does `git add -A`, which would re-commit installers without this rule.

## 5. Fix a blocked push (GH001: >100 MB file in history)
Symptom: push rejected because an old (unpushed) commit contains a big `temp/install/*.exe`.
Strategy — **rewrite only the unpushed range** `origin/main..HEAD`; keep all already-published history hashes unchanged → push stays a fast-forward (no force-push, cloud safe).

Steps (plumbing, never touches the working tree — safe while SiYuan is open):
```bash
# 1. snapshot safety branch (local only, optional but recommended)
git branch backup-before-cleanup

# 2. for EACH commit in the range that contains the blob, rewrite its tree
#    without the exe, using a throwaway index:
GIT_INDEX_FILE=/tmp/idx git read-tree <rev>^{tree}
GIT_INDEX_FILE=/tmp/idx git rm --cached --ignore-unmatch temp/install/siyuan-3.7.1-win.exe
newtree=$(GIT_INDEX_FILE=/tmp/idx git write-tree)
newrev=$(git commit-tree $newtree -p <parent> -m "<msg>")
git update-ref refs/heads/main $newrev

# 3. repeat for every commit that carries the blob (a child commit's tree
#    ALSO contains it if it was built on top of the tainted one!)
```
⚠️ Lessons (easy to get wrong):
1. The blob must be stripped from **every** commit tree in the range that contains it — not just the one that first added it. Child commits inherit the tainted tree.
2. Plumbing rewrites only the `main` ref and does **not** update the real index. Before committing anything else, run `git reset --mixed <clean-rev>` so the index matches, or you'll re-add the exe.
3. Keep `backup-before-cleanup` until the user confirms the push succeeded.

Then push: `git -c credential.helper="!gh auth git-credential" push` (fast-forward).
To reclaim the ~209 MB the old branch holds in `.git`: `git branch -D backup-before-cleanup && git gc --prune=now` (only after success + user OK).

## 6. Gotchas
- Don't `git push --force` published history.
- `git filter-branch` refuses on a dirty tree (SiYuan leaves 500+ modified files) → use the plumbing approach above instead.
- Always verify `git rev-list --left-right --count origin/main...HEAD` shows `0 0` after a successful push.
- Device rule: only edit SiYuan on one machine at a time (workstation vs home PC) to avoid sync conflicts.
