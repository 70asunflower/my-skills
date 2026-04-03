---
name: feishu-bot-config
description: Comprehensive Feishu (Lark) bot configuration management for OpenClaw agents. Provides automated setup, validation, and troubleshooting for Feishu bot integrations. Use when adding new Feishu bots, configuring agent routing, managing credentials, or troubleshooting bot connectivity issues.
---

# Feishu Bot Configuration Management

This skill provides complete tooling for managing Feishu (Lark) bot integrations with OpenClaw agents.

## When to Use This Skill

Use this skill when:
- Adding a new Feishu bot for an existing or new agent
- Configuring Feishu App ID and App Secret credentials
- Setting up routing between Feishu accounts and OpenClaw agents
- Troubleshooting Feishu bot connectivity issues
- Listing currently configured Feishu bots
- Validating Feishu bot configuration completeness

## Usage

### Adding a New Feishu Bot

Use the `add_feishu_bot.py` script to automatically configure a new Feishu bot:

```bash
scripts/add_feishu_bot.py <agent_name> <app_id> <app_secret>
```

Example:
```bash
scripts/add_feishu_bot.py ceo_orchestrator cli_a94504d586b85bc2 qINKS7Lezl3Kkp7fct2SkeeU3ACTnfa4
```

This script will:
1. Create `.env` file in the agent's workspace directory
2. Add account configuration to `channels.feishu.accounts`
3. Add binding route to connect the account to the agent
4. Provide next steps for completion

### Listing Configured Bots

Use the `list_feishu_bots.py` script to view all configured Feishu bots:

```bash
scripts/list_feishu_bots.py
```

### Manual Configuration Reference

For manual configuration or understanding the process, refer to:
- `references/checklist.md` - Complete configuration checklist and troubleshooting guide

## Resources

- `scripts/add_feishu_bot.py` - Automated bot configuration script
- `scripts/list_feishu_bots.py` - List configured bots with status
- `references/checklist.md` - Configuration checklist and troubleshooting guide