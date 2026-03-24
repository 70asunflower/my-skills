# -*- coding: utf-8 -*-
"""
Notion API 公共模块
封装认证、请求、错误处理和输出格式化。
所有脚本通过此模块与 Notion 交互。
"""

import os
import sys
import time
import re
from datetime import datetime

# 彻底清除所有代理环境变量（大小写都要清除）
proxy_vars = [
    'http_proxy', 'https_proxy', 'ftp_proxy', 'all_proxy',
    'HTTP_PROXY', 'HTTPS_PROXY', 'FTP_PROXY', 'ALL_PROXY',
    'no_proxy', 'NO_PROXY'
]
for var in proxy_vars:
    os.environ.pop(var, None)

# 尝试导入 notion_client，未安装时给出友好提示
try:
    from notion_client import Client, APIResponseError
except ImportError:
    print("ERROR|CONFIG|notion-client 未安装，请执行: pip install notion-client", flush=True)
    sys.exit(1)


# ──────────────────────────────────────────────
# 环境变量读取
# ──────────────────────────────────────────────

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "").strip()
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip()
NOTION_QUOTES_PAGE_ID = os.environ.get("NOTION_QUOTES_PAGE_ID", "").strip()
OPENCLAW_CLAW_NAME = os.environ.get("OPENCLAW_CLAW_NAME", "").strip()

# 最大重试次数（应对速率限制）
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # 秒


# ──────────────────────────────────────────────
# 页面 ID 标准化
# ──────────────────────────────────────────────

def normalize_page_id(page_id: str) -> str:
    """
    将 32 位十六进制字符标准化为带连字符的 UUID 格式。
    支持输入：
      - 32 位无连字符：1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
      - 带连字符 UUID：1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d
      - 含有 URL 前缀的情况会被清理
    """
    # 移除所有非十六进制字符
    clean = re.sub(r'[^0-9a-fA-F]', '', page_id)
    if len(clean) != 32:
        return page_id  # 无法标准化，返回原值让 API 报错
    return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"


# ──────────────────────────────────────────────
# 输出工具（统一协议）
# ──────────────────────────────────────────────

def output_ok(message: str):
    """输出成功结果到 stdout"""
    print(f"OK|{message}", flush=True)


def output_error(error_type: str, message: str = ""):
    """输出错误到 stdout，调试详情到 stderr"""
    if message:
        print(f"ERROR|{error_type}|{message}", flush=True)
    else:
        print(f"ERROR|{error_type}", flush=True)


def log_debug(message: str):
    """调试日志输出到 stderr（不展示给用户）"""
    print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


# ──────────────────────────────────────────────
# 配置检查
# ──────────────────────────────────────────────

def check_required_config() -> bool:
    """
    检查必须的环境变量是否已配置。
    返回 True 表示配置完整，False 表示缺失。
    """
    if not NOTION_API_KEY:
        output_error("CONFIG", "NOTION_API_KEY 未配置")
        return False
    if not NOTION_PARENT_PAGE_ID:
        output_error("CONFIG", "NOTION_PARENT_PAGE_ID 未配置")
        return False
    return True


def check_quotes_config() -> bool:
    """检查摘抄本配置"""
    if not NOTION_QUOTES_PAGE_ID:
        output_error("CONFIG", "NOTION_QUOTES_PAGE_ID 未配置，摘抄功能需要先配置摘抄本页面 ID")
        return False
    return True


# ──────────────────────────────────────────────
# Notion 客户端初始化
# ──────────────────────────────────────────────

_client = None


def get_client() -> Client:
    """获取 Notion Client 单例（禁用代理，直连 Notion API）"""
    global _client
    if _client is None:
        if not NOTION_API_KEY:
            output_error("CONFIG", "NOTION_API_KEY 未配置")
            sys.exit(1)
        # 清除代理环境变量，直连 Notion API
        import httpx
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY']:
            os.environ.pop(var, None)
        _client = Client(auth=NOTION_API_KEY)
    return _client


def get_parent_page_id() -> str:
    """获取标准化后的父页面 ID"""
    return normalize_page_id(NOTION_PARENT_PAGE_ID)


def get_quotes_page_id() -> str:
    """获取标准化后的摘抄本页面 ID"""
    return normalize_page_id(NOTION_QUOTES_PAGE_ID)


# ──────────────────────────────────────────────
# 带重试的 API 调用
# ──────────────────────────────────────────────

