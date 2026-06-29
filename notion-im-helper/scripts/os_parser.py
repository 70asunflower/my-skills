"""Parse os-prefixed messages into structured commands for 8+1 Life OS.

Input:  "os l 晨跑5公里 @身体 energy:h duration:30"
Output: {"command": "log", "content": "晨跑5公里", "bucket": "Body", ...}

Pure logic — no API calls, no stdout.
Bucket resolution delegated to user.lifeos.client.
"""
import re, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from user.lifeos.client import resolve_bucket, list_available_buckets


# ---- Command registry ----

CMD_ALIASES = {
    "log":     ["l", "log", "记录"],
    "idea":    ["i", "idea", "灵感"],
    "habit":   ["h", "habit", "习惯", "打卡"],
    "streaks": ["hs", "streaks"],
    "today":   ["今天"],
    "week":    ["本周"],
    "bucket":  ["桶"],
    "weekly":  ["周报", "wr"],
    "monthly": ["月报", "mr"],
    "adventure": ["冒险"],
    "ideas_list": ["灵感列表"],
}

REVERSE_CMD = {}
for cmd, aliases in CMD_ALIASES.items():
    for a in aliases:
        REVERSE_CMD[a] = cmd


# ---- Main parser ----

def parse(message):
    """Parse an os-prefixed message into a structured command dict.

    Args:
        message: Raw message string. May or may not include "os " prefix.

    Returns:
        {
            "command": "log" | "idea" | "habit" | "streaks" | "today"
                     | "week" | "bucket" | "weekly" | "monthly" | "adventure"
                     | "ideas_list" | None,
            "content": str | None,       # cleaned content text
            "bucket": str | None,        # resolved English short name
            "energy": str | None,        # "high" | "medium" | "low"
            "duration": int | None,      # minutes
            "source": str | None,        # idea source
            "urgency": str | None,       # "now" | "thisweek" | "later"
            "notes": str | None,         # note / 备注
            "mood": str | None,          # "Great" | "Good" | "Neutral" | "Low" | "Terrible"
            "adventure": str | None,     # reserved for future adventure relation
            "error": str | None,         # error message if parsing failed
        }
    """
    message = message.strip()

    # Strip leading "os " if present (case-insensitive)
    if message.lower().startswith("os "):
        message = message[3:].strip()
    elif message.lower() == "os":
        return {"command": None, "content": None, "bucket": None,
                "energy": None, "duration": None, "source": None,
                "urgency": None, "notes": None, "mood": None,
                "adventure": None,
                "error": "请提供 os 命令，例如: os l 晨跑 @身体"}

    # Extract command word (first token)
    parts = message.split(None, 1)
    cmd_token = parts[0].lower() if parts else ""
    remaining = parts[1] if len(parts) > 1 else ""

    command = REVERSE_CMD.get(cmd_token)
    if not command:
        # Try matching the full message as a command (for multi-char commands like "今天")
        for alias, cmd in REVERSE_CMD.items():
            if message.startswith(alias) and (len(message) == len(alias) or message[len(alias)] == " "):
                command = cmd
                remaining = message[len(alias):].strip()
                break

    if not command:
        return {"command": None, "content": message, "bucket": None,
                "energy": None, "duration": None, "source": None,
                "urgency": None, "notes": None, "mood": None,
                "adventure": None,
                "error": f"未知命令: {cmd_token}。可用: l/log/i/idea/h/habit/hs/今天/本周/桶/周报/月报"}

    # ---- Extract attributes from remaining text (single-pass, preserve original) ----

    # Compile all attribute patterns: (name, pattern, value_transform)
    PATTERNS = [
        ("bucket",  re.compile(r'@(\S+)')),
        ("energy",  re.compile(r'\benergy:([hml])\b', re.IGNORECASE)),
        ("duration", re.compile(r'\bdur(?:ation)?:(\d+)\b', re.IGNORECASE)),
        ("source",  re.compile(r'\bsource:(\S+)\b', re.IGNORECASE)),
        ("urgency", re.compile(r'\burg(?:ency)?:(now|thisweek|later)\b', re.IGNORECASE)),
        ("note_q",  re.compile(r'\b(?:note|备注):"([^"]+)"', re.IGNORECASE)),
        ("note_w",  re.compile(r'\b(?:note|备注):(\S+)', re.IGNORECASE)),
        ("mood",    re.compile(r'\bmood:(great|good|neutral|low|terrible)\b', re.IGNORECASE)),
    ]

    # Collect all matches with their spans
    matches = []
    for attr_name, pat in PATTERNS:
        for m in pat.finditer(remaining):
            matches.append((m.start(), m.end(), attr_name, m.group(1)))

    # Sort by position (descending) so removal doesn't shift indices
    matches.sort(key=lambda x: x[0], reverse=True)

    # Remove all matched spans from remaining text
    content_chars = list(remaining)
    for start, end, _, _ in matches:
        for i in range(end - 1, start - 1, -1):
            content_chars[i] = None
    # Rebuild content text — collapse consecutive whitespace that came from removals
    content_text = "".join(c for c in content_chars if c is not None)
    content = " ".join(content_text.split()).strip() if content_text.strip() else None

    # Extract values from matches (in original order for debugging)
    bucket_raw = None
    bucket = None
    energy = None
    duration = None
    source = None
    urgency = None
    notes = None
    mood = None

    for _, _, attr_name, value in sorted(matches, key=lambda x: x[0]):
        if attr_name == "bucket":
            bucket_raw = value
            _, short_name = resolve_bucket(value)
            if short_name is None:
                available = list_available_buckets()
                return {"command": command, "content": remaining, "bucket": None,
                        "energy": None, "duration": None, "source": None,
                        "urgency": None, "notes": None, "mood": None,
                        "adventure": None,
                        "error": f"未找到桶 '{value}'。可用桶: {', '.join(available)}"}
            bucket = short_name
        elif attr_name == "energy":
            energy_map = {"h": "high", "m": "medium", "l": "low"}
            energy = energy_map[value.lower()]
        elif attr_name == "duration":
            duration = int(value)
        elif attr_name == "source":
            source = value
        elif attr_name == "urgency":
            urgency_map = {"now": "Now", "thisweek": "ThisWeek", "later": "Later"}
            urgency = urgency_map[value.lower()]
        elif attr_name == "note_q":
            notes = value
        elif attr_name == "note_w":
            if notes is None:  # quoted note takes priority
                notes = value
        elif attr_name == "mood":
            mood_map = {"great": "Great", "good": "Good", "neutral": "Neutral",
                         "low": "Low", "terrible": "Terrible"}
            mood = mood_map[value.lower()]

    # ---- Validate minimum requirements ----
    write_commands = {"log", "idea", "habit"}
    if command in write_commands and not content:
        labels = {"log": "活动内容", "idea": "灵感内容", "habit": "习惯名称"}
        return {"command": command, "content": None, "bucket": bucket,
                "energy": energy, "duration": duration, "source": source,
                "urgency": urgency, "notes": notes, "mood": mood,
                "adventure": None,
                "error": f"请提供{labels[command]}，例如: os {command} 晨跑5公里 @身体"}

    return {
        "command": command,
        "content": content,
        "bucket": bucket,
        "energy": energy,
        "duration": duration,
        "source": source,
        "urgency": urgency,
        "notes": notes,
        "mood": mood,
        "adventure": None,
        "error": None,
    }


# ---- CLI test entry ----

if __name__ == "__main__":
    import sys
    msg = sys.argv[1] if len(sys.argv) > 1 else "os l 晨跑5公里 @身体 energy:h duration:30"
    result = parse(msg)
    import json as _json
    print(_json.dumps(result, ensure_ascii=False, indent=2))
