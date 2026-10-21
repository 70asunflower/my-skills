# -*- coding: utf-8 -*-
"""xhs-pipeline：小红书信息收集通用引擎（profile 驱动）。
所有中文参数经 urllib+JSON 传输；打开/关闭笔记用真实点击与 Esc（防 300017 风控）；
坐标现测现用；汇总重建整删整建（Fix B）。

用法（--profile 默认 <skill>/profiles/job.json，可用 --profile 指定其他配置）:
  python pipeline.py check
  python pipeline.py search "<关键词>" --category "<分类名>" [--limit 3]      # 弹窗点击路径（限流时改用 search-tokens）
  python pipeline.py search-tokens "<关键词>" --category "<分类名>" [--limit 3]  # 卡片DOM抽token→整页直开（弹窗限流绕开，X34）
  python pipeline.py fetch-url "<笔记分享链接>" --category "<分类名>" [--keyword 兜底词]   # 单篇直收
  python pipeline.py fetch-profile "<博主主页链接>" --category "<分类名>" [--limit 0]   # 主页整收：SSR抽token逐篇直开（X33）
  python pipeline.py review / prep-images / clean-staging
  python pipeline.py merge-q  --category "<分类名>" --file <题目.json>
  python pipeline.py merge-jobs --category "<分类名>" --file <岗位.json>
  python pipeline.py collect-current                       # 抓当前打开帖子的评论
  python pipeline.py collect-search --keyword <关键词> --limit 3   # 搜索并批量抓评论
  python pipeline.py merge-tips                            # 重建《实用tips收藏》
"""
import argparse, json, os, random, re, shutil, sys, tempfile, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\qilin\.zcode\skills\ai-tutorial-pipeline\scripts")
import wb
import siyuan
from wb import wb as call_wb  # wb 是模块，wb.wb 才是请求函数

SKILL_DIR = Path(__file__).resolve().parent.parent

# 广告/诱饵识别：强特征命中一个即判广告；弱特征命中两个判广告
AD_STRONG = ["卖资料", "出售资料", "出资料", "资料包", "付费", "收费", "淘宝", "闲鱼", "拍下",
             "训练营", "保过", "一对一辅导", "简历修改", "简历优化", "付费咨询", "加微信", "加V",
             "加v", "＋V", "扫码", "私聊领取", "私信领取", "评论区扣", "扣1", "扣个1", "dd我", "滴滴我"]
AD_WEAK = ["课程", "9.9", "19.9", "29.9", "99元", "资料", "内部渠道", "保证offer", "全程班", "真题出售"]
EXP_HINTS = ["面经", "一面", "二面", "三面", "hr面", "HR面", "问了", "被问", "提问", "手撕", "拷打",
             "复盘", "上岸", "oc", "OC", "offer", "秋招", "春招", "实习", "校招", "笔试", "面试",
             "回忆", "记录", "准备", "基础", "项目"]

