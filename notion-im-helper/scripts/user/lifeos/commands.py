"""8+1 Life OS commands — daily log, ideas, habits, weekly review."""
import os
import sys
import time
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from .client import (
    load_config, resolve_bucket, get_bucket_label,
    create_page, update_page, query_database,
    build_title, build_rich_text, build_date, build_select,
    build_relation, build_number, build_checkbox,
    get_week_range,
)


# ===== Daily Log =====

def cmd_log(content, bucket_name=None, energy=None, duration=None, date_str=None, notes=None, mood=None, adventure_id=None):
    """Create a daily log entry.
    
    Examples:
        lifeos log "晨跑5公里" --bucket 身体 --energy high --duration 30
        lifeos log "读论文" --bucket learning
        lifeos l "写代码" -b earning --mood good
    """
    config = load_config()

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    properties = {
        "Content": build_title(content),
        "Date": build_date(date_str),
    }

    if bucket_name:
        bucket_id, short = resolve_bucket(bucket_name)
        if bucket_id:
            properties["Bucket"] = build_relation([bucket_id])
        else:
            print(f"WARN|未找到桶 '{bucket_name}'，可用的桶: {', '.join(config['bucket_page_ids'].keys())}")
            return

    if energy:
        energy_map = {"h": "High", "m": "Medium", "l": "Low"}
        energy_val = energy_map.get(energy.lower(), energy)
        properties["Energy"] = build_select(energy_val)

    if duration:
        properties["Duration_min"] = build_number(int(duration))

    if notes:
        properties["Notes"] = build_rich_text(notes)

    if mood:
        mood_values = ["Great", "Good", "Neutral", "Low", "Terrible"]
        mood_val = mood if mood in mood_values else mood.capitalize()
        properties["Mood"] = build_select(mood_val)

    if adventure_id:
        properties["Adventure"] = build_relation([adventure_id])

    page_id = create_page(config["databases"]["daily_log"], properties)
    if page_id:
        bucket_label = f" ({bucket_name})" if bucket_name else ""
        print(f"OK|已记录每日活动: {content}{bucket_label}")


# ===== Ideas =====

def cmd_idea(content, bucket_name=None, source=None, urgency="Later"):
    """Quick-capture an idea to the Idea Inbox.
    
    Examples:
        lifeos idea "试试用 Obsidian 做知识图谱" --bucket learning
        lifeos i "周末去爬山" -b play --urgency now
    """
    config = load_config()

    properties = {
        "Idea": build_title(content),
        "IdeaStatus": build_select("Collected"),
    }

    if bucket_name:
        bucket_id, short = resolve_bucket(bucket_name)
        if bucket_id:
            properties["Bucket"] = build_relation([bucket_id])

    if source:
        source_map = {
            "book": "Book", "podcast": "Podcast", "conversation": "Conversation",
            "spontaneous": "Spontaneous", "internet": "Internet", "ai": "AI",
        }
        source_val = source_map.get(source.lower(), source)
        properties["Source"] = build_select(source_val)

    if urgency:
        urgency_map = {"now": "Now", "thisweek": "ThisWeek", "later": "Later"}
        urgency_val = urgency_map.get(urgency.lower(), urgency)
        properties["Urgency"] = build_select(urgency_val)

    page_id = create_page(config["databases"]["ideas"], properties)
    if page_id:
        bucket_label = f" [{bucket_name}]" if bucket_name else ""
        print(f"OK|已记录灵感: {content}{bucket_label}")


# ===== Habits =====

def cmd_habit_check(habit_name, date_str=None):
    """Log a habit completion for today.
    
    Examples:
        lifeos habit check "冥想"
        lifeos h c "跑步"
    """
    config = load_config()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Find the habit by name
    habits = query_database(
        config["databases"]["habits"],
        filter_dict={"property": "Habit", "title": {"contains": habit_name}}
    )
    
    if not habits:
        print(f"ERROR|未找到习惯 '{habit_name}'")
        return
    
    habit = habits[0]
    habit_id = habit["id"]
    habit_title = habit["properties"]["Habit"]["title"][0]["plain_text"]

    # Check if already logged today
    today_logs = query_database(
        config["databases"]["habit_log"],
        filter_dict={
            "and": [
                {"property": "Habit", "relation": {"contains": habit_id}},
                {"property": "Date", "date": {"equals": date_str}},
            ]
        }
    )

    if today_logs:
        # Update existing entry
        log_id = today_logs[0]["id"]
        update_page(log_id, {"Completed": build_checkbox(True)})
    else:
        # Create new entry
        create_page(config["databases"]["habit_log"], {
            "LogEntry": build_title(f"{habit_title} - {date_str}"),
            "Date": build_date(date_str),
            "Habit": build_relation([habit_id]),
            "Completed": build_checkbox(True),
        })

    print(f"OK|习惯打卡: {habit_title} ✅")


