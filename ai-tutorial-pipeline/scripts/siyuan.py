# -*- coding: utf-8 -*-
"""思源笔记 Kernel API 操作库。
铁律：端口永远从 conf.json 的 serverAddrs 现读（每次启动会漂移，写死必踩坑）；
写入后用 getChildBlocks 活数据校验；对用户可见的写入后 reloadUI；
入库前后做表格/公式格式校验（Qwen 复制输出的表格行间常夹空行，必须拼接）。
用法: python siyuan.py <status|find <kw>|recent|create <notebook> <path>|save <md> --parent-id ID --fallback T|tree <id>>
"""
import json, os, re, sys, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CONF = Path(os.environ.get("SIYUAN_CONF", r"D:\MyData\Warehouse\siyuan-backup\conf\conf.json"))


def load_connection():
    conf = json.loads(CONF.read_text(encoding="utf-8-sig")) if CONF.is_file() else {}
    token = os.environ.get("SIYUAN_TOKEN") or (conf.get("api") or {}).get("token") or ""
    urls = [os.environ["SIYUAN_URL"].rstrip("/")] if os.environ.get("SIYUAN_URL") else []
    urls += [v.rstrip("/") for v in conf.get("serverAddrs") or []
             if isinstance(v, str) and v.startswith(("http://127.0.0.1:", "http://localhost:"))]
    urls.append("http://127.0.0.1:6806")
    return list(dict.fromkeys(urls)), token


def call(base, token, path, payload=None, timeout=30):
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        res = json.loads(r.read().decode("utf-8"))
    if not isinstance(res, dict) or res.get("code") != 0:
        raise RuntimeError(f"{path}: {res.get('msg') if isinstance(res, dict) else 'malformed'}")
    return res.get("data")


def connect():
    urls, token = load_connection()
    errs = []
    for u in urls:
        try:
            call(u, token, "/api/notebook/lsNotebooks", {}, 5)
            return u, token
        except Exception as e:
            errs.append(f"{u}:{type(e).__name__}")
    raise RuntimeError("找不到可用的思源内核: " + "; ".join(errs))


ZW = re.compile("[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u2064\ufeff\u061c\u034f]")
SEG = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]*`|\$\$.*?\$\$|\$[^$\n]*\S\$)", re.S)


def join_table_rows(md):
    """去掉表格行之间的空行（GFM 要求行连续；Qwen 复制输出经常行间夹空行导致表格失效）。跳过代码围栏。"""
    lines = md.split("\n")
    out, fence = [], False
    for l in lines:
        ls = l.lstrip()
        if ls.startswith("```") or ls.startswith("~~~"):
            fence = not fence
            out.append(l)
            continue
        if fence:
            out.append(l)
            continue
        if ls.startswith("|") and out and out[-1].strip() == "":
            j = len(out) - 1
            while j >= 0 and out[j].strip() == "":
                j -= 1
            if j >= 0 and out[j].lstrip().startswith("|"):
                while len(out) - 1 > j:
                    out.pop()
        out.append(l)
    return "\n".join(out)


def _ncols(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return len(re.split(r"(?<!\\)\|", s)) + (1 if s == "" and line.strip() == "|" else 0)


def _is_sep(line):
    return bool(re.match(r"^\s*\|[\s:|\-]+\|?\s*$", line) and "-" in line)


def check_tables(md):
    """源 Markdown 层面的表格完整性检查。返回 (issues, n_tables)。"""
    lines = md.split("\n")
    issues, n_tables = [], 0
    i, fence = 0, False
    while i < len(lines):
        ls = lines[i].lstrip()
        if ls.startswith("```") or ls.startswith("~~~"):
            fence = not fence
            i += 1
            continue
        if not fence and ls.startswith("|") and i + 1 < len(lines) and _is_sep(lines[i + 1]):
            n_tables += 1
            rows = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i])
                i += 1
            header = _ncols(rows[0])
            for ri, r in enumerate(rows):
                if _ncols(r) != header:
                    issues.append(f"表{n_tables}第{ri + 1}行列数{_ncols(r)}!={header}")
        else:
            i += 1
    return issues, n_tables


