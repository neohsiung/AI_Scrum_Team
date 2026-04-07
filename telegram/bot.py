"""
Telegram Bot integration - each agent has its own bot.

Each agent runs an independent Telegram bot that:
- Receives messages from the human owner
- Sends responses back
- Handles escalation messages
- Supports special commands (/status, /memory, /growth, /task, /consensus)
"""

import json

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import structlog

from config.settings import settings
from core.base_agent import BaseAgent
from core.consensus import consensus_manager

logger = structlog.get_logger()


class AgentTelegramBot:
    """Telegram bot wrapper for a single agent."""

    def __init__(self, agent: BaseAgent, token: str):
        self.agent = agent
        self.token = token
        self.app: Application | None = None
        self._agents_registry: dict[str, BaseAgent] = {}

    def set_agents_registry(self, registry: dict[str, BaseAgent]):
        """Set reference to all agents for A2A and consensus."""
        self._agents_registry = registry

    async def setup(self):
        """Build and configure the Telegram application."""
        self.app = Application.builder().token(self.token).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("memory", self._cmd_memory))
        self.app.add_handler(CommandHandler("growth", self._cmd_growth))
        self.app.add_handler(CommandHandler("task", self._cmd_task))
        self.app.add_handler(CommandHandler("consensus", self._cmd_consensus))
        self.app.add_handler(CommandHandler("ask", self._cmd_ask_agent))
        self.app.add_handler(CommandHandler("relay", self._cmd_relay))
        self.app.add_handler(CommandHandler("broadcast", self._cmd_broadcast))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        logger.info("telegram_bot_setup", agent=self.agent.NAME)

    async def start(self):
        """Start polling for messages."""
        if self.app:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            logger.info("telegram_bot_started", agent=self.agent.NAME)

    async def stop(self):
        """Stop the bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    # ---- Command Handlers ----

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = f"""👋 你好！我是 **{self.agent.NAME}**

我是你的 AI Scrum Team 成員，專責：
{chr(10).join(f'• {s}' for s in self.agent.SKILLS[:5])}

**可用指令：**
/help - 查看所有指令
/status - 查看我的狀態
/memory - 查看我的記憶
/growth - 查看我的成長記錄
/task <描述> - 派發任務給我
/consensus <議題> - 發起團隊共識討論
/ask <角色> <訊息> - 請我問其他成員

直接傳訊息給我就可以對話了！"""
        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """**指令列表：**

💬 直接傳訊息 - 與我對話/諮詢
/status - 我的當前狀態
/memory [類型] - 查看記憶 (learning/skill/decision/feedback/growth/task)
/growth - 技能成長記錄
/task <描述> - 派發任務
/consensus <議題> - 發起團隊共識投票
/ask <角色> <訊息> - 透過我向其他成員溝通

