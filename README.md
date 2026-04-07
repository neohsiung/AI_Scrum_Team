# Agent Scrum Team 🏃

8 個 AI Agent 組成的 Scrum 開發團隊，各自擁有獨立記憶、技能和 Telegram 頻道。

## 架構概覽

```
┌─────────────────────────────────────────────────────────┐
│                    你 (Human Owner)                       │
│              透過 8 個獨立 Telegram Bot 溝通               │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┘
       │      │      │      │      │      │      │
  ┌────▼─┐┌───▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼─┐┌──▼─┐┌─────▼─┐
  │ SM   ││ PO   ││ TL  ││ BE  ││ FE  ││ App││ QA ││DevOps │
  │      ││      ││     ││Go+RR││ Vue ││Flut││    ││       │
  └──┬───┘└──┬───┘└──┬──┘└──┬──┘└──┬──┘└──┬─┘└──┬─┘└──┬────┘
     │       │       │      │      │      │     │     │
     └───────┴───────┴──────┴──────┴──────┴─────┴─────┘
                    A2A Message Bus (Redis)
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    │ (持久記憶)   │
                    └─────────────┘
```

## 角色分工

| 角色 | 職責 | 技術棧 |
|------|------|--------|
| **Scrum Master** | 流程優化、Sprint 管理 | Agile/Scrum |
| **Product Owner** | 產品決策、需求管理 | PRD, User Stories |
| **Tech Lead** | 技術方向、資源分配 | 架構設計 |
| **Backend** | API 與服務開發 | Go + Ruby on Rails |
| **Frontend** | Web 前端 | Vue.js 3 |
| **App** | 行動應用 | Flutter |
| **QA** | 品質保證 | 測試自動化 |
| **DevOps** | 基礎建設與監控 | Docker, K8s, CI/CD |

## 核心功能

- **獨立記憶層**：每個 Agent 有短期記憶（對話 buffer）和長期記憶（SQLite 持久化）
- **A2A 通訊**：Agent 之間透過 Redis pub/sub 互相溝通
- **自主成長**：每次互動後自我反思並記錄學習
- **互助成長**：Agent 可以要求其他 Agent 在特定領域成長
- **共識機制**：團隊討論 3 輪無共識自動升級給人類決策
- **任務流轉**：PO 接收需求 → TL 技術規劃 → 分派給開發 → QA 測試 → DevOps 部署

## 快速開始

### 前置條件

- MacBook Pro M2（或任何有 Docker 的機器）
- Claude Team 帳號的 API Key
- Telegram 帳號

### 1. 建立 Telegram Bots

```bash
python scripts/setup_telegram_bots.py
```

在 Telegram 中找 @BotFather，建立 8 個 Bot，取得各自的 token。

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，填入所有 token
```

### 3. 啟動

```bash
# 使用 Docker Compose（推薦）
docker compose up -d

# 或本地開發
pip install -e .
redis-server &
python main.py
```

### 4. 開始使用

在 Telegram 中分別與 8 個 Bot 對話：
- 直接傳訊息 = 諮詢該角色
- `/task <描述>` = 派發任務
- `/consensus <議題>` = 發起團隊共識
- `/ask <角色> <訊息>` = 透過 A2A 問其他成員
- `/status` = 查看 Agent 狀態
- `/growth` = 查看成長記錄

## 搬移系統

整套系統只需要：
1. 這個 Git repo
2. `.env` 檔案
3. `data/` 目錄（Agent 的持久記憶）

```bash
# 在新機器上
git clone <repo>
cp your-backup/.env .
cp -r your-backup/data/ ./data/
docker compose up -d
```

## 工作流程範例

```
你 → PO (Telegram): 我要做一個用戶登入功能
PO → TL (A2A): 這個需求的技術規劃
TL → Backend (A2A): 實作 API 認證
TL → Frontend (A2A): 實作登入頁面
TL → App (A2A): 實作行動版登入
Backend/FE/App → QA (A2A): 提交測試
QA → DevOps (A2A): 測試通過，可部署
DevOps → 你 (Telegram): 部署完成
```

## 技術細節

- **LLM**: Claude API (Anthropic)
- **記憶**: SQLite (持久) + In-memory deque (短期)
- **通訊**: Redis pub/sub (A2A), Telegram Bot API (Human)
- **容器化**: Docker Compose
- **語言**: Python 3.12