def api_call_with_retry(func, *args, **kwargs):
    """
    带自动重试的 API 调用包装器。
    自动处理速率限制（429）和临时网络错误。
    最多重试 MAX_RETRIES 次，间隔 RETRY_DELAY 秒。
    """
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except APIResponseError as e:
            last_error = e
            log_debug(f"API 错误 (尝试 {attempt + 1}/{MAX_RETRIES + 1}): {e.status} {e.code}")
            if e.status == 429:
                # 速率限制，等待后重试
                if attempt < MAX_RETRIES:
                    retry_after = float(e.headers.get("Retry-After", RETRY_DELAY)) if hasattr(e, 'headers') and e.headers else RETRY_DELAY
                    log_debug(f"速率限制，等待 {retry_after}s 后重试...")
                    time.sleep(retry_after)
                    continue
                else:
                    output_error("RATE_LIMIT")
                    sys.exit(1)
            elif e.status == 401:
                output_error("AUTH", "API 密钥无效")
                sys.exit(1)
            elif e.status == 403:
                output_error("AUTH", "页面未授权，需要在 Notion 中 Connect to Integration")
                sys.exit(1)
            elif e.status == 404:
                output_error("AUTH", "页面不存在或未授权")
                sys.exit(1)
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                output_error("API", str(e.code))
                sys.exit(1)
        except Exception as e:
            last_error = e
            log_debug(f"未知错误 (尝试 {attempt + 1}/{MAX_RETRIES + 1}): {type(e).__name__}: {e}")
            if "connect" in str(e).lower() or "timeout" in str(e).lower() or "network" in str(e).lower():
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                output_error("NETWORK")
                sys.exit(1)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            output_error("UNKNOWN", str(e))
            sys.exit(1)

    # 不应到达此处
    output_error("UNKNOWN", str(last_error) if last_error else "未知错误")
    sys.exit(1)


# ──────────────────────────────────────────────
# 常用 Notion Block 构建器
# ──────────────────────────────────────────────

def make_rich_text(text: str, bold: bool = False, italic: bool = False, color: str = "default") -> list:
    """创建富文本数组"""
    rt = {
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "color": color,
        },
    }
    return [rt]


def make_paragraph_block(text: str, color: str = "default") -> dict:
    """创建段落块"""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": make_rich_text(text),
            "color": color,
        },
    }


def make_heading_block(level: int, text: str) -> dict:
    """创建标题块（level: 1/2/3）"""
    heading_type = f"heading_{level}"
    return {
        "object": "block",
        "type": heading_type,
        heading_type: {
            "rich_text": make_rich_text(text),
        },
    }


def make_todo_block(text: str, checked: bool = False) -> dict:
    """创建待办块"""
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": make_rich_text(text),
            "checked": checked,
        },
    }


def make_quote_block(text: str) -> dict:
    """创建引用块"""
    return {
        "object": "block",
        "type": "quote",
        "quote": {
            "rich_text": make_rich_text(text),
        },
    }


def make_divider_block() -> dict:
    """创建分割线块"""
    return {
        "object": "block",
        "type": "divider",
        "divider": {},
    }


def make_bulleted_list_block(text: str, children: list = None) -> dict:
    """创建无序列表项"""
    block = {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": make_rich_text(text),
        },
    }
    if children:
        block["bulleted_list_item"]["children"] = children
    return block


def make_numbered_list_block(text: str, children: list = None) -> dict:
    """创建有序列表项"""
    block = {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {
            "rich_text": make_rich_text(text),
        },
    }
    if children:
        block["numbered_list_item"]["children"] = children
    return block


def make_toggle_block(text: str, children: list = None) -> dict:
    """创建折叠块（Toggle）"""
    block = {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": make_rich_text(text),
        },
    }
    if children:
        block["toggle"]["children"] = children
    return block


# ──────────────────────────────────────────────
# 追加内容到页面
# ──────────────────────────────────────────────

def append_blocks(blocks: list, page_id: str = None):
    """
    向指定页面追加内容块。
    page_id 默认使用 NOTION_PARENT_PAGE_ID。
    """
    if page_id is None:
        page_id = get_parent_page_id()

    client = get_client()
    return api_call_with_retry(
        client.blocks.children.append,
        block_id=page_id,
        children=blocks,
    )


def append_im_blocks(blocks: list, page_id: str = None, type_key: str = None, tag: str = None, project: str = None):
    """
    针对 IM 系统消息的聚合追加逻辑。
    1. 自动与本地 `.last_date` 进行比对，若跨天则插入 `---` 分割线。
    2. 如果提供了 type_key，则自动在消息体前额外插入一条彩色抬头块（包含时间、Emoji、标签和项目）。
    """
    new_blocks = []
    
    # 存放在用户主目录的 .qclaw/workspace 中，符合 QClaw 用户的个人配置习惯
    home_dir = os.path.expanduser("~")
    state_dir = os.path.join(home_dir, ".qclaw", "workspace", "notion-im-helper")
    os.makedirs(state_dir, exist_ok=True)
    last_date_file = os.path.join(state_dir, ".last_date")
    
    today_str = get_today_str()
    last_date = ""
    if os.path.exists(last_date_file):
        with open(last_date_file, "r", encoding="utf-8") as f:
            last_date = f.read().strip()
            
    # 如果跨天了，先插入一条分割线，并更新文件
    if last_date != today_str:
        new_blocks.append(make_divider_block())
        with open(last_date_file, "w", encoding="utf-8") as f:
            f.write(today_str)
            
    # 判断并生成专属抬头
    if type_key:
        header_block = build_header_block(type_key, tag, project)
        new_blocks.append(header_block)
        
    new_blocks.extend(blocks)
    
    return append_blocks(new_blocks, page_id=page_id)