**角色代碼：** scrum\\_master, product\\_owner, tech\\_lead, backend, frontend, app, qa, devops"""
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        growth = await self.agent.long_memory.get_growth_summary()
        recent_memories = await self.agent.long_memory.recall(limit=3)

        status = f"**{self.agent.NAME} 狀態報告**\n\n"
        status += f"🎯 角色: {self.agent.ROLE}\n"
        status += f"🧠 短期記憶: {len(self.agent.short_memory._buffer)} 條訊息\n"

        if growth:
            status += "\n📈 **技能等級：**\n"
            for g in growth:
                level_bar = "█" * int(g["level"] * 10) + "░" * (10 - int(g["level"] * 10))
                status += f"  {g['skill_area']}: [{level_bar}] {g['level']:.1f}\n"

        if recent_memories:
            status += "\n📝 **最近記憶：**\n"
            for m in recent_memories:
                status += f"  • [{m['memory_type']}] {m['content'][:80]}...\n"

        await update.message.reply_text(status, parse_mode="Markdown")

    async def _cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        memory_type = args[0] if args else None

        from memory.memory_store import MemoryType

        mt = None
        if memory_type:
            try:
                mt = MemoryType(memory_type)
            except ValueError:
                await update.message.reply_text(
                    f"未知的記憶類型。可用: {', '.join(m.value for m in MemoryType)}"
                )
                return

        memories = await self.agent.long_memory.recall(memory_type=mt, limit=10)

        if not memories:
            await update.message.reply_text("目前沒有相關記憶。")
            return

        text = f"**{self.agent.NAME} 的記憶：**\n\n"
        for m in memories:
            text += f"• [{m['memory_type']}] {m['content'][:150]}\n"
            text += f"  重要性: {m['importance']:.1f} | 時間: {m['timestamp']}\n\n"

        await update.message.reply_text(text[:4000], parse_mode="Markdown")

    async def _cmd_growth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        growth = await self.agent.long_memory.get_growth_summary()

        if not growth:
            await update.message.reply_text("目前沒有成長記錄。持續與我互動，我會不斷學習成長！")
            return

        text = f"**{self.agent.NAME} 成長記錄：**\n\n"
        for g in growth:
            level_bar = "█" * int(g["level"] * 10) + "░" * (10 - int(g["level"] * 10))
            text += f"📊 **{g['skill_area']}**\n"
            text += f"   等級: [{level_bar}] {g['level']:.1f}/1.0\n"
            text += f"   {g['description']}\n\n"

        await update.message.reply_text(text[:4000], parse_mode="Markdown")

    async def _cmd_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("用法: /task <任務描述>")
            return

        task_desc = " ".join(context.args)
        await update.message.reply_text(f"📋 收到任務，正在處理中...\n\n任務: {task_desc}")

        task = {
            "description": task_desc,
            "assigned_to": self.agent.ROLE,
            "source": "human_owner",
        }
        response = await self.agent.receive_task(task)
        await update.message.reply_text(response[:4000])

    async def _cmd_consensus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("用法: /consensus <議題描述>")
            return

        topic = " ".join(context.args)
        await update.message.reply_text(
            f"🗳 發起共識討論...\n\n議題: {topic}\n參與者: 全體成員"
        )

        participants = list(self._agents_registry.keys())

        # Set escalation callback to send to owner
        async def escalate_to_owner(msg: str):
            await update.message.reply_text(msg[:4000])

        consensus_manager.set_escalation_callback(escalate_to_owner)

        result = await consensus_manager.start_consensus(
            topic=topic,
            initiator=self.agent.ROLE,
            participants=participants,
            agents_registry=self._agents_registry,
        )
        await update.message.reply_text(result[:4000])

    async def _cmd_ask_agent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("用法: /ask <角色> <訊息>\n例如: /ask backend 這個 API 的效能如何？")
            return

        target_role = context.args[0]
        message = " ".join(context.args[1:])

        if target_role not in self._agents_registry:
            await update.message.reply_text(
                f"找不到角色: {target_role}\n"
                f"可用角色: {', '.join(self._agents_registry.keys())}"
            )
            return

        await update.message.reply_text(
            f"📨 正在向 {target_role} 傳送訊息..."
        )

        # Send A2A message
        await self.agent.send_a2a(target_role, message, msg_type="request")
        await update.message.reply_text(
            f"✅ 已透過 A2A 向 {target_role} 發送訊息。"
        )

    async def _cmd_relay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Human Proxy exclusive: relay a message to an agent with intent analysis."""
        if self.agent.ROLE != "human_proxy":
            await update.message.reply_text("此指令僅限 Human Proxy 使用。")
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "用法: /relay <角色> <訊息>\n"
                "例如: /relay tech_lead 我們需要重構認證模組\n\n"
                "我會幫你分析意圖、智慧轉達、並回報結果。"
            )
            return

        target_role = context.args[0]
        raw_message = " ".join(context.args[1:])

        if target_role not in self._agents_registry:
            await update.message.reply_text(
                f"找不到角色: {target_role}\n"
                f"可用角色: {', '.join(self._agents_registry.keys())}"
            )
            return

        await update.message.reply_text(f"🔄 正在分析您的意圖並轉達給 {target_role}...")

        # Step 1: Use Human Proxy's Claude to analyze intent and craft the relay message
        analysis_prompt = (
            f"老闆要我把以下訊息傳給 {target_role}：\n\n"
            f"「{raw_message}」\n\n"
            f"請你：\n"
            f"1. 分析老闆為什麼要問這個（深層動機）\n"
            f"2. 將訊息轉化為更具體、對 {target_role} 更有幫助的版本\n"
            f"3. 說明你為什麼這樣轉達\n\n"
            f"格式：\n"
            f"📋 **轉達內容**：[你轉化後要傳給 {target_role} 的訊息]\n\n"
            f"🧠 **意圖分析**：\n"
            f"- 老闆為什麼這樣問：[分析]\n"
            f"- 我為什麼這樣轉達：[理由]\n\n"
            f"💡 **建議**：[如果有的話]"
        )

        proxy_analysis = await self.agent.chat(analysis_prompt)

        # Send analysis back to owner first
        for i in range(0, len(proxy_analysis), 4000):
            await update.message.reply_text(proxy_analysis[i : i + 4000])

        # Step 2: Actually relay to the target agent via A2A
        await self.agent.send_a2a(
            target_role,
            f"[來自老闆，由 Human Proxy 轉達]\n{raw_message}",
            msg_type="request",
        )
        await update.message.reply_text(f"✅ 已轉達給 {target_role}。")

    async def _cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Human Proxy exclusive: broadcast a message to all or selected agents."""
        if self.agent.ROLE != "human_proxy":
            await update.message.reply_text("此指令僅限 Human Proxy 使用。")
            return

        if not context.args:
            await update.message.reply_text(
                "用法: /broadcast <訊息>\n"
                "向所有團隊成員廣播訊息。"
            )
            return

        message = " ".join(context.args)
        targets = [r for r in self._agents_registry if r != "human_proxy"]

        await update.message.reply_text(
            f"📢 正在向 {len(targets)} 位團隊成員廣播..."
        )

        for role in targets:
            await self.agent.send_a2a(
                role,
                f"[老闆廣播，由 Human Proxy 轉達]\n{message}",
                msg_type="request",
            )

        await update.message.reply_text(
            f"✅ 已廣播給：{', '.join(targets)}"
        )

    # ---- Message Handler ----

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages - main conversation."""
        user_message = update.message.text

        # Verify it's from the owner
        if settings.telegram_owner_chat_id and str(update.effective_chat.id) != settings.telegram_owner_chat_id:
            await update.message.reply_text("⛔ 未授權的使用者。")
            return

        response = await self.agent.chat(user_message)

        # Split long messages
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i : i + 4000])


def get_token_for_role(role: str) -> str:
    """Get the Telegram bot token for a given role."""
    token_map = {
        "scrum_master": settings.telegram_token_scrum_master,
        "product_owner": settings.telegram_token_product_owner,
        "tech_lead": settings.telegram_token_tech_lead,
        "backend": settings.telegram_token_backend,
        "frontend": settings.telegram_token_frontend,
        "app": settings.telegram_token_app,
        "qa": settings.telegram_token_qa,
        "devops": settings.telegram_token_devops,
        "uiux": settings.telegram_token_uiux,
        "human_proxy": settings.telegram_token_human_proxy,
    }
    return token_map.get(role, "")