def cmd_habit_streaks():
    """Update all habit streaks."""
    config = load_config()
    
    active_habits = query_database(
        config["databases"]["habits"],
        filter_dict={"property": "HabitStatus", "select": {"equals": "Active"}}
    )

    for habit in active_habits:
        habit_id = habit["id"]
        habit_name = habit["properties"]["Habit"]["title"][0]["plain_text"]

        # Get all completed logs sorted by date desc
        logs = query_database(
            config["databases"]["habit_log"],
            filter_dict={"property": "Habit", "relation": {"contains": habit_id}},
            sorts=[{"property": "Date", "direction": "descending"}]
        )

        # Calculate streak
        completed_dates = set()
        for log in logs:
            if log["properties"].get("Completed", {}).get("checkbox"):
                d = log["properties"]["Date"]["date"]["start"]
                completed_dates.add(d)

        streak = 0
        check_date = datetime.now().date()
        while check_date.isoformat() in completed_dates:
            streak += 1
            check_date -= timedelta(days=1)

        old_longest = habit["properties"].get("LongestStreak", {}).get("number", 0) or 0
        total = len(completed_dates)

        update_page(habit_id, {
            "CurrentStreak": build_number(streak),
            "LongestStreak": build_number(max(streak, old_longest)),
            "StreakUpdated": build_date(datetime.now().strftime("%Y-%m-%d")),
        })
        print(f"  {habit_name}: streak={streak}, longest={max(streak, old_longest)}, total={total}")

    print("OK|所有习惯 streak 已更新")


# ===== Ideas List =====

def cmd_ideas_list(status="Collected"):
    """List ideas by status."""
    config = load_config()
    ideas = query_database(
        config["databases"]["ideas"],
        filter_dict={"property": "IdeaStatus", "select": {"equals": status}},
        sorts=[{"property": "Urgency", "direction": "ascending"}]
    )

    if not ideas:
        print(f"OK|没有状态为 '{status}' 的灵感")
        return

    print(f"\n灵感 ({status}):")
    for i, idea in enumerate(ideas, 1):
        props = idea["properties"]
        title = props["Idea"]["title"][0]["plain_text"] if props["Idea"]["title"] else "?"
        bucket_rel = props.get("Bucket", {}).get("relation", [])
        bucket_name = ""
        if bucket_rel:
            bucket_name = f" [{get_bucket_label(bucket_rel[0]['id'])}]"
        urgency = props.get("Urgency", {}).get("select", {})
        urgency_name = urgency.get("name", "") if urgency else ""
        print(f"  {i}. {title}{bucket_name}" + (f" ⚡{urgency_name}" if urgency_name else ""))


# ===== Daily Log Summary =====

def cmd_log_today():
    """Show today's logged activities."""
    config = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    
    logs = query_database(
        config["databases"]["daily_log"],
        filter_dict={"property": "Date", "date": {"equals": today}}
    )

    if not logs:
        print(f"OK|今天还没有记录活动")
        return

    print(f"\n今日活动 ({today}):")
    total_min = 0
    for log in logs:
        props = log["properties"]
        content = props["Content"]["title"][0]["plain_text"] if props["Content"]["title"] else "?"
        bucket_rel = props.get("Bucket", {}).get("relation", [])
        bucket_name = ""
        if bucket_rel:
            bucket_name = f" [{get_bucket_label(bucket_rel[0]['id'])}]"
        duration = props.get("Duration_min", {}).get("number", 0) or 0
        total_min += duration
        energy = props.get("Energy", {}).get("select", {})
        energy_str = f" ⚡{energy.get('name', '')}" if energy else ""
        duration_str = f" ({duration}min)" if duration else ""
        print(f"  • {content}{bucket_name}{duration_str}{energy_str}")

    if total_min > 0:
        print(f"  总计: {total_min}分钟")


# ===== Daily Log History =====

def cmd_log_history(days=7, bucket_name=None):
    """Show daily log history."""
    config = load_config()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    filter_dict = {"property": "Date", "date": {"on_or_after": since}}
    
    if bucket_name:
        bucket_id, short = resolve_bucket(bucket_name)
        if bucket_id:
            filter_dict = {
                "and": [
                    filter_dict,
                    {"property": "Bucket", "relation": {"contains": bucket_id}},
                ]
            }

    logs = query_database(
        config["databases"]["daily_log"],
        filter_dict=filter_dict,
        sorts=[{"property": "Date", "direction": "descending"}]
    )

    if not logs:
        print(f"OK|近 {days} 天没有记录")
        return

    print(f"\n近{days}天活动:")
    by_date = defaultdict(list)
    for log in logs:
        props = log["properties"]
        d = props["Date"]["date"]["start"]
        content = props["Content"]["title"][0]["plain_text"] if props["Content"]["title"] else "?"
        bucket_rel = props.get("Bucket", {}).get("relation", [])
        bucket_label = ""
        if bucket_rel:
            bucket_label = f"[{get_bucket_label(bucket_rel[0]['id'])}] "
        by_date[d].append(f"{bucket_label}{content}")

    for d in sorted(by_date.keys(), reverse=True):
        print(f"  {d}:")
        for entry in by_date[d]:
            print(f"    • {entry}")
