"""Notion API wrapper - shared client for all record operations."""
import os
import sys
import json
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = os.environ.get("NOTION_API_KEY", "")
PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")
BASE_URL = "https://api.notion.com/v1"

HEADERS_TEMPLATE = {
    "Authorization": "",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def get_headers():
    headers = HEADERS_TEMPLATE.copy()
    headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def api_request(method, path, body=None):
    """Make a single API request with retry on rate limit."""
    headers = get_headers()
    url = f"{BASE_URL}/{path}"

    for attempt in range(3):
        try:
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            resp = urllib.request.urlopen(req)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                import time
                time.sleep(1.5 * (attempt + 1))
                continue
            error_body = e.read().decode()
            try:
                err_data = json.loads(error_body)
                message = err_data.get("message", str(e))
            except Exception:
                message = str(e)
            return {"error": True, "code": e.code, "message": message}
        except Exception as e:
            import time
            if attempt < 2:
                time.sleep(1)
                continue
            return {"error": True, "message": str(e)}

    return {"error": True, "message": "Rate limited after retries"}


def append_blocks(children, silent=False):
    """Append a list of blocks to the page."""
    if not children:
        print("OK|没有内容可追加")
        return
    result = api_request("PATCH", f"blocks/{PAGE_ID}/children", {"children": children})
    if result.get("error"):
        _emit_error(result)
        return
    block_count = len(result.get("results", children))
    if not silent:
        print(f"OK|已记录到 Notion，共 {block_count} 个 blocks")


def get_children(page_id=None, start_cursor=None, page_size=100, silent=False):
    """Read page children blocks."""
    pid = page_id or PAGE_ID
    params = f"page_size={page_size}"
    if start_cursor:
        params += f"&start_cursor={start_cursor}"
    result = api_request("GET", f"blocks/{pid}/children?{params}")
    if result.get("error"):
        if not silent:
            _emit_error(result)
        return None
    return result


def delete_last_block():
    """Delete the last block on the page."""
    data = get_children()
    if not data or "results" not in data or not data["results"]:
        print("OK| 没有可撤回的记录")
        return
    last_block = data["results"][-1]
    block_id = last_block["id"]
    result = api_request("DELETE", f"blocks/{block_id}")
    if result.get("error"):
        _emit_error(result)
        return
    print("OK| 已撤回最后一条记录")


def check_config():
    """Verify API key and page access."""
    if not API_KEY:
        return {"ok": False, "code": "CONFIG", "message": "NOTION_API_KEY 未配置"}
    if not PAGE_ID:
        return {"ok": False, "code": "CONFIG", "message": "NOTION_PARENT_PAGE_ID 未配置"}

    result = api_request("GET", f"blocks/{PAGE_ID}/children?page_size=1")
    if result.get("error"):
        code = result.get("code", 0)
        msg = result.get("message", "")
        if code == 401 or "Unauthorized" in msg:
            return {"ok": False, "code": "AUTH", "message": "API Key 无效或页面未授权"}
        if code == 404 or "Not Found" in msg:
            return {"ok": False, "code": "AUTH", "message": "页面不存在或 Integration 未授权"}
        return {"ok": False, "code": "UNKNOWN", "message": msg}
    return {"ok": True, "message": ""}


def _emit_error(result):
    """Emit a friendly error message based on the error code."""
    msg = result.get("message", "")
    code = result.get("code", 0)
    if code == 401 or "Unauthorized" in msg:
        print("ERROR|AUTH")
    elif code == 404 or "Could not find" in msg:
        print("ERROR|AUTH")
    elif code == 429:
        print("ERROR|RATE_LIMIT")
    else:
        print("ERROR|NETWORK")


if __name__ == "__main__":
    result = check_config()
    if not result["ok"]:
        print(f"ERROR|{result['code']}")
    else:
        print("OK|配置检查通过")
