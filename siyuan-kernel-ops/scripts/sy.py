"""SiYuan Kernel API helper — the reference implementation for siyuan-kernel-ops.

Usage from a WorkBuddy session (replace <skill dir> with the skill's base directory):

    import sys; sys.path.insert(0, r"<skill dir>/scripts")
    from sy import connect, call
    base, token = connect()
    call(base, token, "/api/notebook/lsNotebooks")

Smoke test: python sy.py
"""

import json
import os
import urllib.error
import urllib.request
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


if __name__ == "__main__":
    base, token = connect()
    notebooks = call(base, token, "/api/notebook/lsNotebooks")["notebooks"]
    version = call(base, token, "/api/system/version")
    print(f"kernel : {base}")
    print(f"version: {version}")
    print(f"notebooks: {len(notebooks)}")
    for nb in notebooks:
        state = "closed" if nb.get("closed") else "open"
        print(f"  {nb['id']}  {nb['name']}  ({state})")
