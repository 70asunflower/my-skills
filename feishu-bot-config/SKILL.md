---
name: feishu-bot-config
description: Manage Feishu (Lark) bot integrations with OpenClaw agents — add new bots, configure App ID/App Secret, set up routing, list configured bots, and troubleshoot connectivity. Use whenever the user mentions Feishu bots, wants to connect a Feishu app to an agent, configure channels or bindings, troubleshoot a bot not responding, or manage pairing.
---

# Feishu Bot Configuration Management

## Workflow

### Adding a New Feishu Bot

Run the automated configuration script:

```bash
scripts/add_feishu_bot.py <agent_name> <app_id> <app_secret>
```

The script handles three steps:
1. Creates `.env` file with credentials in `~/.openclaw/workspace-<agent_name>/`
2. Adds the Feishu account to `channels.feishu.accounts` in `~/.openclaw/openclaw.json`
3. Adds a binding route to connect the account to the specified agent

After the script completes, remind the user of the remaining manual steps:

1. Restart Gateway: `openclaw gateway restart`
2. User starts a conversation with the bot in Feishu to get a pairing code
3. Approve the pairing: `openclaw pairing approve feishu <CODE>`

### Listing Configured Bots

Run the listing script to see all configured bots and their binding status:

```bash
scripts/list_feishu_bots.py
```

This reads `~/.openclaw/openclaw.json` and shows each bot's App ID, default agent, and whether the binding route is present.

### Troubleshooting

If a bot doesn't respond, check these in order — use `list_feishu_bots.py` first to quickly spot missing bindings:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Bot no response | Missing `channels.feishu.accounts` config | Add account with script or manually |
| Bot no response | Missing `bindings` route | Add binding with script |
| Bot no response | Gateway not restarted | `openclaw gateway restart` |
| Pairing required | User hasn't been approved | `openclaw pairing approve feishu <CODE>` |
| Credential error | Wrong App Secret | Check/fix `.env` file |

For the full manual configuration checklist, see `references/checklist.md`.
