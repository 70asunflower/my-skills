#!/usr/bin/env python3
"""
List all configured Feishu Bots.
"""

import json
import sys
from pathlib import Path

def load_openclaw_config():
    """Load openclaw.json configuration."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse config: {e}", file=sys.stderr)
            sys.exit(1)

def list_bots(config):
    """List all configured Feishu bots."""
    feishu_config = config.get('channels', {}).get('feishu', {})
    accounts = feishu_config.get('accounts', {})
    
    if not accounts:
        print("No Feishu bots configured.")
        return
    
    print("\n📱 Configured Feishu Bots:\n")
    print(f"{'App ID':<35} {'Agent':<25} {'Status'}")
    print("-" * 80)
    
    for app_id, account in accounts.items():
        if app_id == 'default':
            continue
        agent = account.get('defaultAgent', 'N/A')
        
        # Check if binding exists
        bindings = config.get('bindings', [])
        has_binding = any(
            b.get('match', {}).get('accountId') == app_id 
            for b in bindings
        )
        
        status = "✅ OK" if has_binding else "⚠️  Missing binding"
        print(f"{app_id:<35} {agent:<25} {status}")
    
    print()

def main():
    config = load_openclaw_config()
    list_bots(config)

if __name__ == "__main__":
    main()
