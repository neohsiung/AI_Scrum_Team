"""
Helper script to guide you through creating 8 Telegram bots.

Run this interactively: python scripts/setup_telegram_bots.py
"""

ROLES = [
    ("SCRUM_MASTER", "Scrum Master", "scrum_master_bot"),
    ("PRODUCT_OWNER", "Product Owner", "product_owner_bot"),
    ("TECH_LEAD", "Tech Lead", "tech_lead_bot"),
    ("BACKEND", "Backend Developer", "backend_dev_bot"),
    ("FRONTEND", "Frontend Developer", "frontend_dev_bot"),
    ("APP", "App Developer", "app_dev_bot"),
    ("QA", "QA Engineer", "qa_engineer_bot"),
    ("DEVOPS", "DevOps Engineer", "devops_eng_bot"),
]


def main():
    print("=" * 60)
    print("🤖 Telegram Bot Setup Guide for Agent Scrum Team")
    print("=" * 60)
    print()
    print("你需要在 Telegram 中建立 8 個 Bot。")
    print("步驟：")
    print("1. 在 Telegram 搜尋 @BotFather")
    print("2. 對 BotFather 發送 /newbot")
    print("3. 依照提示設定 bot 名稱和 username")
    print("4. 複製 token 到 .env 檔案中")
    print()
    print("建議命名格式（username 必須全球唯一，加上你的前綴）：")
    print()

    env_lines = []
    for env_key, display_name, suggested_suffix in ROLES:
        print(f"  Bot Name: 「{display_name} - AI Scrum Team」")
        print(f"  Username: yourprefix_{suggested_suffix}")
        print(f"  → .env key: TG_TOKEN_{env_key}")
        print()
        env_lines.append(f"TG_TOKEN_{env_key}=<paste_token_here>")

    print("=" * 60)
    print("完成後，將以下內容填入 .env 檔案：")
    print()
    for line in env_lines:
        print(line)

    print()
    print("另外還需要取得你的 Chat ID：")
    print("1. 在 Telegram 搜尋 @userinfobot")
    print("2. 發送任何訊息，它會回覆你的 Chat ID")
    print("3. 填入 .env: TG_OWNER_CHAT_ID=<your_chat_id>")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
