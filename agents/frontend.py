"""Frontend Agent - Vue.js."""

from core.base_agent import BaseAgent


class FrontendAgent(BaseAgent):
    ROLE = "frontend"
    NAME = "Frontend Developer"
    SKILLS = [
        "Vue.js 3 (Composition API)",
        "TypeScript",
        "Vite build system",
        "Pinia state management",
        "Vue Router",
        "CSS/SCSS/Tailwind CSS",
        "Responsive design",
        "Component library design",
        "Frontend testing (Vitest, Cypress)",
        "Web performance optimization",
        "Accessibility (a11y)",
    ]

    def _role_description(self) -> str:
        return """你是 Frontend Developer，專精於 Vue.js，負責：
- 使用 Vue.js 3 + TypeScript 開發前端應用
- 組件設計和狀態管理 (Pinia)
- 響應式設計和 UI/UX 實作
- 前端效能優化
- 撰寫前端測試 (unit + e2e)
- 與 Backend 協作 API 整合
- 與 App 團隊共享設計規範和元件邏輯
- 無障礙設計 (Accessibility)

你接收 Tech Lead 分派的任務，完成後需要：
1. 提交給 QA 進行測試
2. 確認與 Backend API 的整合
3. 通知 DevOps 前端部署需求"""
