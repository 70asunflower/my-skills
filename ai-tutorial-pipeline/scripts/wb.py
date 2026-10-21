# -*- coding: utf-8 -*-
"""WebBridge 操作库：控制用户本机真实浏览器（默认 Edge，复用登录态；chat.qwen.ai 等）。
所有中文参数都经 urllib+JSON 传输，绝不走 shell 内联（Windows shell 会弄坏中文）。
用法: python wb.py <daemon|open <url>|snapshot|send <prompt_file>|copy-latest <out.md>> [--session NAME]
"""
import json, os, re, subprocess, sys, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BRIDGE = "http://127.0.0.1:10086/command"
DEFAULT_SESSION = os.environ.get("WB_SESSION", "ai-tutorial")

NO_TAB_HINT = "该会话还没有当前标签页（HTTP 502）。generate.py 会自动 find_tab/navigate；CLI 单用时先执行: python wb.py open <url> --session <名>"


def wb(action, args, session=DEFAULT_SESSION, timeout=90):
    body = json.dumps({"action": action, "args": args, "session": session}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BRIDGE, data=body, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{action} 失败 HTTP {e.code}: {NO_TAB_HINT if e.code == 502 else e.reason}")


def ensure_daemon(wait_ext=60):
    """守护进程没起就启动；扩展没连上就等它重连。"""
    try:
        r = wb("list_tabs", {}, timeout=8)
        if r.get("ok"):
            return "ok"
    except Exception:
        pass
    exe = os.path.expanduser(r"~\.kimi-webbridge\bin\kimi-webbridge.exe")
    if os.path.isfile(exe):
        subprocess.run([exe, "start"], capture_output=True, timeout=30)
    deadline = time.time() + wait_ext
    last = None
    while time.time() < deadline:
        try:
            r = wb("list_tabs", {}, timeout=8)
            if r.get("ok"):
                return "ok"
            last = json.dumps(r.get("error", {}), ensure_ascii=False)
        except Exception as e:
            last = type(e).__name__
        time.sleep(5)
    raise RuntimeError(f"WebBridge 不可用: {last}（浏览器扩展未连接？让用户打开 Edge 检查扩展）")


def snap(session=DEFAULT_SESSION):
    return wb("snapshot", {}, session=session)["data"]


def blob_buttons(tree):
    texts, buttons = [], []
    def walk(node):
        if isinstance(node, dict):
            role, name = node.get("role"), node.get("name") or ""
            if role == "StaticText":
                texts.append(name)
            elif role == "button":
                buttons.append(name)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(tree)
    return "".join(texts), buttons


def find_refs(tree, send_names=("Send", "发送", "Stop", "停止"), textbox_names=("Ask Qwen",)):
    refs = {}
    def walk(node):
        if isinstance(node, dict):
            role, name, ref = node.get("role"), node.get("name") or "", node.get("ref")
            if ref and role == "button" and name in send_names:
                refs.setdefault("send", ref)
                refs["send_name"] = name
            if ref and role == "textbox" and name in textbox_names:
                refs.setdefault("input", ref)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(tree)
    return refs


def composer_coords(session, composer_css):
    r = wb("evaluate", {"code": (
        "(() => { const els=[...document.querySelectorAll(" + json.dumps(composer_css) + ")]"
        ".map(e=>{const r=e.getBoundingClientRect();return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),empty:(e.value!==undefined?e.value.length:(e.textContent||'').trim().length)}});"
        "const eds=els.filter(e=>e.y>0&&e.y<window.innerHeight); eds.sort((a,b)=>b.y-a.y); return JSON.stringify(eds[0]||null); })()")}, session=session)
    if not r.get("ok"):
        raise RuntimeError(f"composer 定位失败: {json.dumps(r)[:150]}")
    return json.loads((r.get("data") or {}).get("value") or "null")


def editor_empty(session, composer_css):
    try:
        r = wb("evaluate", {"code": (
            "(() => { const e=document.querySelector(" + json.dumps(composer_css) + ");"
            " return e ? String((e.value!==undefined?e.value:(e.textContent||'')).length) : 'gone'; })()")}, session=session)
        v = (r.get("data") or {}).get("value")
        return v == "0" or v == "gone"
    except Exception:
        return False


def cdp_click(session, x, y):
    for t in ("mouseMoved", "mousePressed", "mouseReleased"):
        wb("cdp", {"method": "Input.dispatchMouseEvent",
                   "params": {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1}}, session=session)


def cdp_keys(session, *keys):
    for k in keys:
        wb("cdp", {"method": "Input.dispatchKeyEvent", "params": k}, session=session)


def install_interceptor(session):
    """劫持页面剪贴板写入：系统剪贴板可能被 360 等占用而不可读写，拦截器 100% 可靠。幂等 + 每次清空。"""
    wb("evaluate", {"code": """
      (() => { if(!window.__patched){ window.__patched=true; window.__capA=null; window.__capB=null;
        const o=navigator.clipboard.writeText.bind(navigator.clipboard);
        navigator.clipboard.writeText=(t)=>{window.__capA=t; return o(t);};
        document.addEventListener('copy', (e)=>{ try{ window.__capB=e.clipboardData.getData('text/plain'); }catch(_){}}, true);}
        window.__capA=null; window.__capB=null; return 'ok'; })()
    """}, session=session)


def read_captured(session):
    r = wb("evaluate", {"code": "JSON.stringify({a:window.__capA||null, b:window.__capB||null})"}, session=session)
    caps = json.loads((r.get("data") or {}).get("value") or "{}")
    return caps.get("a") or caps.get("b")


def pick_marker(prompt):
    lines = [l.strip() for l in prompt.splitlines() if l.strip()]
    best = max(lines, key=len) if lines else prompt
    m = re.sub(r"[\W\s]+", "", best, flags=re.UNICODE)
    if len(m) >= 6:
        return m[:12]
    return (re.sub(r"\s+", "", prompt) or "SEND")[:12]


CTRL_A = ({"type": "keyDown", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65, "modifiers": 2},
          {"type": "keyUp", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65, "modifiers": 2})
DELETE = ({"type": "keyDown", "key": "Delete", "code": "Delete", "windowsVirtualKeyCode": 46},
          {"type": "keyUp", "key": "Delete", "code": "Delete", "windowsVirtualKeyCode": 46})
ENTER = ({"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": "\r"},
         {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})


def send_prompt(session, prompt, composer_css='textarea[placeholder="Ask Qwen"]'):
    """发送一条提示词并验证已进入对话（标记计数增加 + 输入框清空）。返回 (ok, blob_len, copies)。"""
    marker = pick_marker(prompt)
    for attempt in range(2):
        s = snap(session)
        blob, buttons = blob_buttons(s["tree"])
        refs = find_refs(s["tree"])
        marker_pre = blob.count(marker)  # 发送前标记出现次数（重发场景下旧消息也含标记）
        sent = False
        # 路径 A：fill 引用（拿到输入框引用才尝试）
        if refs.get("input") and refs.get("send"):
            r = wb("fill", {"selector": refs["input"], "value": prompt}, session=session)
            if r.get("ok"):
                time.sleep(1)
                r2 = wb("click", {"selector": refs["send"]}, session=session)
                sent = r2.get("ok")
        # 路径 B：CDP 真实点击聚焦 → 清空残留 → insertText → 点 Send / 回车
        if not sent:
            ed = composer_coords(session, composer_css)
            if not ed:
                raise RuntimeError("找不到输入框 " + composer_css)
            cdp_click(session, ed["x"], ed["y"])
            time.sleep(0.8)
            cdp_keys(session, *CTRL_A, *DELETE)  # 清空残留，避免拼接旧内容
            time.sleep(0.3)
            r = wb("cdp", {"method": "Input.insertText", "params": {"text": prompt}}, session=session)
            if not r.get("ok"):
                raise RuntimeError("insertText 失败")
            time.sleep(1)
            refs = find_refs(snap(session)["tree"])
            if refs.get("send"):
                r2 = wb("click", {"selector": refs["send"]}, session=session)
                sent = r2.get("ok")
            else:
                cdp_keys(session, *ENTER)
                sent = True
        if not sent:
            time.sleep(2)
            continue
        # 验证：给足时间并多次确认，避免把"慢回显"误判为失败而重发
        ok = False
        for _ in range(3):
            time.sleep(4)
            blob2, buttons2 = blob_buttons(snap(session)["tree"])
            if blob2.count(marker) > marker_pre and editor_empty(session, composer_css):
                ok = True
                break
        if ok:
            copies = sum(1 for b in buttons2 if b == "Copy")
            return True, len(blob2), copies
        time.sleep(2)
    raise RuntimeError("发送失败：标记计数未增加或输入框未清空")


def wait_idle(session, deadline_s=600, interval=10):
    """等当前生成结束（Stop 按钮消失）。"""
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        s = snap(session)
        blob, buttons = blob_buttons(s["tree"])
        if not any(b in ("Stop", "停止") for b in buttons):
            return len(blob)
        time.sleep(interval)
    raise RuntimeError("等待空闲超时")


def wait_done(session, baseline, copies_at_send, min_growth=1500, deadline_s=1500, interval=20):
    """等一章生成完成：Stop 消失 + 复制按钮数增加，双确认。对"正在生成"和"早已完成"都适用。"""
    deadline = time.time() + deadline_s
    confirm = 0
    i = 0
    while time.time() < deadline:
        i += 1
        s = snap(session)
        blob, buttons = blob_buttons(s["tree"])
        stop = any(b in ("Stop", "停止") for b in buttons)
        copies = sum(1 for b in buttons if b == "Copy")
        print(f"    poll {i} len={len(blob)} stop={stop} copies={copies}", flush=True)
        if not stop and copies > copies_at_send and len(blob) > baseline + min_growth:
            confirm += 1
            if confirm >= 2:
                return len(blob)
        else:
            confirm = 0
        time.sleep(interval)
    raise RuntimeError("生成超时")


def copy_btn_coords(session, copy_btn_css):
    r = wb("evaluate", {"code": (
        "(() => { const bs=[...document.querySelectorAll(" + json.dumps(copy_btn_css) + ")];"
        " if(!bs.length) return '[]';"
        " const b=bs[bs.length-1]; const r=b.getBoundingClientRect();"
        " return JSON.stringify({x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2), vis:r.bottom>0&&r.top<window.innerHeight, n:bs.length}); })()")}, session=session)
    return json.loads((r.get("data") or {}).get("value") or "null")


def capture_latest(session, copy_btn_css='button[aria-label="Copy"], button[title="Copy"]', retries=3):
    """点击最新一条回复的复制按钮（文档序最后一个），经拦截器取回 Markdown。"""
    install_interceptor(session)
    for attempt in range(retries):
        info = copy_btn_coords(session, copy_btn_css)
        if not info or info.get("n", 0) == 0:
            time.sleep(3)
            continue
        if not info.get("vis"):
            wb("evaluate", {"code": (
                "(() => { const bs=[...document.querySelectorAll(" + json.dumps(copy_btn_css) + ")];"
                " if(bs.length) bs[bs.length-1].scrollIntoView({block:'center'}); return 'ok'; })()")}, session=session)
            time.sleep(2.5)  # 平滑滚动动画结束后再量坐标
            info = copy_btn_coords(session, copy_btn_css)
            if not info or not info.get("vis"):
                continue
        time.sleep(0.5)
        cdp_click(session, info["x"], info["y"])
        time.sleep(1.5)
        val = read_captured(session)
        if isinstance(val, str) and len(val) > 500:
            return val
        time.sleep(2)
    raise RuntimeError("复制按钮点击后未截获到内容")


# ---------- CLI（救援/调试用） ----------
def main():
    a = sys.argv[1:]
    session = DEFAULT_SESSION
    if "--session" in a:
        i = a.index("--session")
        if i + 1 >= len(a):
            raise SystemExit("--session 需要一个值")
        session = a[i + 1]
        del a[i:i + 2]
    cmd = a[0] if a else "daemon"
    if cmd == "daemon":
        print(ensure_daemon())
    elif cmd == "open":
        r = wb("navigate", {"url": a[1], "newTab": True, "group_title": os.environ.get("WB_GROUP", "教程生成")}, session=session)
        print(json.dumps(r.get("data", r), ensure_ascii=False))
    elif cmd == "snapshot":
        s = snap(session)
        blob, buttons = blob_buttons(s["tree"])
        print(json.dumps({"url": s.get("url"), "chars": len(blob), "buttons": buttons,
                          "tail": blob[-120:]}, ensure_ascii=False))
    elif cmd == "send":
        prompt = open(a[1], encoding="utf-8").read().strip()
        ok, blen, copies = send_prompt(session, prompt)
        print(json.dumps({"sent": ok, "len": blen, "copies": copies}))
    elif cmd == "copy-latest":
        val = capture_latest(session)
        open(a[1], "w", encoding="utf-8").write(val)
        print(f"OK_CHARS {len(val)} HEAD {val[:60]!r}")
    else:
        raise SystemExit(f"未知命令 {cmd}（daemon|open|snapshot|send|copy-latest）")


if __name__ == "__main__":
    main()