# ──────────────────────────────────────────────
# 读取页面内容块
# ──────────────────────────────────────────────

def list_blocks(page_id: str = None, start_cursor: str = None) -> dict:
    """
    列出指定页面的内容块。
    返回 Notion API 原始响应（包含 results、has_more、next_cursor）。
    """
    if page_id is None:
        page_id = get_parent_page_id()

    client = get_client()
    kwargs = {"block_id": page_id}
    if start_cursor:
        kwargs["start_cursor"] = start_cursor

    return api_call_with_retry(client.blocks.children.list, **kwargs)


def list_all_blocks(page_id: str = None) -> list:
    """列出指定页面的所有内容块（自动分页）"""
    all_blocks = []
    cursor = None
    while True:
        response = list_blocks(page_id=page_id, start_cursor=cursor)
        all_blocks.extend(response.get("results", []))
        if not response.get("has_more", False):
            break
        cursor = response.get("next_cursor")
    return all_blocks


# ──────────────────────────────────────────────
# 搜索
# ──────────────────────────────────────────────

def search_pages(query: str, page_size: int = 10) -> list:
    """
    搜索 Notion 页面。
    返回搜索结果列表。
    """
    client = get_client()
    response = api_call_with_retry(
        client.search,
        query=query,
        page_size=page_size,
    )
    return response.get("results", [])


# ──────────────────────────────────────────────
# 时间工具
# ──────────────────────────────────────────────

def get_timestamp() -> str:
    """获取当前时间戳字符串（格式：YYYY-MM-DD HH:MM）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_today_str() -> str:
    """获取今天日期字符串（格式：YYYY-MM-DD）"""
    return datetime.now().strftime("%Y-%m-%d")


# ──────────────────────────────────────────────
# 标签/项目 参数解析工具
# ──────────────────────────────────────────────

TYPE_CONFIG = {
    "flash": {"emoji": "💭", "color": "gray"},
    "diary": {"emoji": "📅", "color": "blue"},
    "todo": {"emoji": "✅", "color": "red"},
    "done": {"emoji": "✔️", "color": "green"},
    "note": {"emoji": "📝", "color": "yellow"},
    "idea": {"emoji": "💡", "color": "orange"},
    "question": {"emoji": "❓", "color": "purple"},
    "quote": {"emoji": "📖", "color": "green"},
    "link": {"emoji": "🔗", "color": "gray"},
    "task": {"emoji": "🎯", "color": "red"},
    "summary": {"emoji": "📊", "color": "blue"},
    "heading": {"emoji": "📌", "color": "default"},
    "list": {"emoji": "📌", "color": "default"},
    "toggle": {"emoji": "📂", "color": "default"},
}

PROJECT_CONFIG = {
    "工作": {"emoji": "💼", "color": "blue"},
    "工作项目": {"emoji": "💼", "color": "blue"},
    "学习": {"emoji": "📚", "color": "green"},
    "学习项目": {"emoji": "📚", "color": "green"},
    "读书": {"emoji": "📖", "color": "purple"},
    "读书项目": {"emoji": "📖", "color": "purple"},
}

def parse_metadata_args(args: list) -> tuple:
    """
    从命令行参数中解析 --tag 和 --project。
    返回 (remaining_args, tag, project)。
    丢弃了之前的 claw 概念。
    """
    tag = None
    project = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == "--tag" and i + 1 < len(args):
            tag = args[i + 1]
            i += 2
        elif args[i] == "--project" and i + 1 < len(args):
            project = args[i + 1]
            i += 2
        elif args[i] in ("--claw", "--source") and i + 1 < len(args):
            # 直接丢弃旧版的 claw 和 source 标识参数及其值
            i += 2
        elif args[i] == "--content" and i + 1 < len(args):
            remaining.append(args[i + 1])
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return remaining, tag, project


def build_header_block(type_key: str, tag: str = None, project: str = None) -> dict:
    """
    构建标准化的双行/多行结构的首行抬头（Paragraph Block）。
    格式示例：10:30 📅  #标签 💼【项目】
    整体文字颜色由 type_key 决定。
    """
    config = TYPE_CONFIG.get(type_key, {"emoji": "💬", "color": "gray"})
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    emoji = config["emoji"]
    color = "gray"  # 统一使用灰色
    
    parts = [f"{time_str} {emoji}"]
    if tag:
        parts.append(f"#{tag}")
    if project:
        proj_emoji = PROJECT_CONFIG.get(project, {}).get("emoji", "")
        if proj_emoji:
            parts.append(f"{proj_emoji}【{project}】")
        else:
            parts.append(f"【{project}】")
            
    text_content = "  ".join(parts)
    return make_paragraph_block(text_content, color=color)
