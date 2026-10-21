# -*- coding: utf-8 -*-
"""上传 PNG 到思源 assets 并把文档中含旧 asset 的图片块原位换新（updateBlock）。
用前改下面【配置区】：DOC_ID / 每张图的 PNG、旧 asset 标记、版本号词干、题注。
判定上传成功只认非空 succMap；换块后断言新 asset 恰好 1 处、旧 asset 0 处。"""
import json, time, uuid, urllib.request
from pathlib import Path

# ---------------- 配置区 ----------------
DOC_ID = "20261015200128-7dutt8l"
RELOAD_UI = True
# (PNG 路径, 旧 asset 文件名里的唯一标记, 上传文件名词干, 题注 alt)
JOBS = [
    (r"D:\Project\Zcode\tmp_cmos_redraw\sym-p1-redraw.png", "sym-p1-v2-fbd67f", "sym-p1-v3",
     "插图 1｜题注待改"),
]
# ----------------------------------------

CONF = Path(r"D:\MyData\Warehouse\siyuan-backup\conf\conf.json")


def load_connection():
    conf = json.loads(CONF.read_text(encoding="utf-8-sig"))
    token = (conf.get("api") or {}).get("token") or ""
    urls = [v.rstrip("/") for v in conf.get("serverAddrs") or []
            if isinstance(v, str) and v.startswith(("http://127.0.0.1:", "http://localhost:"))]
    urls.append("http://127.0.0.1:6806")  # 兜底；端口每次启动漂移，conf 里的优先
    return list(dict.fromkeys(urls)), token


def call_json(base, token, path, payload=None, timeout=30):
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.loads(r.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"{path}: {result.get('msg')}")
    return result.get("data")


def upload_asset(base, token, png: Path, stem: str) -> str:
    boundary = "----ZCodeBoundary" + uuid.uuid4().hex
    fname = stem + "-" + uuid.uuid4().hex[:6] + ".png"
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file[]"; filename="{fname}"\r\n'.encode(),  # 必须 file[] 带 []
        b"Content-Type: image/png\r\n\r\n",
        png.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(base + "/api/asset/upload", data=b"".join(parts), method="POST")
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"upload {fname}: {result.get('msg')}")
    succ = (result.get("data") or {}).get("succMap") or {}
    if not succ:  # 写错字段名时这里静默为空，磁盘上没有文件
        raise RuntimeError(f"upload silent failure for {fname}")
    return next(iter(succ.values()))


def main():
    urls, token = load_connection()
    base = None
    for u in urls:
        try:
            d = call_json(u, token, "/api/notebook/lsNotebooks", {}, 5)
            if isinstance(d, dict) and d.get("notebooks"):
                base = u
                break
        except Exception:
            pass
    if not base:
        raise RuntimeError("no kernel")
    print("kernel:", base)

    children = call_json(base, token, "/api/block/getChildBlocks", {"id": DOC_ID})
    for png, old_marker, stem, alt in JOBS:
        asset = upload_asset(base, token, Path(png), stem)
        target = next((c for c in children if old_marker in (c.get("markdown") or "")), None)
        assert target is not None, f"block for {old_marker} not found"
        call_json(base, token, "/api/block/updateBlock",
                  {"id": target["id"], "dataType": "markdown", "data": f"![{alt}]({asset})"})
        time.sleep(1.5)
        children = call_json(base, token, "/api/block/getChildBlocks", {"id": DOC_ID})
        hit = [c for c in children if asset in (c.get("markdown") or "")]
        stale = [c for c in children if old_marker in (c.get("markdown") or "")]
        assert len(hit) == 1 and not stale, f"swap verify failed for {old_marker}"
        print(f"swapped {old_marker} -> {asset}")
        time.sleep(1)

    if RELOAD_UI:
        call_json(base, token, "/api/ui/reloadUI", {})
    print(f"done; {len(JOBS)} figure(s) swapped")


if __name__ == "__main__":
    main()