def clean_markdown(md):
    """为思源清洗网页 AI 的 Markdown：零宽字符、CRLF、思源 KaTeX 不兼容写法、ASCII ~（下标语法陷阱）、表格行拼接。"""
    md = md.replace("\r\n", "\n").replace("\r", "\n")
    md = ZW.sub("", md)
    if md.count("```") % 2 == 1 or md.count("~~~") % 2 == 1:
        raise RuntimeError("内容截断：代码围栏未闭合，拒绝入库")
    out, pos = [], 0
    for m in SEG.finditer(md):
        if m.start() > pos:
            out.append(("text", md[pos:m.start()]))
        seg = m.group(0)
        kind = "code" if seg[:3] in ("```", "~~~") or seg[0] == "`" else "math"
        out.append((kind, seg))
        pos = m.end()
    if pos < len(md):
        out.append(("text", md[pos:]))
    fixed = []
    for kind, seg in out:
        if kind == "code":
            fixed.append(seg)
        elif kind == "math":
            if seg.startswith("$$"):
                inner = seg[2:-2]
                balanced = inner.count("\\begin{") == inner.count("\\end{")
                if not balanced and ("\\quad" in inner or "\\qquad" in inner):
                    # aligned 等环境不能拆，把间距宏换成空格
                    inner = re.sub(r"\\qquad(?![a-zA-Z])|\\quad(?![a-zA-Z])", " ", inner)
                    fixed.append("$$" + inner + "$$")
                elif "\\qquad" in inner or "\\quad" in inner:
                    pieces = [p.strip() for p in re.split(r"\\qquad(?![a-zA-Z])|\\quad(?![a-zA-Z])", inner) if p.strip()]
                    fixed.append("\n\n".join("$$" + p + "$$" for p in pieces))
                else:
                    inner = re.sub(r"\\[;,](?![a-zA-Z])", " ", inner).replace("\\!", "")
                    fixed.append("$$" + inner + "$$")
            else:
                inner = re.sub(r"\\[;,](?![a-zA-Z])", " ", seg[1:-1]).replace("\\!", "")
                inner = re.sub(r"\\qquad(?![a-zA-Z])|\\quad(?![a-zA-Z])", " ", inner)
                inner = inner.replace("~", " ")
                fixed.append("$" + inner + "$")
        else:
            fixed.append(seg.replace("~", "～"))
    return join_table_rows("".join(fixed))


def title_from_md(md, fallback):
    """从正文第一个（代码围栏外的）## 行取标题。"""
    fence = False
    for line in md.split("\n"):
        ls = line.lstrip()
        if ls.startswith("```") or ls.startswith("~~~"):
            fence = not fence
            continue
        if not fence and ls.startswith("## "):
            t = re.sub(r"\*\*+", "", ls[3:]).replace("/", "／").strip()
            if t:
                return t
    return fallback


def body_from_md(md):
    lines = md.strip().split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def doc_info(base, token, doc_id):
    """返回文档的 {notebook, hpath}。doc 根块在 blocks 表 type='d'，box 列即笔记本 ID。"""
    rows = call(base, token, "/api/query/sql",
                {"stmt": "SELECT box, hpath FROM blocks WHERE id='" + doc_id.replace("'", "''") + "' AND type='d' LIMIT 1"})
    if not rows:
        raise RuntimeError(f"文档 {doc_id} 不存在")
    return {"notebook": rows[0]["box"], "hpath": rows[0]["hpath"]}


def doc_exists(base, token, notebook, full_path):
    r = call(base, token, "/api/filetree/getIDsByHPath", {"notebook": notebook, "path": full_path})
    return list(r) if isinstance(r, list) and r else None


FORBID_MATH = [r"\\;", r"\\,", r"\\!", r"\\quad(?![a-zA-Z])", r"\\qquad(?![a-zA-Z])",
               r"\\\(", r"\\\)", r"\\\[", r"\\\]", r"<sup>", r"</sup>"]


def audit_doc(base, token, doc_id, expect_tables=None, min_blocks=5):
    """入库后格式校验（活数据）：块数、表格块数、伪表格段落、公式禁词。min_blocks 按内容形态放宽（如小红书短帖）。"""
    kids = call(base, token, "/api/block/getChildBlocks", {"id": doc_id})
    tables = [k for k in kids if k.get("type") == "t"]
    maths = [k for k in kids if k.get("type") == "m"]
    pseudo = [k for k in kids if k.get("type") == "p"
              and (k.get("markdown", "").count("|") >= 4) and k.get("markdown", "").lstrip().startswith("|")]
    bad_math = sum(1 for m in maths if any(re.search(p, m.get("markdown", "")) for p in FORBID_MATH))
    info = {"blocks": len(kids), "tables": len(tables), "maths": len(maths),
            "pseudo": len(pseudo), "bad_math": bad_math}
    problems = []
    if info["blocks"] < min_blocks:
        problems.append(f"块数过少 {info['blocks']}")
    if pseudo:
        problems.append(f"{len(pseudo)} 个伪表格（表格未解析，检查行间空行/列数）")
    if expect_tables is not None and len(tables) != expect_tables:
        problems.append(f"表格块数 {len(tables)} != 源 {expect_tables}")
    if bad_math:
        problems.append(f"{bad_math} 个公式块含思源不兼容写法")
    return info, problems


