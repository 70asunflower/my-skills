"""Check Notion configuration on first use."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from notion_client import check_config


def show_guide():
    return """📝 首次使用 Notion 助手，需要 2 分钟做个配置~

1️⃣ 创建 Notion Integration
   → 打开 https://www.notion.so/my-integrations
   → 点击 "Create new integration"
   → 填写名称（如 "notion-im-helper"），选择你的工作空间
   → 提交后复制 Internal Integration Token（以 ntn_ 或 secret_ 开头）

2️⃣ 获取页面 ID
   → 打开你要写入的 Notion 页面
   → 从 URL 中复制最后的 32 位字符

3️⃣ 配置到 OpenClaw
   openclaw config set env.NOTION_API_KEY "你的密钥"
   openclaw config set env.NOTION_PARENT_PAGE_ID "你的页面ID"
   openclaw gateway restart

4️⃣ 授权 Integration 访问页面
   → 打开你的 Notion 页面 → 点右上角 ··· → Connect to → 选择你的 Integration

配置好了发条消息试试：d 测试一下 ✨"""


result = check_config()
if not result["ok"]:
    code = result["code"]
    if code == "CONFIG":
        print("ERROR|CONFIG")
    elif code == "AUTH":
        print("ERROR|AUTH")
    else:
        print("ERROR|CONFIG")
else:
    print("OK|配置检查通过")