ESC = ({"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
       {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------- profile ----------
def load_profile(profile_path):
    p = Path(profile_path).resolve()
    prof = json.loads(p.read_text(encoding="utf-8-sig"))
    prof["_path"] = str(p)
    if not prof.get("session"):
        prof["session"] = "xhs-" + prof.get("name", "pipe")
    sd = prof.get("staging_dir") or str(Path(tempfile.gettempdir()) / f"xhs_staging_{prof.get('name', 'pipe')}")
    prof["_staging"] = Path(sd)  # 目录懒创建（仅 search 需要），绝不落在 skill 目录内
    cats = {}
    for c in prof.get("categories", []):
        if not c.get("name"):
            raise SystemExit("profile 的 categories 项缺少 name 字段")
        cats[c["name"]] = c
    prof["_cats"] = cats
    return prof


def cat_conf(prof, name):
    c = prof["_cats"].get(name)
    if not c:
        raise SystemExit(f"profile 里没有分类「{name}」，现有：{list(prof['_cats'])}")
    return c


# ---------- 浏览器基础 ----------
def ensure_page(prof, session):
    site = prof.get("site", "https://www.xiaohongshu.com")
    # 先找本会话的标签页，再借用用户正在看的，最后才开新页；全部容错处理
    for kwargs in ({}, {"active": True}):
        try:
            t = call_wb("find_tab", {"url": site, **kwargs}, session=session)
            if t.get("ok") and (t.get("data") or {}).get("success"):
                return
        except Exception:
            continue
    try:
        call_wb("navigate", {"url": site, "newTab": True, "group_title": prof.get("group_title", "xhs 收集")}, session=session)
    except Exception as e:
        raise RuntimeError(f"无法在小红书打开标签页（浏览器/扩展是否就绪）: {e}")
    time.sleep(3)
    current_url(session)  # 可达性探测（失败会抛错给上层）


def login_ok(session):
    r = call_wb("evaluate", {"code": "JSON.stringify({modal: !!document.querySelector('.login-container, .login-modal')})"}, session=session)
    try:
        d = json.loads((r.get("data") or {}).get("value") or "{}")
    except Exception:
        d = {}
    if d.get("modal"):
        return False, "检测到登录弹窗"
    return True, "未见登录弹窗（登录 cookie 多为 httpOnly，探测不到属正常）"


def modal_open(session):
    r = call_wb("evaluate", {"code": "JSON.stringify({open: !!document.querySelector('#detail-title')})"}, session=session)
    try:
        return json.loads((r.get("data") or {}).get("value") or "{}").get("open", False)
    except Exception:
        return False


def close_note(session):
    """关闭笔记弹窗并验证。实测关闭按钮的 CDP 点击经常无效，Esc 优先。"""
    for _ in range(2):
        wb.cdp_keys(session, *ESC)
        time.sleep(1.5)
        if not modal_open(session):
            return
    r = call_wb("evaluate", {"code": (
        "(() => { const els=[...document.querySelectorAll('.close-circle, .close-icon, button[class*=\"close\"]')]"
        ".map(e=>{const r=e.getBoundingClientRect(); return {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2), vis:r.width>0&&r.height>0};})"
        ".filter(p=>p.vis && p.x>300 && p.y<200); return JSON.stringify(els); })()")}, session=session)
    cands = json.loads((r.get("data") or {}).get("value") or "[]")
    for c in cands[:2]:
        wb.cdp_click(session, c["x"], c["y"])
        time.sleep(1.5)
        if not modal_open(session):
            return
    raise RuntimeError("弹窗关闭失败，停止以免重复抓取同一篇")


def ensure_modal_closed(session):
    if modal_open(session):
        wb.cdp_keys(session, *ESC)
        time.sleep(1.2)


def risk_blocked(session):
    r = call_wb("evaluate", {"code": "JSON.stringify({captcha: !!document.querySelector('.captcha-container, [class*=captcha]'), loginModal: !!document.querySelector('.login-container, .login-modal'), blocked: (document.body.innerText||'').indexOf('300017') >= 0 || (document.body.innerText||'').indexOf('url is invalid') >= 0})"}, session=session)
    try:
        d = json.loads((r.get("data") or {}).get("value") or "{}")
        return d.get("captcha") or d.get("loginModal") or d.get("blocked")
    except Exception:
        return False


def current_url(session):
    r = call_wb("evaluate", {"code": "location.href"}, session=session)
    return (r.get("data") or {}).get("value") or ""


# ---------- 搜索与抓取 ----------
def do_search(session, keyword):
    """进入搜索结果页：真实搜索框交互为主；验证真的到了搜索结果页。"""
    ensure_modal_closed(session)
    call_wb("navigate", {"url": "https://www.xiaohongshu.com"}, session=session)
    time.sleep(3)
    r = call_wb("evaluate", {"code": (
        "(() => { const e=document.querySelector('input[placeholder*=\"搜索\"]'); if(!e) return 'none';"
        " const r=e.getBoundingClientRect(); return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}); })()")}, session=session)
    raw = (r.get("data") or {}).get("value")
    pos = None
    if raw and raw != "none":
        try:
            pos = json.loads(raw)
        except Exception:
            pos = None
    if pos:
        for _ in range(2):
            wb.cdp_click(session, pos["x"], pos["y"])
            time.sleep(0.8)
            call_wb("cdp", {"method": "Input.insertText", "params": {"text": keyword}}, session=session)
            time.sleep(0.6)
            wb.cdp_keys(session, *wb.ENTER)
            time.sleep(4)
            if "/search_result" in current_url(session):
                break
    if "/search_result" not in current_url(session):
        url = "https://www.xiaohongshu.com/search_result?keyword=" + urllib.parse.quote(keyword) + "&source=web_explore_feed"
        call_wb("navigate", {"url": url}, session=session)
        time.sleep(4)
    cards = visible_cards(session, [])
    if not cards:
        time.sleep(3)
        cards = visible_cards(session, [])
    if not cards and risk_blocked(session):
        raise RuntimeError("search_blocked: 搜索页被风控拦截（300017/验证码/登录弹窗）")
    return cards


def visible_cards(session, exclude_keywords):
    """当前视口内、有标题、坐标有效的卡片；标题命中 exclude_keywords 的直接跳过（不计入任何计数）。"""
    code = """
      (() => { const out = [];
        document.querySelectorAll('section.note-item').forEach((card) => {
          const tEl = card.querySelector('.title, a.title, .note-text');
          const title = (tEl?.innerText || '').trim();
          if (!title) return;
          const r = card.getBoundingClientRect();
          const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
          if (cx <= 0 || r.width < 50) return;
          if (cy <= 80 || cy > window.innerHeight - 40) return;
          const clickY = Math.max(Math.round(r.y + 40), Math.min(cy, Math.round(r.y + 150)));
          if (clickY >= window.innerHeight - 10) return;
          const aEl = card.querySelector('a[href*="/explore/"], a[href*="/discovery/item/"], a[href]');
          const href = aEl?.getAttribute('href') || '';
          out.push({title: title.slice(0, 80), x: cx, y: clickY, href});
        });
        return JSON.stringify(out);
      })()
    """
    r = call_wb("evaluate", {"code": code}, session=session)
    raw = (r.get("data") or {}).get("value") or "[]"
    try:
        cards = json.loads(raw)
    except Exception:
        cards = []
    if exclude_keywords:
        cards = [c for c in cards if not any(k in c["title"] for k in exclude_keywords)]
    return cards


def extract_note(session, collect_comments=True):
    code = """
      (() => {
        const g = (sels) => { for (const s of sels) { const e = document.querySelector(s); if (e) return e; } return null; };
        const title = g(['#detail-title', '.title', 'h1'])?.innerText?.trim() || '';
        const desc = g(['#detail-desc', '.desc', '.note-text'])?.innerText?.trim() || '';
        const author = g(['.author-container .username', '.username', '.name'])?.innerText?.trim() || '';
        const date = g(['.bottom-container .date', '.date'])?.innerText?.trim() || '';
        const likes = g(['.like-wrapper .count', '.interact-container .count', '.count'])?.innerText?.trim() || '';
        const isVideo = !!document.querySelector('.player-container, video');
        const imgs = [...document.querySelectorAll('.media-container img, .swiper-slide img, .note-detail img')]
          .map(i => i.src || i.getAttribute('data-src') || '')
          .filter(u => u.includes('xhscdn') && !u.includes('avatar') && !u.includes('logo'));
        const comments = COLLECT_COMMENTS ? [...document.querySelectorAll('.comments-container .comment-item, .comment-item')]
          .map(c => ({
            author: c.querySelector('.author .name, .name')?.innerText?.trim() || '',
            text: c.querySelector('.content .note-text, .note-text')?.innerText?.trim() || ''
          }))
          .filter(c => c.text)
          .slice(0, 40) : [];
        return JSON.stringify({title, desc, author, date, likes, url: location.href, isVideo, images: imgs, comments});
      })()
    """.replace("COLLECT_COMMENTS", "true" if collect_comments else "false")
    r = call_wb("evaluate", {"code": code}, session=session)
    raw = (r.get("data") or {}).get("value")
    if not raw:
        return None
    try:
        d = json.loads(raw)
    except Exception:
        return None
    if not (d.get("desc") or d.get("title")):
        return None
    # 只有标题、无正文无图无视频 = 弹窗没打开、在搜索页上抓到了卡片标题（2026-09-05 快手/瑞芯微死循环根因），按提取失败处理走重试
    if not d.get("desc") and not d.get("images") and not d.get("isVideo"):
        return None
    return d


def sniff_ext(data):
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    return ".bin"


def fetch_image(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.xiaohongshu.com/"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def classify_note(note):
    text = (note.get("title") or "") + "\n" + (note.get("desc") or "")
    strong = [p for p in AD_STRONG if p in text]
    weak = [p for p in AD_WEAK if p in text]
    exp = [p for p in EXP_HINTS if p in text]
    if len(strong) >= 1 or len(weak) >= 2:
        return "ad", {"strong": strong, "weak": weak, "exp": exp}
    return "ok", {"exp": exp}


def fold_question_items(base, token, doc_id):
    """给题卡列表项设置 fold=1（SQL 一次取全部列表项，Python 筛题卡，逐项设置）。
    注意：blocks.content 会剥掉 markdown 标记（无 **），本版本无 batch/setBlockAttrs 端点（404），
    新建文档的块索引有滞后——需轮询等待。"""
    deadline = time.time() + 15
    rows, last_n = [], -1
    while time.time() < deadline:
        rows = siyuan.call(base, token, "/api/query/sql",
                           {"stmt": f"SELECT id, content FROM blocks WHERE root_id='{doc_id}' AND type='i' LIMIT 5000"}) or []
        # 块索引是逐步写入的：等到数量连续两轮不变才认为同步完成，否则大文档会漏折后半部分题卡
        if rows and len(rows) == last_n:
            break
        last_n = len(rows)
        time.sleep(1)
    qids = []
    for r in rows:
        c = (r.get("content") or "").strip()
        if re.search(r"Q\d+[.．]", c) and not c.startswith(("🧭", "🎯", "🔑", "✅", "🔭")):
            qids.append(r["id"])
    for i in qids:
        siyuan.call(base, token, "/api/attr/setBlockAttrs", {"id": i, "attrs": {"fold": "1"}})
    return len(qids)


def normalize_q(q):
    """题目规范化：去编号/来源标注（贪心到行尾）/空白/标点，小写——用于跨帖去重。"""
    q = re.sub(r"^[\s\-\*•·]+\d*[\.、\)．]?\s*", "", q.strip())
    q = re.sub(r"（来源：.*）", "", q)
    q = re.sub(r"[\s，。,．?？!！：:；;（）()\[\]【】\"'「」…·]", "", q).lower()
    return q


# ---------- 命令 ----------
def cmd_check(prof, session):
    ensure_page(prof, session)
    ok, why = login_ok(session)
    base, token = siyuan.connect()
    out = {"bridge": "ok", "xhs_login": ok, "xhs_login_why": why, "kernel": base,
           "profile": prof.get("name"), "categories": {}}
    for name, conf in prof["_cats"].items():
        try:
            info = siyuan.doc_info(base, token, conf["subpage_id"])
            out["categories"][name] = {"id": conf["subpage_id"], "hpath": info["hpath"],
                                       "question_bank": conf.get("question_bank", False),
                                       "jobs": conf.get("jobs", False)}
        except Exception as e:
            out["categories"][name] = {"id": conf.get("subpage_id"), "error": str(e)[:80]}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not ok:
        sys.exit(2)


def note_id(href_or_url):
    """从小红书链接里取笔记 id；取不到返回 None（如搜索页链接）。"""
    m = re.search(r"/(?:explore|discovery/item)/([0-9a-f]{10,})", href_or_url or "")
    return m.group(1) if m else None


def cmd_search(prof, session, keyword, cat_name, limit):
    conf = cat_conf(prof, cat_name)
    exclude = conf.get("exclude_title_keywords", [])
    wb.ensure_daemon()
    ensure_page(prof, session)
    ok, why = login_ok(session)
    if not ok:
        print(json.dumps({"error": "未登录: " + why}, ensure_ascii=False))
        sys.exit(2)
    prof["_staging"].mkdir(parents=True, exist_ok=True)  # 仅 search 懒创建暂存目录
    staging = prof["_staging"]
    # 跨关键词去重 manifest：本次收集会话内已处理过的笔记 id 不再重复点开（clean-staging 时一并删除）
    manifest = staging / "_seen.json"
    seen_ids = set()
    if manifest.exists():
        try:
            seen_ids = set(json.loads(manifest.read_text(encoding="utf-8-sig")))
        except Exception:
            seen_ids = set()

    cards = do_search(session, keyword)
    log(f"搜索[{keyword}] 开始，视口内卡片 {len(cards)} 张")
    staged = []
    dups, ads, filtered, fails = 0, 0, 0, 0
    processed, seen_notes = set(), set()
    consec_dups = 0  # 连续命中重复笔记的计数：>=4 熔断，防止同名笔记死循环（2026-09-05 快手/瑞芯微两例）
    stale_rounds = 0
    cards_seen = len(cards)
    slug = re.sub(r"\W+", "", keyword)[:8] or "kw"
    aborted = None
    try:
        while len(staged) < limit:
            if risk_blocked(session):
                aborted = "risk_blocked（登录/验证码/风控错误页）"
                log("!! " + aborted)
                break
            cand = next((c for c in visible_cards(session, exclude) if c["title"] not in processed), None)
            if not cand:
                call_wb("evaluate", {"code": "window.scrollBy(0, Math.max(300, window.innerHeight - 200)); 'ok'"}, session=session)
                time.sleep(2)
                vc = visible_cards(session, exclude)
                cards_seen += len(vc)
                cand = next((c for c in vc if c["title"] not in processed), None)
                if not cand:
                    stale_rounds += 1
                    if stale_rounds >= 3:
                        log("没有更多新卡片，结束")
                        break
                    continue
            stale_rounds = 0
            processed.add(cand["title"])
            nid = note_id(cand.get("href", ""))
            if nid and nid in seen_ids:
                dups += 1
                log(f"已处理过(按笔记id去重)，跳过: {cand['title'][:30]}")
                continue
            note = None
            for attempt in range(2):
                if attempt == 1:
                    # 重试前按标题重新定位卡片（弹窗开关可能引发虚拟化重排，旧坐标不可信）
                    cand2 = next((c for c in visible_cards(session, exclude) if c["title"] == cand["title"]), None)
                    if not cand2:
                        break
                    cand = cand2
                wb.cdp_click(session, cand["x"], cand["y"])
                time.sleep(random.uniform(2.2, 3.0))
                note = extract_note(session)
                if note:
                    break
                close_note(session)
            if not note:
                fails += 1
                log(f"提取失败(已重试): {cand['title'][:30]}")
                if fails >= 5:
                    log("连续提取失败 >=5，疑似触发内容限流（弹窗无内容），熔断结束本关键词，稍后重跑")
                    break
                continue
            note["title"] = note["title"] or cand["title"]
            nid = nid or note_id(note.get("url", ""))
            if nid:
                seen_ids.add(nid)
            note_key = re.sub(r"\s+", "", note["title"])[:20]
            if note_key in seen_notes:
                dups += 1
                consec_dups += 1
                log(f"同一篇重复弹出，关闭跳过: {note['title'][:30]}")
                close_note(session)
                if consec_dups >= 4:
                    log("连续 4 次命中重复笔记，熔断结束本关键词（搜索结果多为已见内容）")
                    break
                continue
            consec_dups = 0
            seen_notes.add(note_key)
            verdict, hits = classify_note(note)
            if verdict == "ad":
                ads += 1
                log(f"广告/诱饵跳过: {note['title'][:30]} | 命中 {hits.get('strong') or hits.get('weak')}")
                close_note(session)
                continue
            if exclude and any(k in (note.get("title", "") + note.get("desc", ""))[:200] for k in exclude):
                filtered += 1
                log(f"分类过滤跳过: {note['title'][:30]}")
                close_note(session)
                continue
            # 每篇笔记一个统一 uid：图片与 JSON 同名不同后缀，避免时间戳差 1 秒导致对不上（2026-09-05 实测坑）
            uid = f"{slug}_{int(time.time())}_{len(staged)}"
            img_files, img_failed = [], 0
            with ThreadPoolExecutor(max_workers=4) as pool:
                def _dl(iu):
                    i, u = iu
                    try:
                        data = fetch_image(u)
                        fp = staging / f"{uid}_img{i}{sniff_ext(data)}"
                        fp.write_bytes(data)
                        return str(fp)
                    except Exception:
                        return None
                results = list(pool.map(_dl, enumerate(note.get("images", []))))
            img_failed = sum(1 for r in results if r is None)
            img_files = [r for r in results if r]
            if img_failed:
                log(f"!! {img_failed} 张图片下载失败（笔记其余内容不受影响）: {note['title'][:30]}")
            comments = note.get("comments", [])
            kept = [c for c in comments if (c.get("author") == note.get("author")) or len(c.get("text", "")) >= 15 or "？" in c.get("text", "") or "?" in c.get("text", "")]
            note["comments"] = kept
            note["comments_dropped"] = len(comments) - len(kept)
            note["images"] = img_files
            note["images_failed"] = img_failed
            note["keyword"] = keyword
            note["category"] = cat_name
            note["note_id"] = nid
            note["captured_at"] = time.strftime("%Y-%m-%d %H:%M")
            sf = staging / f"{uid}.json"
            sf.write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
            staged.append({"staging": str(sf), "title": note["title"][:50],
                           "desc_preview": (note.get("desc") or "")[:100].replace("\n", " "),
                           "author": note.get("author"), "date": note.get("date"),
                           "likes": note.get("likes"), "images": img_files,
                           "comments": len(kept), "exp_signals": hits.get("exp", [])[:6]})
            log(f"暂存: {note['title'][:36]} 图片{len(img_files)}张 评论{len(kept)}条")
            close_note(session)
    except Exception as e:
        aborted = f"{type(e).__name__}: {str(e)[:150]}"
        log(f"!! 异常中止: {aborted}")
    finally:
        try:
            manifest.write_text(json.dumps(sorted(seen_ids), ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        print(json.dumps({"keyword": keyword, "category": cat_name, "cards_seen": cards_seen,
                          "staged": staged, "dups": dups, "ads_skipped": ads,
                          "filtered": filtered, "fails": fails, "aborted": aborted},
                         ensure_ascii=False, indent=1))
    if aborted:
        sys.exit(1)


def cmd_review(prof):
    sd = prof["_staging"]
    out = []
    for f in sorted(sd.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        desc = (d.get("desc") or "").strip()
        it = (d.get("image_text") or "").strip()
        out.append({"staging": str(f), "title": (d.get("title") or "")[:50],
                    "category": d.get("category"),
                    "desc_chars": len(desc),
                    "desc_preview": desc[:80].replace("\n", " "),
                    "images": len(d.get("images", [])), "image_text_chars": len(it),
                    "comments": len(d.get("comments", [])),
                    "needs_image_read": bool(d.get("images")) and len(desc) < 100 and not it})
    print(json.dumps({"count": len(out), "staging_dir": str(sd), "items": out}, ensure_ascii=False, indent=1))


def cmd_clean_staging(prof):
    sd = prof["_staging"]
    n = 0
    for pat in ("*.json", "*.jpg", "*.jpeg", "*.webp", "*.png", "*.bin"):
        for f in sd.glob(pat):
            f.unlink()
            n += 1
    conv = sd / "conv"
    if conv.is_dir():
        shutil.rmtree(conv, ignore_errors=True)
    print(json.dumps({"deleted": n, "dir": str(sd)}, ensure_ascii=False))


def cmd_prep_images(prof, max_px=1400):
    """把暂存图片转压成 ≤max_px 的 JPG（conv/ 子目录），供模型 Read 读图（大 webp 会超图片预算）。
    同时核对各暂存 JSON 引用的图片是否都在磁盘上（images_failed/命名错位排查）。"""
    sd = prof["_staging"]
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("需要 Pillow：pip install pillow")
    conv = sd / "conv"
    conv.mkdir(exist_ok=True)
    converted, missing = 0, []
    for f in sorted(sd.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        for p in d.get("images", []):
            src = Path(p)
            if not src.exists():
                missing.append(str(src))
                continue
            out = conv / (src.stem + ".jpg")
            if out.exists():
                continue
            try:
                im = Image.open(src).convert("RGB")
                w, h = im.size
                if max(w, h) > max_px:
                    r = max_px / max(w, h)
                    im = im.resize((int(w * r), int(h * r)))
                im.save(out, "JPEG", quality=72)
                converted += 1
            except Exception as e:
                missing.append(f"{src} ({e})")
    print(json.dumps({"converted": converted, "missing_or_failed": missing,
                      "conv_dir": str(conv)}, ensure_ascii=False, indent=1))


# ---------- 汇总 ----------
def fold_question_items(base, token, doc_id):
    """给题卡列表项设置 fold=1（SQL 一次取全部列表项，Python 筛题卡，逐项设置）。
    注意：blocks.content 会剥掉 markdown 标记（无 **），本版本无 batch/setBlockAttrs 端点（404），
    新建文档的块索引有滞后——需轮询等待。"""
    deadline = time.time() + 15
    rows, last_n = [], -1
    while time.time() < deadline:
        rows = siyuan.call(base, token, "/api/query/sql",
                           {"stmt": f"SELECT id, content FROM blocks WHERE root_id='{doc_id}' AND type='i' LIMIT 5000"}) or []
        # 块索引是逐步写入的：等到数量连续两轮不变才认为同步完成，否则大文档会漏折后半部分题卡
        if rows and len(rows) == last_n:
            break
        last_n = len(rows)
        time.sleep(1)
    qids = []
    for r in rows:
        c = (r.get("content") or "").strip()
        if re.search(r"Q\d+[.．]", c) and not c.startswith(("🧭", "🎯", "🔑", "✅", "🔭")):
            qids.append(r["id"])
    for i in qids:
        siyuan.call(base, token, "/api/attr/setBlockAttrs", {"id": i, "attrs": {"fold": "1"}})
    return len(qids)


def normalize_q(q):
    """题目规范化：去编号/来源标注（贪心到行尾）/空白/标点，小写——用于跨帖去重。"""
    q = re.sub(r"^[\s\-\*•·]+\d*[\.、\)．]?\s*", "", q.strip())
    q = re.sub(r"（来源：.*）", "", q)
    q = re.sub(r"[\s，。,．?？!！：:；;（）()\[\]【】\"'「」…·]", "", q).lower()
    return q


def cmd_merge_q(prof, cat_name, qfile):
    """从累计题目 JSON 全量重建《题目汇总（按知识类型）》。
    累计 JSON 是唯一事实来源（含答案），新增题目由模型在文件层去重后追加；
    本命令做文件内去重 → 整删整建 → 折叠 → 读回校验。"""
    conf = cat_conf(prof, cat_name)
    data = json.loads(Path(qfile).read_text(encoding="utf-8-sig"))

    items, order, existing = {}, [], set()
    qnum = 0
    added = skipped = invalid = 0
    for it in data.get("items", []):
        q = re.sub(r"\s+", " ", str(it.get("q", ""))).strip()
        t = str(it.get("type", "")).strip()
        qn = normalize_q(q) if q else ""
        if not qn or not t:
            invalid += 1
            continue
        if qn in existing:
            skipped += 1
            continue
        if t not in items:
            items[t] = []
            order.append(t)
        a = it.get("a") or {}
        fields = [("🧭 思路", "思路"), ("🎯 考查", "考查"), ("🔑 关键词", "关键词"),
                  ("✅ 解答", "解答"), ("🔭 拓展", "拓展")]
        sub = []
        for label, key in fields:
            v = re.sub(r"\s*\n\s*", "；", str(a.get(key, ""))).strip()  # 多行答案会破坏列表结构，压成一行
            if v:
                sub.append(f"  - {label}：{v}")
        qnum += 1
        items[t].append((qn, qnum, f"**Q{qnum}. {q}**" + ("\n" + "\n".join(sub) if sub else "")))
        existing.add(qn)
        added += 1

    parts = ["> 面试题按知识类型汇总（题卡制：题目默认折叠，点开看思路/考查/关键词/解答/拓展）。", ""]
    total = 0
    for t in order:
        if not items.get(t):
            continue
        parts.append(f"## {t}")
        for _, _, line in items[t]:
            parts.append(f"- {line}")
            total += 1
        parts.append("")
    md2 = "\n".join(parts).strip() + "\n"

    # Tripwire：0 条有效条目时中止，防止错误文件清空线上汇总
    if total == 0:
        raise SystemExit("输入 0 条有效条目，中止以免清空汇总（检查 --file 是否指向累计题目 JSON）")

    base, token = siyuan.connect()
    info = siyuan.doc_info(base, token, conf["subpage_id"])
    sum_path = info["hpath"].rstrip("/") + "/题目汇总（按知识类型）"

    # Fix B（整删整建）：先删同路径全部旧文档并轮询确认索引清空，再建新文档；
    # 创建后再轮询确认新 id 已进索引（防止背靠背合并看到假空而重复建页）。
    exist_ids = list(siyuan.doc_exists(base, token, info["notebook"], sum_path) or [])
    for did in exist_ids:
        try:
            siyuan.call(base, token, "/api/filetree/removeDocByID", {"id": did})
        except Exception:
            pass  # 旧 id 可能已被删（索引滞后），由下方空置轮询兜底
    deadline = time.time() + 10
    while time.time() < deadline:
        if not siyuan.doc_exists(base, token, info["notebook"], sum_path):
            break
        time.sleep(0.5)
    doc_id = siyuan.call(base, token, "/api/filetree/createDocWithMd",
                         {"notebook": info["notebook"], "path": sum_path, "markdown": md2})
    folded = fold_question_items(base, token, doc_id)
    deadline = time.time() + 10
    confirmed = False
    while time.time() < deadline:
        if doc_id in (siyuan.doc_exists(base, token, info["notebook"], sum_path) or []):
            confirmed = True
            break
        time.sleep(0.5)
    exp2 = siyuan.call(base, token, "/api/export/exportMdContent", {"id": doc_id})
    got = sum(1 for l in ((exp2 or {}).get("content", "")).split("\n") if l.startswith("- "))
    siyuan.call(base, token, "/api/ui/reloadUI", {})
    ok = confirmed and (got >= total) and got > 0
    print(json.dumps({"added": added, "skipped_dup": skipped, "invalid": invalid, "total_questions": total,
                      "folded": folded, "verify_lines": got, "create_confirmed": confirmed,
                      "ok": ok, "doc_id": doc_id, "path": sum_path},
                     ensure_ascii=False))
    if not ok:
        sys.exit(5)


def cmd_merge_jobs(prof, cat_name, jfile):
    """从累计岗位 JSON 全量重建《岗位汇总》单页（按收录日期分组，按笔记 id 去重，链接保留）。"""
    conf = cat_conf(prof, cat_name)
    data = json.loads(Path(jfile).read_text(encoding="utf-8-sig"))

    lines_by_date, order, existing_ids = {}, [], set()
    today = time.strftime("%Y-%m-%d")
    added = skipped = invalid = 0
    for it in data.get("items", []):
        title = re.sub(r"\s+", " ", str(it.get("title", ""))).strip().replace("/", "／")[:60]
        summary = re.sub(r"\s+", " ", str(it.get("summary", ""))).strip()
        url = str(it.get("url", "")).strip()
        if not title or not summary:
            invalid += 1
            continue
        nid = (re.search(r"([0-9a-fA-F]{24})", url) or [None, ""])[1]
        if nid and nid in existing_ids:
            skipped += 1
            continue
        date = re.sub(r"\s+", " ", str(it.get("date") or today)).strip() or today
        if date not in lines_by_date:
            order.append(date)
            lines_by_date[date] = []
        safe_url = url.replace("(", "%28").replace(")", "%29").replace(" ", "%20")
        line = f"**{title}**：{summary}" + (f"（[原帖]({safe_url})）" if url else "")
        lines_by_date[date].append(line)
        if nid:
            existing_ids.add(nid)
        added += 1

    parts = ["> 收集的岗位信息汇总（按收录日期分组，自动按笔记 id 去重）。", ""]
    total = 0
    for d in order:
        if not lines_by_date.get(d):
            continue
        parts.append(f"## {d}")
        for l in lines_by_date[d]:
            parts.append(f"- {l}")
            total += 1
        parts.append("")
    md2 = "\n".join(parts).strip() + "\n"

    # Tripwire：0 条有效条目时中止，防止错误文件清空线上汇总
    if total == 0:
        raise SystemExit("输入 0 条有效岗位，中止以免清空汇总（检查 --file 是否指向累计岗位 JSON）")

    base, token = siyuan.connect()
    info = siyuan.doc_info(base, token, conf["subpage_id"])
    sum_path = info["hpath"].rstrip("/") + "/岗位汇总"

    # Fix B（整删整建）：删同路径全部旧文档 → 轮询确认清空 → 创建 → 轮询确认新 id 进索引
    exist_ids = list(siyuan.doc_exists(base, token, info["notebook"], sum_path) or [])
    for did in exist_ids:
        try:
            siyuan.call(base, token, "/api/filetree/removeDocByID", {"id": did})
        except Exception:
            pass
    deadline = time.time() + 10
    while time.time() < deadline:
        if not siyuan.doc_exists(base, token, info["notebook"], sum_path):
            break
        time.sleep(0.5)
    doc_id = siyuan.call(base, token, "/api/filetree/createDocWithMd",
                         {"notebook": info["notebook"], "path": sum_path, "markdown": md2})
    deadline = time.time() + 10
    confirmed = False
    while time.time() < deadline:
        if doc_id in (siyuan.doc_exists(base, token, info["notebook"], sum_path) or []):
            confirmed = True
            break
        time.sleep(0.5)
    exp2 = siyuan.call(base, token, "/api/export/exportMdContent", {"id": doc_id})
    got = sum(1 for l in ((exp2 or {}).get("content", "")).split("\n") if l.startswith("- "))
    siyuan.call(base, token, "/api/ui/reloadUI", {})
    ok = confirmed and (got == total) and got > 0
    print(json.dumps({"added": added, "skipped_dup": skipped, "invalid": invalid, "total_entries": total,
                      "verify_lines": got, "create_confirmed": confirmed,
                      "ok": ok, "doc_id": doc_id, "path": sum_path}, ensure_ascii=False))
    if not ok:
        sys.exit(5)


def cmd_check(prof, session):
    ensure_page(prof, session)
    ok, why = login_ok(session)
    base, token = siyuan.connect()
    out = {"bridge": "ok", "xhs_login": ok, "xhs_login_why": why, "kernel": base,
           "profile": prof.get("name"), "categories": {}}
    for name, conf in prof["_cats"].items():
        try:
            info = siyuan.doc_info(base, token, conf["subpage_id"])
            out["categories"][name] = {"id": conf["subpage_id"], "hpath": info["hpath"],
                                       "question_bank": conf.get("question_bank", False),
                                       "jobs": conf.get("jobs", False)}
        except Exception as e:
            out["categories"][name] = {"id": conf.get("subpage_id"), "error": str(e)[:80]}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not ok:
        sys.exit(2)


# ---------- 评论收集工作流（金句/神评论） ----------
def parse_likes(s):
    s = (s or "").strip()
    m = re.match(r"([\d.]+)万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    return int(s) if s.isdigit() else 0


def scrape_comments(session, rounds=3):
    """抓当前页面可见评论，并滚动评论区加载更多；按文本去重。"""
    js = """
      (() => {
        const items = [...document.querySelectorAll('.comment-item')];
        const out = items.map(c => ({
          author: c.querySelector('.author .name, .name')?.innerText?.trim() || '',
          text: c.querySelector('.content .note-text, .note-text')?.innerText?.trim() || '',
          likes: c.querySelector('.like .count, .like-wrapper .count')?.innerText?.trim() || '',
          date: c.querySelector('.date')?.innerText?.trim() || '',
          badge: (c.innerText || '').includes('作者赞过') ? 1 : 0
        })).filter(c => c.text);
        const sc = [...document.querySelectorAll('*')].find(e =>
          e.scrollHeight > e.clientHeight + 100 && e.clientHeight > 200 &&
          String(e.className).includes('comment'));
        if (sc) sc.scrollTop += Math.round(sc.clientHeight * 0.9);
        return JSON.stringify(out);
      })()
    """
    seen, all_c = set(), []
    for _ in range(rounds):
        r = call_wb("evaluate", {"code": js}, session=session)
        raw = (r.get("data") or {}).get("value") or "[]"
        try:
            batch = json.loads(raw)
        except Exception:
            batch = []
        for c in batch:
            key = c["text"][:60]
            if key in seen:
                continue
            seen.add(key)
            all_c.append(c)
        time.sleep(1.2)
    return all_c


def _comments_store(prof):
    store_f = Path(prof["work_dir"]) / "comments.json"
    store_f.parent.mkdir(parents=True, exist_ok=True)
    store = json.loads(store_f.read_text(encoding="utf-8")) if store_f.exists() else {"posts": []}
    return store_f, store


def cmd_collect_current(prof, session):
    """抓取用户当前正在查看的帖子的高赞评论（借用当前标签页，不导航）。"""
    wb.ensure_daemon()
    t = call_wb("find_tab", {"url": "https://www.xiaohongshu.com", "active": True}, session=session)
    if not (t.get("ok") and (t.get("data") or {}).get("success")):
        print(json.dumps({"error": "请在 Edge 里打开你想收集的帖子后再试"}, ensure_ascii=False))
        sys.exit(2)
    comments = scrape_comments(session)
    r = call_wb("evaluate", {"code": "document.title.replace(/ - 小红书$/, '')"}, session=session)
    title = ((r.get("data") or {}).get("value") or "")[:60]
    url = current_url(session)
    pid = (re.search(r"([0-9a-f]{24})", url) or [None, title[:24]])[1]
    store_f, store = _comments_store(prof)
    hit = next((p for p in store["posts"] if p.get("id") == pid), None)
    if hit:
        have = {c["text"][:60] for c in hit["comments"]}
        new = [c for c in comments if c["text"][:60] not in have]
        hit["comments"].extend(new)
        store_f.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"status": "updated", "title": title, "comments_added": len(new),
                          "comments_total": len(hit["comments"])}, ensure_ascii=False))
    else:
        post = {"id": pid, "title": title, "url": url, "comments": comments,
                "collected_at": time.strftime("%Y-%m-%d %H:%M")}
        store["posts"].append(post)
        store_f.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"status": "new", "title": title, "comments": len(comments)}, ensure_ascii=False))


def cmd_collect_search(prof, session, keyword, limit):
    wb.ensure_daemon()
    ensure_page(prof, session)
    ok, why = login_ok(session)
    if not ok:
        print(json.dumps({"error": "未登录: " + why}, ensure_ascii=False))
        sys.exit(2)
    cards = do_search(session, keyword)
    log(f"搜索[{keyword}] 视口内卡片 {len(cards)} 张")
    collected = []
    store_f, store = _comments_store(prof)
    for idx, c in enumerate(cards):
        if idx >= limit:
            break
        if risk_blocked(session):
            log("!! 风控拦截，停止")
            break
        wb.cdp_click(session, c["x"], c["y"])
        time.sleep(random.uniform(2.2, 3.0))
        comments = scrape_comments(session)
        r = call_wb("evaluate", {"code": (
            "(document.querySelector('#detail-desc')||document.querySelector('.desc')||{}).innerText?.trim()||''")}, session=session)
        desc = ((r.get("data") or {}).get("value") or "")[:3000]
        if comments or desc:
            url = current_url(session)
            pid = (re.search(r"([0-9a-f]{24})", url) or [None, c["title"][:24]])[1]
            hit = next((p for p in store["posts"] if p.get("id") == pid), None)
            if not hit:
                post = {"id": pid, "title": c["title"], "url": url, "desc": desc, "comments": comments,
                        "collected_at": time.strftime("%Y-%m-%d %H:%M")}
                store["posts"].append(post)
                store_f.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
                collected.append({"title": c["title"][:40], "comments": len(comments), "desc_chars": len(desc)})
                log(f"已收集 正文{len(desc)}字+{len(comments)}条评论: {c['title'][:36]}")
            else:
                if desc and not hit.get("desc"):
                    hit["desc"] = desc
                have = {cm["text"][:60] for cm in hit.get("comments", [])}
                new = [cm for cm in comments if cm["text"][:60] not in have]
                hit.setdefault("comments", []).extend(new)
                store_f.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
                log(f"重复帖子，补正文/评论{len(new)}条: {c['title'][:36]}")
        close_note(session)
    print(json.dumps({"keyword": keyword, "collected": collected, "store_posts": len(store["posts"])},
                     ensure_ascii=False, indent=1))


def cmd_collect_tokens(prof, session, keyword, limit):
    """弹窗限流替代路径（X34）：真实搜索 → 卡片 DOM 抽 (noteId, xsec_token) → 逐篇
    explore 整页直开 → 抓正文 + 滚动加载评论 → 入累计评论库（comments.json）。"""
    wb.ensure_daemon()
    ensure_page(prof, session)
    ok, why = login_ok(session)
    if not ok:
        print(json.dumps({"error": "未登录: " + why}, ensure_ascii=False))
        sys.exit(2)
    cards = do_search(session, keyword)
    pairs = _dom_note_pairs(session)
    log(f"搜索[{keyword}] 卡片{len(cards)}张，DOM 解出 {len(pairs)} 篇带 token")
    store_f, store = _comments_store(prof)
    have_ids = {p.get("id") for p in store["posts"]}
    collected, fails = [], 0
    for nid, meta in pairs.items():
        if len(collected) >= limit:
            break
        if nid in have_ids:
            log(f"重复跳过: {meta['title'][:30]}")
            continue
        note_url = f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={meta['tok']}&xsec_source={meta['src']}"
        call_wb("navigate", {"url": note_url}, session=session)
        time.sleep(random.uniform(4.0, 5.5))
        note = extract_note(session, collect_comments=False)
        if not note:
            time.sleep(2.5)
            note = extract_note(session, collect_comments=False)
        if not note:
            fails += 1
            log(f"提取失败: {meta['title'][:30]}")
            if fails >= 4:
                log("连续提取失败，熔断结束本关键词")
                break
            continue
        comments = scrape_comments(session, rounds=3)
        have_ids.add(nid)
        post = {"id": nid, "title": note.get("title") or meta["title"], "url": note_url,
                "desc": (note.get("desc") or "")[:3000], "author": note.get("author"),
                "likes": note.get("likes"), "comments": comments,
                "collected_at": time.strftime("%Y-%m-%d %H:%M"), "keyword": keyword}
        store["posts"].append(post)
        store_f.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
        collected.append({"title": post["title"][:40], "desc_chars": len(post["desc"]), "comments": len(comments)})
        log(f"已收集 正文{len(post['desc'])}字+{len(comments)}条评论: {post['title'][:36]}")
    print(json.dumps({"keyword": keyword, "collected": collected, "store_posts": len(store["posts"])},
                     ensure_ascii=False, indent=1))


def cmd_merge_tips(prof):
    """从精选 tips JSON 全量重建《实用tips收藏》单页（按帖子分组）。
    条目只保留内容本身（不写作者/赞数）；tips 来自帖子正文或评论，由模型精选。"""
    tips_file = Path(prof["work_dir"]) / "tips_curated.json"
    if not tips_file.exists():
        raise SystemExit("缺少 tips_curated.json（先由模型精选实用 tips 写入 work_dir）")
    store = json.loads(tips_file.read_text(encoding="utf-8"))
    md = ["> 小红书实用 tips 收藏（按帖子分组，已按实用性精选；只保留内容本身）。", ""]
    total = 0
    seen = set()
    for p in store.get("posts", []):
        tips = [t for t in p.get("tips", []) if t]
        dedup = []
        for t in tips:
            qn = normalize_q(t)
            if qn in seen:
                continue
            seen.add(qn)
            dedup.append(t)
        if not dedup:
            continue
        md.append(f"## {p.get('title', '未命名帖子')}")
        md.append("")
        for t in dedup:
            md.append(f"- {t}")
            total += 1
        md.append("")
    md2 = "\n".join(md).strip() + "\n"
    if total == 0:
        raise SystemExit("精选 tips 为空：先由模型精选实用 tips 写入 tips_curated.json")
    base, token = siyuan.connect()
    # 注意：parent_path 相对笔记本根（不含笔记本名），笔记本 id 不能传给 doc_info
    sum_path = (prof.get("parent_path") or "").rstrip("/") + "/" + prof.get("summary_doc", "实用tips收藏")
    exist_ids = list(siyuan.doc_exists(base, token, prof["notebook"], sum_path) or [])
    for did in exist_ids:
        try:
            siyuan.call(base, token, "/api/filetree/removeDocByID", {"id": did})
        except Exception:
            pass
    deadline = time.time() + 10
    while time.time() < deadline:
        if not siyuan.doc_exists(base, token, prof["notebook"], sum_path):
            break
        time.sleep(0.5)
    doc_id = siyuan.call(base, token, "/api/filetree/createDocWithMd",
                         {"notebook": prof["notebook"], "path": sum_path, "markdown": md2})
    siyuan.call(base, token, "/api/ui/reloadUI", {})
    print(json.dumps({"total_tips": total, "ok": True, "doc_id": doc_id, "path": sum_path}, ensure_ascii=False))


def cmd_fetch_url(prof, session, url, cat_name, fallback_kw=None):
    """按用户分享的笔记链接抓单篇入暂存区（用户直接丢链接时用，不走搜索）。
    优先借用浏览器里已打开的同一笔记标签页（零导航零风控）；否则直接导航分享链接
    （带 xsec_token 的分享链接一般可直开）；触发风控且有 fallback_kw 时回退搜索真实点击。"""
    cat_conf(prof, cat_name)  # 仅校验分类存在
    wb.ensure_daemon()
    ensure_page(prof, session)
    ensure_modal_closed(session)
    nid = note_id(url) or ""
    if nid and nid in current_url(session):
        log("当前标签页已是目标笔记，不导航")
    else:
        call_wb("navigate", {"url": url}, session=session)
        time.sleep(3.5)
        if risk_blocked(session):
            log("!! 直接导航触发风控（300017/验证码）")
            try:
                close_note(session)  # 可能没有笔记弹窗（错误页/信息流），清场即可不强求
            except Exception:
                pass
            if not fallback_kw:
                print(json.dumps({"error": "直连被风控且未提供 --keyword；可在浏览器手动打开该笔记后重跑（会借用已开标签页）"}, ensure_ascii=False))
                sys.exit(2)
            key = re.sub(r"\s+", "", fallback_kw)
            do_search(session, fallback_kw)
            cand = next((c for c in visible_cards(session, []) if key in re.sub(r"\s+", "", c.get("title", ""))), None)
            if not cand:
                print(json.dumps({"error": f"搜索兜底未找到标题含[{fallback_kw}]的卡片"}, ensure_ascii=False))
                sys.exit(3)
            wb.cdp_click(session, cand["x"], cand["y"])
            time.sleep(random.uniform(2.5, 3.2))
    if risk_blocked(session):
        print(json.dumps({"error": "风控拦截（验证码/登录/300017），请人工处理后重试"}, ensure_ascii=False))
        sys.exit(2)
    note = None
    for _ in range(2):
        note = extract_note(session)
        if note:
            break
        time.sleep(2)
    if not note:
        print(json.dumps({"error": "笔记提取失败（弹窗未打开或页面结构变化）", "url": current_url(session)}, ensure_ascii=False))
        sys.exit(4)
    nid = note_id(note.get("url", "")) or nid
    prof["_staging"].mkdir(parents=True, exist_ok=True)
    staging = prof["_staging"]
    uid = f"single_{int(time.time())}_0"
    with ThreadPoolExecutor(max_workers=4) as pool:
        def _dl(iu):
            i, u = iu
            try:
                data = fetch_image(u)
                fp = staging / f"{uid}_img{i}{sniff_ext(data)}"
                fp.write_bytes(data)
                return str(fp)
            except Exception:
                return None
        results = list(pool.map(_dl, enumerate(note.get("images", []))))
    img_files = [r for r in results if r]
    img_failed = sum(1 for r in results if r is None)
    comments = note.get("comments", [])
    kept = [c for c in comments if (c.get("author") == note.get("author")) or len(c.get("text", "")) >= 15 or "？" in c.get("text", "") or "?" in c.get("text", "")]
    note["comments"] = kept
    note["comments_dropped"] = len(comments) - len(kept)
    note["images"] = img_files
    note["images_failed"] = img_failed
    note["keyword"] = "单篇URL(用户分享)"
    note["category"] = cat_name
    note["note_id"] = nid
    note["captured_at"] = time.strftime("%Y-%m-%d %H:%M")
    sf = staging / f"{uid}.json"
    sf.write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
    # 记入 _seen manifest：本会话后续批量搜索跳过该篇
    manifest = staging / "_seen.json"
    try:
        seen_ids = set(json.loads(manifest.read_text(encoding="utf-8-sig")))
    except Exception:
        seen_ids = set()
    if nid:
        seen_ids.add(nid)
    manifest.write_text(json.dumps(sorted(seen_ids), ensure_ascii=False), encoding="utf-8")
    try:
        close_note(session)
    except Exception:
        log("收尾关页失败（fetch-url 直开的笔记整页无弹窗可关，属预期；数据已落盘）")
    print(json.dumps({"staged": str(sf), "title": note["title"], "author": note.get("author"),
                      "date": note.get("date"), "likes": note.get("likes"),
                      "desc_chars": len(note.get("desc", "")), "images": len(img_files),
                      "images_failed": img_failed, "comments": len(kept),
                      "url": note.get("url", "")[:120]}, ensure_ascii=False, indent=1))


def _profile_pairs(session, prof_url, uid):
    """KimiBridge network 捕获主页 SSR 文档体，抽 (noteId, xsec_token) 配对。
    主页卡片数据是 SSR 直出（无运行时 user_posted 请求），每张卡片的链接自带 token：
    /user/profile/<uid>/<noteId>?xsec_token=... —— 拿它逐篇走 explore 整页（fetch-url 已验证的路径）。"""
    call_wb("network", {"cmd": "start"}, session=session)
    call_wb("navigate", {"url": prof_url}, session=session)
    time.sleep(8)
    doc = None
    for _ in range(2):
        lst = call_wb("network", {"cmd": "list"}, session=session)
        reqs = ((lst.get("data") or {}).get("requests")) or []
        doc = next((r for r in reqs if f"user/profile/{uid}" in r.get("url", "")
                    and "text/html" in (r.get("mimeType") or "")), None)
        if doc:
            break
        time.sleep(3)
    if not doc:
        try:
            call_wb("network", {"cmd": "stop"}, session=session)
        except Exception:
            pass
        raise RuntimeError("network 捕获未找到主页文档响应（扩展是否支持 network 工具）")
    det = call_wb("network", {"cmd": "detail", "requestId": doc["requestId"]}, session=session)
    body = (det.get("data") or {}).get("body") or ""
    if not isinstance(body, str):
        body = json.dumps(body, ensure_ascii=False)
    try:
        call_wb("network", {"cmd": "stop"}, session=session)
    except Exception:
        pass
    pairs = {}
    for m in re.finditer(rf'/(?:user/profile/{uid}|explore)/([0-9a-f]{{24}})\?[^"\']*?xsec_token=([^&"\']+)', body):
        nid, tok = m.group(1), m.group(2)
        if nid not in pairs:
            pairs[nid] = tok
    return pairs


def cmd_fetch_profile(prof, session, url, cat_name, limit=0):
    """博主主页整页收集：network 捕获 SSR 拿每篇笔记的 xsec_token → 逐篇 explore 整页导航抓取入暂存。
    主页卡片点击开弹窗的路径在 SPA 下会无声失败（实测 2026-09-30），此路径完全绕开弹窗。
    用法: pipeline.py fetch-profile "<主页URL带xsec_token>" --category <分类名> [--limit 0]"""
    m = re.search(r"/user/profile/([0-9a-f]{24})", url or "")
    if not m:
        raise SystemExit('URL 需是博主主页链接 /user/profile/<uid>?xsec_token=...')
    uid = m.group(1)
    conf = cat_conf(prof, cat_name)
    exclude = conf.get("exclude_title_keywords", [])
    wb.ensure_daemon()
    ensure_page(prof, session)
    ok, why = login_ok(session)
    if not ok:
        print(json.dumps({"error": "未登录: " + why}, ensure_ascii=False))
        sys.exit(2)
    prof["_staging"].mkdir(parents=True, exist_ok=True)
    staging = prof["_staging"]
    manifest = staging / "_seen.json"
    seen_ids = set()
    if manifest.exists():
        try:
            seen_ids = set(json.loads(manifest.read_text(encoding="utf-8-sig")))
        except Exception:
            seen_ids = set()

    log("捕获主页 SSR，抽取笔记 token…")
    pairs = _profile_pairs(session, url, uid)
    if not pairs:
        print(json.dumps({"error": "主页文档体未解出任何 (noteId, token) 配对"}, ensure_ascii=False))
        sys.exit(3)
    log(f"解出 {len(pairs)} 篇笔记，开始逐篇整页抓取")
    staged, dups, ads, filtered, fails = [], 0, 0, 0, 0
    slug = f"prof_{uid[:8]}"
    aborted = None
    try:
        for nid, tok in pairs.items():
            if limit and len(staged) >= limit:
                break
            if risk_blocked(session):
                aborted = "risk_blocked（登录/验证码/风控错误页）"
                log("!! " + aborted)
                break
            if nid in seen_ids:
                dups += 1
                continue
            note_url = f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={tok}&xsec_source=pc_user"
            call_wb("navigate", {"url": note_url}, session=session)
            time.sleep(random.uniform(4.0, 5.5))
            note = extract_note(session)
            if not note:
                time.sleep(2.5)
                note = extract_note(session)
            if not note:
                fails += 1
                log(f"提取失败: {nid[:16]}…（token 失效或内容限流）")
                if fails >= 5:
                    log("连续提取失败 >=5，熔断结束（稍后可用 fetch-url 补漏）")
                    break
                continue
            seen_ids.add(nid)
            verdict, hits = classify_note(note)
            if verdict == "ad":
                ads += 1
                log(f"广告/诱饵跳过: {note['title'][:30]} | 命中 {hits.get('strong') or hits.get('weak')}")
                continue
            if exclude and any(k in (note.get("title", "") + note.get("desc", ""))[:200] for k in exclude):
                filtered += 1
                log(f"分类过滤跳过: {note['title'][:30]}")
                continue
            uid_ = f"{slug}_{int(time.time())}_{len(staged)}"
            with ThreadPoolExecutor(max_workers=4) as pool:
                def _dl(iu):
                    i, u = iu
                    try:
                        data = fetch_image(u)
                        fp = staging / f"{uid_}_img{i}{sniff_ext(data)}"
                        fp.write_bytes(data)
                        return str(fp)
                    except Exception:
                        return None
                results = list(pool.map(_dl, enumerate(note.get("images", []))))
            img_failed = sum(1 for r in results if r is None)
            img_files = [r for r in results if r]
            if img_failed:
                log(f"!! {img_failed} 张图片下载失败: {note['title'][:30]}")
            comments = note.get("comments", [])
            kept = [c for c in comments if (c.get("author") == note.get("author")) or len(c.get("text", "")) >= 15 or "？" in c.get("text", "") or "?" in c.get("text", "")]
            note["comments"] = kept
            note["comments_dropped"] = len(comments) - len(kept)
            note["images"] = img_files
            note["images_failed"] = img_failed
            note["keyword"] = f"博主主页({uid[:8]})"
            note["category"] = cat_name
            note["note_id"] = nid
            note["captured_at"] = time.strftime("%Y-%m-%d %H:%M")
            sf = staging / f"{uid_}.json"
            sf.write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
            staged.append({"staging": str(sf), "title": note["title"][:50],
                           "desc_preview": (note.get("desc") or "")[:100].replace("\n", " "),
                           "author": note.get("author"), "date": note.get("date"),
                           "likes": note.get("likes"), "images": img_files,
                           "comments": len(kept), "exp_signals": hits.get("exp", [])[:6]})
            log(f"暂存: {note['title'][:36]} 图片{len(img_files)}张 评论{len(kept)}条")
    except Exception as e:
        aborted = f"{type(e).__name__}: {str(e)[:150]}"
        log(f"!! 异常中止: {aborted}")
    finally:
        try:
            manifest.write_text(json.dumps(sorted(seen_ids), ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        print(json.dumps({"profile_uid": uid, "notes_found": len(pairs), "staged": staged,
                          "dups": dups, "ads_skipped": ads, "filtered": filtered,
                          "fails": fails, "aborted": aborted}, ensure_ascii=False, indent=1))
    if aborted:
        sys.exit(1)


def _dom_note_pairs(session):
    """从当前搜索结果页 DOM 抽 (noteId → {tok, title})。卡片含多个链接，只有
    /search_result/<id>?xsec_token= 形态带 token（visible_cards 抓到的 /explore 裸链没有）——
    弹窗被限流时，用 token 走 explore 整页直开（X33：弹窗与 SSR 配额分离）。"""
    r = call_wb("evaluate", {"code": """
      (() => {
        const out = [];
        document.querySelectorAll('section.note-item').forEach(card => {
          const tEl = card.querySelector('.title, a.title, .note-text');
          const title = (tEl?.innerText || '').trim();
          let picked = null;
          card.querySelectorAll('a[href]').forEach(a => {
            const h = a.getAttribute('href') || '';
            if (!picked && h.includes('xsec_token=')) picked = h;
          });
          if (picked) out.push({t: title.slice(0, 80), href: picked});
        });
        return JSON.stringify(out);
      })()
    """}, session=session)
    raw = (r.get("data") or {}).get("value") or "[]"
    try:
        items = json.loads(raw)
    except Exception:
        items = []
    pairs = {}
    for it in items:
        m = re.search(r'/(?:search_result|explore|discovery/item)/([0-9a-f]{24})\?[^"\']*?xsec_token=([^&"\']+)', it.get("href", ""))
        if m:
            nid = m.group(1)
            if nid not in pairs:
                src = re.search(r'xsec_source=([^&"\']+)', it.get("href", ""))
                pairs[nid] = {"tok": m.group(2), "title": it.get("t", ""),
                              "src": src.group(1) if src else "pc_search"}
    return pairs


def cmd_search_tokens(prof, session, keyword, cat_name, limit):
    """搜索结果整页直收（弹窗限流时的替代路径）：真实搜索交互拿结果页 → 从卡片 DOM 抽
    (noteId, xsec_token) → 逐篇 explore 整页导航抓取入暂存。卡片不够时回搜索页滚动加载。
    用法: pipeline.py search-tokens "<关键词>" --category <分类名> [--limit 3]"""
    conf = cat_conf(prof, cat_name)
    exclude = conf.get("exclude_title_keywords", [])
    wb.ensure_daemon()
    ensure_page(prof, session)
    ok, why = login_ok(session)
    if not ok:
        print(json.dumps({"error": "未登录: " + why}, ensure_ascii=False))
        sys.exit(2)
    prof["_staging"].mkdir(parents=True, exist_ok=True)
    staging = prof["_staging"]
    manifest = staging / "_seen.json"
    seen_ids = set()
    if manifest.exists():
        try:
            seen_ids = set(json.loads(manifest.read_text(encoding="utf-8-sig")))
        except Exception:
            seen_ids = set()

    cards = do_search(session, keyword)
    pairs = _dom_note_pairs(session)
    log(f"搜索[{keyword}] 视口卡片 {len(cards)} 张，DOM 解出 {len(pairs)} 篇带 token")
    search_url = current_url(session)
    staged, dups, ads, filtered, fails = [], 0, 0, 0, 0
    processed, seen_notes = set(), set()
    stale_rounds = 0
    slug = re.sub(r"\W+", "", keyword)[:8] or "kw"
    aborted = None
    try:
        while len(staged) < limit:
            if risk_blocked(session):
                aborted = "risk_blocked（登录/验证码/风控错误页）"
                log("!! " + aborted)
                break
            cand = next(((nid, v) for nid, v in pairs.items() if nid not in processed), None)
            if not cand:
                if "/search_result" not in current_url(session):
                    call_wb("navigate", {"url": search_url}, session=session)
                    time.sleep(4)
                call_wb("evaluate", {"code": "window.scrollBy(0, Math.max(300, window.innerHeight - 200)); 'ok'"}, session=session)
                time.sleep(2)
                newp = _dom_note_pairs(session)
                added_new = sum(1 for nid in newp if nid not in pairs)
                for nid, v in newp.items():
                    pairs.setdefault(nid, v)
                if not added_new:
                    stale_rounds += 1
                    if stale_rounds >= 3:
                        log("没有更多新卡片，结束")
                        break
                    continue
                stale_rounds = 0
                continue
            nid, meta = cand
            processed.add(nid)
            if nid in seen_ids:
                dups += 1
                log(f"已处理过(笔记id)，跳过: {meta['title'][:30]}")
                continue
            note_url = f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={meta['tok']}&xsec_source={meta['src']}"
            call_wb("navigate", {"url": note_url}, session=session)
            time.sleep(random.uniform(4.0, 5.5))
            note = extract_note(session)
            if not note:
                time.sleep(2.5)
                note = extract_note(session)
            if not note:
                fails += 1
                log(f"提取失败: {meta['title'][:30]}")
                if fails >= 5:
                    log("连续提取失败 >=5，熔断结束本关键词")
                    break
                continue
            seen_ids.add(nid)
            note["title"] = note["title"] or meta["title"]
            note_key = re.sub(r"\s+", "", note["title"])[:20]
            if note_key in seen_notes:
                dups += 1
                log(f"同题重复，跳过: {note['title'][:30]}")
                continue
            seen_notes.add(note_key)
            verdict, hits = classify_note(note)
            if verdict == "ad":
                ads += 1
                log(f"广告/诱饵跳过: {note['title'][:30]} | 命中 {hits.get('strong') or hits.get('weak')}")
                continue
            if exclude and any(k in (note.get("title", "") + note.get("desc", ""))[:200] for k in exclude):
                filtered += 1
                log(f"分类过滤跳过: {note['title'][:30]}")
                continue
            uid_ = f"{slug}_{int(time.time())}_{len(staged)}"
            with ThreadPoolExecutor(max_workers=4) as pool:
                def _dl(iu):
                    i, u = iu
                    try:
                        data = fetch_image(u)
                        fp = staging / f"{uid_}_img{i}{sniff_ext(data)}"
                        fp.write_bytes(data)
                        return str(fp)
                    except Exception:
                        return None
                results = list(pool.map(_dl, enumerate(note.get("images", []))))
            img_failed = sum(1 for r in results if r is None)
            img_files = [r for r in results if r]
            if img_failed:
                log(f"!! {img_failed} 张图片下载失败: {note['title'][:30]}")
            comments = note.get("comments", [])
            kept = [c for c in comments if (c.get("author") == note.get("author")) or len(c.get("text", "")) >= 15 or "？" in c.get("text", "") or "?" in c.get("text", "")]
            note["comments"] = kept
            note["comments_dropped"] = len(comments) - len(kept)
            note["images"] = img_files
            note["images_failed"] = img_failed
            note["keyword"] = keyword
            note["category"] = cat_name
            note["note_id"] = nid
            note["captured_at"] = time.strftime("%Y-%m-%d %H:%M")
            sf = staging / f"{uid_}.json"
            sf.write_text(json.dumps(note, ensure_ascii=False, indent=1), encoding="utf-8")
            staged.append({"staging": str(sf), "title": note["title"][:50],
                           "desc_preview": (note.get("desc") or "")[:100].replace("\n", " "),
                           "author": note.get("author"), "date": note.get("date"),
                           "likes": note.get("likes"), "images": img_files,
                           "comments": len(kept), "exp_signals": hits.get("exp", [])[:6]})
            log(f"暂存: {note['title'][:36]} 图片{len(img_files)}张 评论{len(kept)}条")
    except Exception as e:
        aborted = f"{type(e).__name__}: {str(e)[:150]}"
        log(f"!! 异常中止: {aborted}")
    finally:
        try:
            manifest.write_text(json.dumps(sorted(seen_ids), ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        print(json.dumps({"keyword": keyword, "category": cat_name, "cards_seen": len(cards),
                          "pairs_found": len(pairs), "staged": staged, "dups": dups,
                          "ads_skipped": ads, "filtered": filtered, "fails": fails,
                          "aborted": aborted}, ensure_ascii=False, indent=1))
    if aborted:
        sys.exit(1)


def argval(a, flag):
    if flag not in a:
        return None
    i = a.index(flag)
    if i + 1 >= len(a):
        raise SystemExit(f"{flag} 需要一个值")
    return a[i + 1]


def main():
    a = sys.argv[1:]
    profile = SKILL_DIR / "profiles" / "job.json"
    if "--profile" in a:
        profile = Path(argval(a, "--profile"))
        i = a.index("--profile")
        del a[i:i + 2]
    prof = load_profile(profile)
    session = prof["session"]
    if "--session" in a:
        session = argval(a, "--session")
        i = a.index("--session")
        del a[i:i + 2]
    cmd = a[0] if a else "check"
    if cmd == "check":
        wb.ensure_daemon()
        cmd_check(prof, session)
    elif cmd == "search":
        ap = argparse.ArgumentParser()
        ap.add_argument("keyword")
        ap.add_argument("--category", required=True)
        ap.add_argument("--limit", type=int, default=3)
        args = ap.parse_args(a[1:])
        cmd_search(prof, session, args.keyword, args.category, args.limit)
    elif cmd == "search-tokens":
        ap = argparse.ArgumentParser()
        ap.add_argument("keyword")
        ap.add_argument("--category", required=True)
        ap.add_argument("--limit", type=int, default=3)
        args = ap.parse_args(a[1:])
        cmd_search_tokens(prof, session, args.keyword, args.category, args.limit)
    elif cmd == "review":
        cmd_review(prof)
    elif cmd == "prep-images":
        cmd_prep_images(prof)
    elif cmd == "merge-q":
        cat = argval(a, "--category")
        qf = argval(a, "--file")
        if not cat or not qf:
            raise SystemExit("用法: pipeline.py merge-q --category <分类名> --file <题目.json>")
        cmd_merge_q(prof, cat, qf)
    elif cmd == "merge-jobs":
        cat = argval(a, "--category")
        jf = argval(a, "--file")
        if not cat or not jf:
            raise SystemExit("用法: pipeline.py merge-jobs --category <分类名> --file <岗位.json>")
        cmd_merge_jobs(prof, cat, jf)
    elif cmd == "clean-staging":
        cmd_clean_staging(prof)
    elif cmd == "collect-current":
        wb.ensure_daemon()
        cmd_collect_current(prof, session)
    elif cmd == "collect-search":
        kw = argval(a, "--keyword")
        limit = int(argval(a, "--limit") or 3)
        if not kw:
            raise SystemExit("用法: pipeline.py collect-search --keyword <关键词> --limit 3")
        cmd_collect_search(prof, session, kw, limit)
    elif cmd == "collect-tokens":
        kw = argval(a, "--keyword")
        limit = int(argval(a, "--limit") or 3)
        if not kw:
            raise SystemExit("用法: pipeline.py collect-tokens --keyword <关键词> --limit 3")
        cmd_collect_tokens(prof, session, kw, limit)
    elif cmd == "fetch-url":
        ap = argparse.ArgumentParser()
        ap.add_argument("url")
        ap.add_argument("--category", required=True)
        ap.add_argument("--keyword", default=None)
        args = ap.parse_args(a[1:])
        cmd_fetch_url(prof, session, args.url, args.category, args.keyword)
    elif cmd == "fetch-profile":
        ap = argparse.ArgumentParser()
        ap.add_argument("url")
        ap.add_argument("--category", required=True)
        ap.add_argument("--limit", type=int, default=0)
        args = ap.parse_args(a[1:])
        cmd_fetch_profile(prof, session, args.url, args.category, args.limit)
    elif cmd == "merge-tips":
        cmd_merge_tips(prof)
    else:
        raise SystemExit(f"未知命令 {cmd}（check|search|search-tokens|fetch-url|fetch-profile|review|prep-images|merge-q|merge-jobs|collect-current|collect-search|merge-tips|clean-staging）")


if __name__ == "__main__":
    main()
