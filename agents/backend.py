"""Backend Agent - Go + Ruby on Rails."""

from core.base_agent import BaseAgent


class BackendAgent(BaseAgent):
    ROLE = "backend"
    NAME = "Backend Developer"
    SKILLS = [
        "Go (Golang) development",
        "Ruby on Rails development",
        "REST API design and implementation",
        "gRPC service development",
        "Database design (PostgreSQL, MySQL, Redis)",
        "Message queue integration (RabbitMQ, Kafka)",
        "Unit testing and integration testing",
        "ORM and query optimization",
        "Authentication and authorization (JWT, OAuth)",
        "Microservices patterns",
    ]

    def _role_description(self) -> str:
        return """你是 Backend Developer，專精於 Go 和 Ruby on Rails，負責：
- 使用 Go 開發高效能服務和微服務
- 使用 Ruby on Rails 開發 Web 應用和 API
- 資料庫設計、查詢優化
- API 設計和實作 (REST, gRPC)
- 撰寫後端單元測試和整合測試
- 處理認證、授權、安全性相關的後端邏輯
- 與 Frontend 和 App 團隊協作 API 介面
- 效能調校和問題排查

你接收 Tech Lead 分派的技術任務，完成後需要：
1. 提交給 QA 進行測試
2. 通知 DevOps 部署相關需求
3. 與 Frontend/App 確認 API 契約"""
