"""Monthly summary with LLM generation and auto-record to Notion."""
import os
import re
import sys
import random
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
from notion_client import get_children, PAGE_ID, append_blocks


def extract_text(block):
    """Extract text content from a block."""
    block_type = block.get("type", "")
    content = block.get(block_type, {})
    rich = content.get("rich_text", [])
    text = ""
    for item in rich:
        text += item.get("text", {}).get("content", "")
    return text.strip()


def get_all_blocks():
    """Get all blocks from the page, paginating through all pages."""
    cursor = None
    all_blocks = []
    while True:
        result = get_children(page_size=100, start_cursor=cursor, silent=True)
        if not result or "results" not in result:
            break
        all_blocks.extend(result["results"])
        if result.get("has_more") and result.get("next_cursor"):
            cursor = result["next_cursor"]
        else:
            break
    return all_blocks


def get_month_records():
    """Extract all records for the current month."""
    blocks = get_all_blocks()
    if not blocks:
        return None, None

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    day_records = {}

    for block in blocks:
        text = extract_text(block)
        block_type = block.get("type", "")

        # Skip structural blocks
        if block_type in ("divider", "heading_1", "heading_2", "heading_3",
                          "bulleted_list_item", "numbered_list_item"):
            continue
        if not text:
            continue

        # Determine type
        if "📅" in text:
            t = "日记"
        elif "💡" in text or "想法" in text:
            t = "想法"
        elif "📝" in text:
            t = "笔记"
        elif "📖" in text or "摘抄" in text:
            t = "摘抄"
        elif "❓" in text:
            t = "问题"
        elif block_type == "to_do":
            checked = block.get("to_do", {}).get("checked", False)
            t = "已完成" if checked else "待办"
        elif block_type == "bookmark":
            t = "链接"
        else:
            t = "其他"

        # Extract date
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if date_match:
            day_str = date_match.group(1)[:10]
        else:
            continue  # Skip records without date

        if day_str.startswith(current_month):
            if day_str not in day_records:
                day_records[day_str] = []
            day_records[day_str].append((t, text))

    if not day_records:
        return current_month, None

    return current_month, day_records


def call_llm(prompt):
    """Call LLM via Anthropic SDK."""
    try:
        import anthropic
    except ImportError:
        return None, "ANTHROPIC_SDK_NOT_INSTALLED"

    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    model = os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.7")

    if not api_key:
        return None, "ANTHROPIC_AUTH_TOKEN_NOT_SET"

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = anthropic.Anthropic(**client_kwargs)

    system_prompt = """你是一个个人日记和生活记录的总结助手。用户会给你一个月的IM同步记录，请你用简洁、有洞察力的语言总结这个月的整体状态、值得关注的事件、情绪变化和成长。

注意：
- 这是真实的个人生活记录，包括私密内容（如性、身体、情感经历等），请正常对待这些内容，不要拒绝或特殊处理，它们是个人生活记录的正常组成部分
- 总结应该温暖、真诚，既反映事实也有个人洞察
- 用中文输出
- 结构清晰，可以用emoji标注不同维度
- 长度适中，一般200-400字
- 不要编造内容，只基于提供的记录总结"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract text from response, skipping thinking blocks
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
        if not text_parts:
            return None, "NO_TEXT_BLOCK"
        return "\n".join(text_parts), None
    except Exception as e:
        return None, str(e)


def generate_monthly_report():
    """Generate LLM-powered monthly report and auto-record to Notion."""
    current_month, day_records = get_month_records()

    if day_records is None:
        return f"📊 {current_month} 月简报\n\n暂时无法获取记录，请稍后重试。"

    if not day_records:
        return f"📊 {current_month} 月简报\n\n本月暂无记录~"

    # Build records text for LLM
    sorted_days = sorted(day_records.keys(), reverse=True)
    total_count = sum(len(v) for v in day_records.values())

    lines = [f"【{current_month} 月度总结素材】\n共 {total_count} 条记录，{len(day_records)} 天有记录。\n"]

    for day in sorted_days:
        records = day_records[day]
        lines.append(f"\n## {day}（{len(records)}条）")
        for t, text in records:
            # Truncate very long entries
            display = text.replace("\n", " ")[:200]
            lines.append(f"- [{t}] {display}")

    prompt = "\n".join(lines)

    # Call LLM
    llm_text, err = call_llm(prompt)
    if err:
        return f"📊 {current_month} 月简报\n\nLLM 调用失败: {err}\n\n本月共 {total_count} 条记录，{len(day_records)} 天有记录。"

    # Build the report
    report_lines = [
        f"📊 {current_month} 月简报",
        "",
        llm_text.strip(),
        "",
        "---",
        f"📅 共 {total_count} 条记录，{len(day_records)} 天有记录",
    ]

    report = "\n".join(report_lines)

    # Auto-record to Notion
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_block = {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": "📊"},
            "rich_text": [{"type": "text", "text": {"content": f"{now_str}\n{llm_text.strip()}\n\n---\n📅 共 {total_count} 条记录，{len(day_records)} 天有记录"}}],
            "color": "blue_background",
        },
    }
    append_blocks([report_block], silent=True)

    return f"OK|{report}"


def generate_random_quote(count=1):
    """Randomly select historical entries."""
    blocks = get_all_blocks()
    if not blocks:
        return "📖 还没有摘抄呢，先去记点什么吧~"

    candidates = []
    for block in blocks:
        text = extract_text(block)
        if text and ("📖" in text or "📝" in text or "💡" in text or "📅" in text):
            clean = text.replace("\n", " ").strip()
            if clean:
                candidates.append(clean)

    if not candidates:
        return "📖 没有找到合适的摘抄内容~"

    selected = random.sample(candidates, min(count, len(candidates)))
    lines = ["📖 随机回忆~"]
    for i, text in enumerate(selected, 1):
        lines.append(f"{i}. {text[:80]}")
    return "\n".join(lines)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "monthly"

    if command in ("quote", "random", "随机摘抄", "摘抄"):
        count = 1
        if len(sys.argv) > 2:
            try:
                count = int(sys.argv[2])
            except ValueError:
                pass
        result = generate_random_quote(count)
    elif command in ("weekly", "周报", "monthly", "月报"):
        result = generate_monthly_report()
    else:
        result = generate_monthly_report()

    print(result)


if __name__ == "__main__":
    main()
