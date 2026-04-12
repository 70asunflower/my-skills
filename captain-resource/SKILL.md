---
name: captain-resource
description: "Add a new resource (link/article/external material) to one of the three learning repositories: ai-learning-journey, embodied-ai-learning, or ic-chip-design-learning. Trigger whenever the user provides a URL or asks to save a resource to their learning repos, or mentions adding content to these directories. Do this for any resource the user wants to catalog — tutorials, docs, videos, tools, papers — regardless of domain. When in doubt about which repo, ask the user."
---

# Captain Resource

Add a URL or resource to the correct learning repository following the 3-place update pattern.

## Step 1: Choose the right repository

Three repos exist under `P:\my_project\`. Pick the best match:

| Repo | Focus |
|------|-------|
| `ai-learning-journey/` | LLMs, agents, prompts, AI frameworks, official docs |
| `embodied-ai-learning/` | Robotics, VLA, sim-to-real, Isaac Sim, MuJoCo, ROS2 |
| `ic-chip-design-learning/` | GPU/CUDA, RTL, EDA tools, IC design, hardware architecture |

If unsure, ask the user. If a link fits multiple repos (e.g., CUDA touches both AI and IC design), add it to all applicable repos.

## Step 2: Choose the right subfolder

Each repo has `0-Resources/` with different categories. Check the subfolder structure below and pick the best match. The naming convention is the same across all repos — each subfolder has a `README.md` with a table of existing resources.

### ai-learning-journey

| Subfolder | Content |
|-----------|---------|
| `1-Official-Docs/` | Official docs, best practices |
| `2-Papers/` | Research papers |
| `3-Tutorials/` | Tutorials, blogs, courses |
| `4-Tools-Frameworks/` | Tools & frameworks |
| `5-Datasets/` | Datasets |

### embodied-ai-learning

| Subfolder | Content |
|-----------|---------|
| `1-Papers/` | Important papers |
| `2-Frameworks-Tools/` | Frameworks & tools |
| `3-Datasets/` | Datasets |
| `4-Tutorials-Courses/` | Tutorials, blogs, courses |
| `5-Projects-OpenSource/` | Open-source projects |

### ic-chip-design-learning

| Subfolder | Content |
|-----------|---------|
| `1-Books/` | IC design textbooks |
| `2-Papers/` | Research papers |
| `3-EDA-Tools/` | EDA tools |
| `4-OpenSource-Projects/` | Open-source projects |
| `5-Courses-Tutorials/` | Courses & tutorials |
| `6-Industry-Standards/` | AMBA, UCIe, JEDEC, etc. |

## Step 3: Create the resource file

Create a `.md` file in the chosen subfolder. Naming: lowercase, hyphen-separated (e.g., `cuda-programming-guide.md`).

Start with frontmatter:

```markdown
---
source: <original URL>
date: YYYY-MM-DD
tags: [tag1, tag2, tag3]
---

# Title

## 核心要点（摘要）

Brief summary in Chinese.

## 详细内容

Key points, topics, what this resource covers.

## 个人备注

Why you're saving it, how it connects to your learning goals.

_Last updated: YYYY-MM-DD_
```

Adjust headings based on content type (e.g., "主要内容" for docs, "核心贡献" for papers). Keep content bilingual or Chinese as the user prefers.

## Step 4: Update the subfolder README.md

Add a row to the table in the subfolder's `README.md`:

```markdown
| [Resource Name](filename.md) — one-line description | `#tag1 #tag2 #tag3` | YYYY-MM-DD |
```

## Step 5: Update the main README.md wiki navigation

Find the matching `<details>` section in the root `README.md` and add the link. All repos use `<details open>` for most sections. Example:

```markdown
<details open>
<summary>4-Tutorials-Courses</summary>

- [Resource Name](0-Resources/4-Tutorials-Courses/filename.md) — one-line description

</details>
```

## Step 6: Update 0-Resources/0-Index.md

Add an entry to `0-Resources/0-Index.md`. The format varies slightly by repo — follow the existing pattern (usually a table row or link under the relevant section).

## Step 7: Commit and push

All three repos are git repositories under `P:\my_project\`. Before running any git command, **always cd into the correct repo first** — don't run git from `P:\my_project` itself.

```bash
cd <repo-name>  # ai-learning-journey, embodied-ai-learning, or ic-chip-design-learning
git add <changed files>
git commit -m "Add <resource name> to <category>"
git push
```

If push fails due to remote changes, `git pull --rebase` and push again.

## Key rules

- **File names**: lowercase, hyphen-separated
- **Every new file gets linked** in: subfolder README → main README wiki nav → 0-Index.md
- **`Last updated` footer** on every resource file
- **Chinese descriptions** preferred, bilingual OK
- **Frontmatter tags** should be short English keywords (the same tags appear in both README table and .md file)
