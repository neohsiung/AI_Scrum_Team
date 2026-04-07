"""
Base Agent class - foundation for all 8 scrum team members.

Each agent has:
- Identity (role, name, system prompt)
- Short-term memory (conversation buffer)
- Long-term memory (persistent SQLite)
- Skills (role-specific capabilities)
- A2A communication (Redis pub/sub)
- Self-growth mechanism
"""

import asyncio
import json
import time

import anthropic
import redis.asyncio as redis
import structlog

from config.settings import settings
from memory.memory_store import (
    LongTermMemory,
    MemoryEntry,
    MemoryType,
    ShortTermMemory,
)

logger = structlog.get_logger()


class BaseAgent:
    """Base class for all scrum team agents."""

    ROLE: str = "base"
    NAME: str = "Base Agent"
    SKILLS: list[str] = []

    def __init__(self):
        self.agent_id = self.ROLE
        self.short_memory = ShortTermMemory(max_messages=50)
        self.long_memory = LongTermMemory(settings.memory_db_path, self.agent_id)
        self.claude = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)
        self._redis: redis.Redis | None = None
        self._running = False
        self._a2a_handlers: dict[str, asyncio.Task] = {}

    async def initialize(self):
        """Initialize agent's memory and connections."""
        await self.long_memory.initialize()
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info("agent_initialized", agent=self.NAME, role=self.ROLE)

    async def shutdown(self):
        """Gracefully shut down the agent."""
        self._running = False
        for task in self._a2a_handlers.values():
            task.cancel()
        if self._redis:
            await self._redis.close()
        logger.info("agent_shutdown", agent=self.NAME)

    # ---- System Prompt Construction ----

    def _build_system_prompt(self) -> str:
        """Build the full system prompt including role, skills, and long-term context."""
        base = f"""You are {self.NAME}, a member of an AI Scrum Team.

## Your Role
{self.ROLE}: {self._role_description()}

## Your Skills
{chr(10).join(f'- {s}' for s in self.SKILLS)}

## Communication Rules
- You communicate in Traditional Chinese (繁體中文) by default.
- You can communicate with other team members via A2A (Agent-to-Agent) messages.
- When you need help from another agent, send them a message through the A2A channel.
- You can request other agents to grow their skills if you notice gaps.
- If the team cannot reach consensus after 3 rounds, escalate to the human owner.

## Self-Growth
- After completing tasks, reflect on what you learned.
- Actively identify areas for improvement.
- When another agent suggests you grow in an area, take it seriously.
- Record your learnings in long-term memory.

## Memory
- You have short-term memory (recent conversation context).
- You have long-term memory (persistent learnings, skills, decisions).
- Use your memories to provide consistent, improving responses.
"""
        return base

    def _role_description(self) -> str:
        """Override in subclass to provide role-specific description."""
        return "Base agent role."

    # ---- Core Chat ----

    async def chat(self, user_message: str, context: dict | None = None) -> str:
        """Process a message from the human owner via Telegram."""
        # Add to short-term memory
        self.short_memory.add("user", user_message, context)

        # Recall relevant long-term memories
        relevant_memories = await self.long_memory.recall(limit=5)
        growth_summary = await self.long_memory.get_growth_summary()

        # Build messages
        system_prompt = self._build_system_prompt()
        if relevant_memories:
            memory_context = "\n## Relevant Long-term Memories\n"
            for m in relevant_memories:
                memory_context += f"- [{m['memory_type']}] {m['content']}\n"
            system_prompt += memory_context

        if growth_summary:
            growth_context = "\n## Your Current Skill Levels\n"
            for g in growth_summary:
                growth_context += f"- {g['skill_area']}: Level {g['level']:.1f} - {g['description']}\n"
            system_prompt += growth_context

        messages = self.short_memory.get_context_for_claude()

        try:
            response = await self.claude.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                system=system_prompt,
                messages=messages,
            )
            reply = response.content[0].text

            # Add to short-term memory
            self.short_memory.add("assistant", reply)

            # Self-reflection: store learnings
            await self._self_reflect(user_message, reply)

            return reply

        except Exception as e:
            logger.error("chat_error", agent=self.NAME, error=str(e))
            return f"[{self.NAME}] 發生錯誤: {str(e)}"

    # ---- A2A Communication ----

    async def send_a2a(self, target_role: str, message: str, msg_type: str = "request"):
        """Send a message to another agent via Redis pub/sub."""
        payload = json.dumps({
            "from": self.ROLE,
            "from_name": self.NAME,
            "to": target_role,
            "type": msg_type,  # request, response, growth_request, consensus
            "content": message,
            "timestamp": time.time(),
        }, ensure_ascii=False)

        channel = f"a2a:{target_role}"
        await self._redis.publish(channel, payload)
        logger.info("a2a_sent", from_agent=self.ROLE, to=target_role, type=msg_type)

        # Store interaction in long-term memory
        await self.long_memory.store(
            MemoryEntry(
                agent_id=self.agent_id,
                memory_type=MemoryType.INTERACTION,
                content=f"Sent to {target_role}: {message}",
                metadata={"target": target_role, "type": msg_type},
            )
        )

    async def start_a2a_listener(self):
        """Start listening for A2A messages."""
        channel = f"a2a:{self.ROLE}"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        self._running = True

        logger.info("a2a_listener_started", agent=self.NAME, channel=channel)

        async for message in pubsub.listen():
            if not self._running:
                break
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    await self._handle_a2a_message(payload)
                except Exception as e:
                    logger.error("a2a_handle_error", agent=self.NAME, error=str(e))

    async def _handle_a2a_message(self, payload: dict):
        """Handle an incoming A2A message."""
        msg_type = payload.get("type", "request")
        from_agent = payload.get("from_name", payload.get("from", "unknown"))
        content = payload.get("content", "")

        logger.info("a2a_received", agent=self.NAME, from_agent=from_agent, type=msg_type)

        # Store in long-term memory
        await self.long_memory.store(
            MemoryEntry(
                agent_id=self.agent_id,
                memory_type=MemoryType.INTERACTION,
                content=f"Received from {from_agent}: {content}",
                metadata={"from": from_agent, "type": msg_type},
            )
        )

        if msg_type == "growth_request":
            await self._handle_growth_request(payload)
        elif msg_type == "consensus":
            await self._handle_consensus(payload)
        else:
            # Process as a regular A2A request - use Claude to generate response
            response = await self._process_a2a_request(payload)
            await self.send_a2a(
                payload["from"], response, msg_type="response"
            )

    async def _process_a2a_request(self, payload: dict) -> str:
        """Use Claude to generate a response to an A2A request."""
        from_agent = payload.get("from_name", payload["from"])
        content = payload["content"]

        messages = [
            {
                "role": "user",
                "content": f"[A2A 訊息來自 {from_agent}]\n{content}\n\n請以你的專業角色回覆。",
            }
        ]

        response = await self.claude.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=self._build_system_prompt(),
            messages=messages,
        )
        return response.content[0].text

    # ---- Growth System ----

    async def _self_reflect(self, user_input: str, response: str):
        """After each interaction, reflect and optionally store learnings."""
        reflection_prompt = f"""Based on this interaction:
User: {user_input[:500]}
Your response: {response[:500]}

Analyze briefly in JSON format:
1. Did you learn something new? (learning: string or null)
2. Should you improve a skill? (skill_to_improve: string or null, current_assessment: float 0-1)
3. Should you ask another team member to grow? (a2a_growth_request: {{target_role: string, area: string}} or null)

Reply ONLY with valid JSON. Use Traditional Chinese for content."""

        try:
            result = await self.claude.messages.create(
                model=settings.claude_model,
                max_tokens=500,
                system="You are a self-reflection engine. Reply only with valid JSON.",
                messages=[{"role": "user", "content": reflection_prompt}],
            )
            reflection = json.loads(result.content[0].text)

            if reflection.get("learning"):
                await self.long_memory.store(
                    MemoryEntry(
                        agent_id=self.agent_id,
                        memory_type=MemoryType.LEARNING,
                        content=reflection["learning"],
                    ),
                    importance=0.7,
                )

            if reflection.get("skill_to_improve"):
                await self.long_memory.update_growth(
                    reflection["skill_to_improve"],
                    reflection.get("current_assessment", 0.5),
                    f"Self-identified improvement area",
                )

            if reflection.get("a2a_growth_request"):
                req = reflection["a2a_growth_request"]
                await self.send_a2a(
                    req["target_role"],
                    f"建議你在以下領域成長: {req['area']}",
                    msg_type="growth_request",
                )
        except (json.JSONDecodeError, Exception) as e:
            logger.debug("reflection_parse_error", agent=self.NAME, error=str(e))

    async def _handle_growth_request(self, payload: dict):
        """Handle a growth request from another agent."""
        from_agent = payload.get("from_name", payload["from"])
        content = payload["content"]

        # Store feedback
        await self.long_memory.store(
            MemoryEntry(
                agent_id=self.agent_id,
                memory_type=MemoryType.FEEDBACK,
                content=f"Growth request from {from_agent}: {content}",
                metadata={"from": from_agent},
            ),
            importance=0.8,
        )

        # Acknowledge
        await self.send_a2a(
            payload["from"],
            f"收到你的成長建議，我會加強這方面的能力。謝謝 {from_agent}！",
            msg_type="response",
        )

        logger.info("growth_request_received", agent=self.NAME, from_agent=from_agent)

    async def _handle_consensus(self, payload: dict):
        """Handle consensus discussion - override in subclass if needed."""
        pass

    # ---- Task Management ----

    async def receive_task(self, task: dict) -> str:
        """Receive and process a task assignment."""
        task_description = json.dumps(task, ensure_ascii=False, indent=2)

        # Store task in long-term memory
        await self.long_memory.store(
            MemoryEntry(
                agent_id=self.agent_id,
                memory_type=MemoryType.TASK,
                content=task_description,
                metadata=task,
            ),
            importance=0.9,
        )

        return await self.chat(f"你收到了一個新任務:\n{task_description}\n請分析並規劃如何完成這個任務。")
