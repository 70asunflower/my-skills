#!/usr/bin/env python3
"""
Add Feishu Bot configuration to OpenClaw.
This script updates openclaw.json with the necessary configuration for a new Feishu Bot.
"""

import json
import sys
import os
from pathlib import Path

def load_openclaw_config():
    """Load openclaw.json configuration."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f), config_path

def save_openclaw_config(config, config_path):
    """Save openclaw.json configuration."""
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Updated: {config_path}")

def create_env_file(agent_name, app_id, app_secret):
    """Create .env file for the agent."""
    workspace = Path.home() / ".openclaw" / f"workspace-{agent_name}"
    env_path = workspace / ".env"
    
    # Create workspace if it doesn't exist
    workspace.mkdir(parents=True, exist_ok=True)
    
    env_content = f"""# Feishu Bot Configuration
FEISHU_APP_ID={app_id}
FEISHU_APP_SECRET={app_secret}
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"Created: {env_path}")

def add_channel_account(config, app_id, app_secret, agent_name):
    """Add Feishu account to channels configuration."""
    if 'channels' not in config:
        config['channels'] = {}
    
    if 'feishu' not in config['channels']:
        config['channels']['feishu'] = {
            "enabled": True,
            "connectionMode": "websocket",
            "domain": "feishu",
            "accounts": {}
        }
    
    if 'accounts' not in config['channels']['feishu']:
        config['channels']['feishu']['accounts'] = {}
    
    config['channels']['feishu']['accounts'][app_id] = {
        "appId": app_id,
        "appSecret": app_secret,
        "defaultAgent": agent_name
    }
    
    print(f"Added channel account: {app_id} -> {agent_name}")

def add_binding(config, app_id, agent_name):
    """Add binding route to configuration."""
    if 'bindings' not in config:
        config['bindings'] = []
    
    # Check if binding already exists
    for binding in config['bindings']:
        if (binding.get('type') == 'route' and 
            binding.get('agentId') == agent_name and
            binding.get('match', {}).get('accountId') == app_id):
            print(f"Binding already exists: {app_id} -> {agent_name}")
            return
    
    config['bindings'].append({
        "type": "route",
        "agentId": agent_name,
        "match": {
            "channel": "feishu",
            "accountId": app_id
        }
    })
    
    print(f"Added binding: {app_id} -> {agent_name}")

def main():
    if len(sys.argv) < 4:
        print("Usage: add_feishu_bot.py <agent_name> <app_id> <app_secret>", file=sys.stderr)
        print("Example: add_feishu_bot.py ceo_orchestrator cli_a94504d586b85bc2 qINKS7Lezl3Kkp7fct2SkeeU3ACTnfa4", file=sys.stderr)
        sys.exit(1)
    
    agent_name = sys.argv[1]
    app_id = sys.argv[2]
    app_secret = sys.argv[3]
    
    print(f"Adding Feishu Bot configuration for agent: {agent_name}")
    print(f"App ID: {app_id}")
    
    # Load config
    config, config_path = load_openclaw_config()
    
    # Create .env file
    create_env_file(agent_name, app_id, app_secret)
    
    # Add channel account
    add_channel_account(config, app_id, app_secret, agent_name)
    
    # Add binding
    add_binding(config, app_id, agent_name)
    
    # Save config
    save_openclaw_config(config, config_path)
    
    print("\n✅ Configuration complete!")
    print("\nNext steps:")
    print("1. Restart Gateway: openclaw gateway restart")
    print("2. In Feishu, start a conversation with the bot")
    print("3. Approve the pairing request: openclaw pairing approve feishu <CODE>")

if __name__ == "__main__":
    main()
