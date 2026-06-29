"""8+1 Life OS API wrapper — database operations on top of notion_client."""
import os
import json
import sys
import time
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notion_client import api_request, API_KEY

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    """Load Life OS configuration."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_bucket(name):
    """Resolve bucket short name from Chinese or English input.
    
    Keys in config are "中文 English" format (e.g., "赚钱 Earning").
    Matches: full key, Chinese-only, English-only (case-insensitive).

    Args:
        name: Chinese name (赚钱) or English short name (Earning)
    
    Returns:
        (bucket_page_id, english_short_name) tuple, or (None, None)
    """
    config = load_config()
    name_lower = name.strip().lower()

    for key, page_id in config["bucket_page_ids"].items():
        # Exact match on full key
        if key.lower() == name_lower:
            short = key.split()[-1]
            return page_id, short

    for key, page_id in config["bucket_page_ids"].items():
        parts = key.split()
        # Match just Chinese or just English part
        for part in parts:
            if part.lower() == name_lower:
                short = parts[-1]
                return page_id, short

    return None, None


def get_bucket_label(page_id):
    """Get display label (e.g. '身体 Body') from a bucket page ID."""
    config = load_config()
    for key, bid in config["bucket_page_ids"].items():
        if bid == page_id:
            return key
    return "?"


def list_available_buckets():
    """Return list of bucket display labels for error messages."""
    config = load_config()
    return list(config["bucket_page_ids"].keys())


def create_page(database_id, properties):
    """Create a page in a Notion database."""
    body = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    result = api_request("POST", "pages", body)
    if result.get("error"):
        print(f"ERROR|NETWORK: {result.get('message', '')}")
        return None
    return result["id"]


def update_page(page_id, properties):
    """Update a page's properties."""
    body = {"properties": properties}
    result = api_request("PATCH", f"pages/{page_id}", body)
    if result.get("error"):
        print(f"ERROR|NETWORK: {result.get('message', '')}")
        return False
    return True


def query_database(database_id, filter_dict=None, sorts=None, page_size=100):
    """Query a Notion database with optional filter and sort."""
    body = {"page_size": page_size}
    if filter_dict:
        body["filter"] = filter_dict
    if sorts:
        body["sorts"] = sorts
    result = api_request("POST", f"databases/{database_id}/query", body)
    if result.get("error"):
        print(f"ERROR|NETWORK: {result.get('message', '')}")
        return []
    return result.get("results", [])


def build_title(content):
    """Build title property value."""
    return {"title": [{"text": {"content": content}}]}


def build_rich_text(text):
    """Build rich_text property value."""
    return {"rich_text": [{"text": {"content": text}}]}


def build_date(date_str):
    """Build date property value."""
    return {"date": {"start": date_str}}


def build_select(name):
    """Build select property value."""
    return {"select": {"name": name}}


def build_relation(page_ids):
    """Build relation property value."""
    return {"relation": [{"id": pid} for pid in page_ids]}


def build_number(value):
    """Build number property value."""
    return {"number": value}


def build_checkbox(checked):
    """Build checkbox property value."""
    return {"checkbox": checked}


def get_week_range(offset_weeks=0):
    """Get the date range for a given week offset (0=this week, -1=last week).
    
    Returns:
        (week_id, start_date, end_date) tuple
    """
    today = datetime.now()
    # Adjust to Monday
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset_weeks)
    sunday = monday + timedelta(days=6)
    week_id = monday.strftime("%G-W%V")
    return week_id, monday, sunday