def save_chapter(base, token, parent_id, md, fallback_title, min_blocks=5):
    """把一章 Markdown 存为 parent_id 的子文档。幂等 + 入库前后格式校验；校验失败自动删除坏文档后报错。"""
    info = doc_info(base, token, parent_id)
    md = clean_markdown(md)
    body = body_from_md(md)
    title = title_from_md(body, fallback_title)
    full_path = info["hpath"].rstrip("/") + "/" + title
    src_issues, src_tables = check_tables(body)
    if src_issues:
        raise RuntimeError("源 Markdown 表格结构有误，拒绝入库: " + "; ".join(src_issues[:5]))

    exist = doc_exists(base, token, info["notebook"], full_path)
    if exist:
        ainfo, problems = audit_doc(base, token, exist[0], expect_tables=src_tables, min_blocks=min_blocks)
        if not problems:
            return {"skipped": True, "doc_id": exist[0], "title": title, "hpath": full_path,
                    "blocks": ainfo["blocks"], "tables": ainfo["tables"]}
        # 已存在的文档格式不合格（历史坏数据）→ 删除重建
        call(base, token, "/api/filetree/removeDocByID", {"id": exist[0]})

    new_id = call(base, token, "/api/filetree/createDocWithMd",
                  {"notebook": info["notebook"], "path": full_path, "markdown": body})
    ainfo, problems = audit_doc(base, token, new_id, expect_tables=src_tables, min_blocks=min_blocks)
    if problems:
        call(base, token, "/api/filetree/removeDocByID", {"id": new_id})
        raise RuntimeError("入库后格式校验失败（坏文档已删除）: " + "; ".join(problems))
    hpath = call(base, token, "/api/filetree/getHPathByID", {"id": new_id})
    call(base, token, "/api/ui/reloadUI", {})
    return {"skipped": False, "doc_id": new_id, "title": title, "hpath": hpath,
            "blocks": ainfo["blocks"], "tables": ainfo["tables"], "chars": len(body)}


def recent_docs(base, token, limit=15):
    rows = call(base, token, "/api/query/sql",
                {"stmt": f"SELECT id, hpath, box, content, updated FROM blocks WHERE type='d' ORDER BY updated DESC LIMIT {limit}"})
    return [{"id": r["id"], "hpath": r["hpath"], "notebook": r["box"], "title": r["content"], "updated": r["updated"]} for r in rows]


def search_docs(base, token, kw, limit=10):
    rows = call(base, token, "/api/query/sql",
                {"stmt": "SELECT id, hpath, box, content FROM blocks WHERE type='d' AND content LIKE " +
                         "'%" + kw.replace("'", "''") + "%' ORDER BY updated DESC LIMIT " + str(limit)})
    return [{"id": r["id"], "hpath": r["hpath"], "notebook": r["box"], "title": r["content"]} for r in rows]


def tree(base, token, parent_id):
    rows = call(base, token, "/api/query/sql",
                {"stmt": "SELECT id, hpath, content FROM blocks WHERE type='d' AND path LIKE '%" + parent_id.replace("'", "''") + "%' ORDER BY hpath LIMIT 50"})
    return rows


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "status"
    base, token = connect()
    if cmd == "status":
        print(json.dumps({"kernel": base}, ensure_ascii=False))
    elif cmd == "find":
        print(json.dumps(search_docs(base, token, a[1]), ensure_ascii=False, indent=1))
    elif cmd == "recent":
        print(json.dumps(recent_docs(base, token), ensure_ascii=False, indent=1))
    elif cmd == "create":
        r = call(base, token, "/api/filetree/createDocWithMd", {"notebook": a[1], "path": a[2], "markdown": ""})
        call(base, token, "/api/ui/reloadUI", {})
        print(json.dumps({"doc_id": r}, ensure_ascii=False))
    elif cmd == "save":
        md = open(a[1], encoding="utf-8-sig").read()
        parent = a[a.index("--parent-id") + 1]
        fb = a[a.index("--fallback") + 1] if "--fallback" in a else "未命名章节"
        print(json.dumps(save_chapter(base, token, parent, md, fb), ensure_ascii=False))
    elif cmd == "tree":
        print(json.dumps(tree(base, token, a[1]), ensure_ascii=False, indent=1))
    else:
        raise SystemExit(f"未知命令 {cmd}（status|find|recent|create|save|tree）")


if __name__ == "__main__":
    main()
