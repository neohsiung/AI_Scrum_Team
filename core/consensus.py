"""
Consensus mechanism for the Scrum Team.

When the team cannot agree on a decision after MAX_CONSENSUS_ROUNDS rounds,
the issue is escalated to the human owner via Telegram.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field

import structlog

from config.settings import settings

logger = structlog.get_logger()


@dataclass
class ConsensusSession:
    topic: str
    initiator: str
    participants: list[str]
    round_number: int = 0
    opinions: dict[str, list[str]] = field(default_factory=dict)
    resolved: bool = False
    resolution: str = ""
    created_at: float = field(default_factory=time.time)


class ConsensusManager:
    """Manages consensus-building discussions between agents."""

    def __init__(self):
        self.sessions: dict[str, ConsensusSession] = {}
        self._escalation_callback = None

    def set_escalation_callback(self, callback):
        """Set the callback function for escalating to human owner."""
        self._escalation_callback = callback

    async def start_consensus(
        self,
        topic: str,
        initiator: str,
        participants: list[str],
        agents_registry: dict,
    ) -> str:
        """Start a new consensus discussion."""
        session_id = f"consensus_{int(time.time())}_{initiator}"
        session = ConsensusSession(
            topic=topic,
            initiator=initiator,
            participants=participants,
        )
        self.sessions[session_id] = session

        logger.info(
            "consensus_started",
            session_id=session_id,
            topic=topic,
            participants=participants,
        )

        # Run consensus rounds
        result = await self._run_consensus_rounds(session_id, agents_registry)
        return result

    async def _run_consensus_rounds(
        self, session_id: str, agents_registry: dict
    ) -> str:
        session = self.sessions[session_id]

        for round_num in range(1, settings.max_consensus_rounds + 1):
            session.round_number = round_num
            logger.info("consensus_round", session_id=session_id, round=round_num)

            # Collect opinions from all participants
            round_opinions = {}
            for role in session.participants:
                agent = agents_registry.get(role)
                if not agent:
                    continue

                # Build context with previous opinions
                context = f"## 共識討論 - 第 {round_num} 輪\n\n"
                context += f"**議題**: {session.topic}\n\n"

                if session.opinions:
                    context += "**前幾輪的意見**:\n"
                    for r, opinions in session.opinions.items():
                        for i, op in enumerate(opinions):
                            context += f"- {r} (第{i+1}輪): {op}\n"
                    context += "\n"

                context += "請表達你的立場和理由。如果你同意某個已提出的方案，請明確表示。"
                context += "\n最後請用 [同意/不同意] 標記你的態度。"

                opinion = await agent.chat(context)
                round_opinions[role] = opinion

                # Store in session
                if role not in session.opinions:
                    session.opinions[role] = []
                session.opinions[role].append(opinion)

            # Check if consensus is reached
            if await self._check_consensus(round_opinions, agents_registry):
                session.resolved = True
                session.resolution = self._summarize_consensus(round_opinions)
                logger.info("consensus_reached", session_id=session_id, round=round_num)
                return f"✅ 共識達成 (第 {round_num} 輪):\n\n{session.resolution}"

        # Failed to reach consensus - escalate
        return await self._escalate(session_id)

    async def _check_consensus(
        self, opinions: dict[str, str], agents_registry: dict
    ) -> bool:
        """Use Claude to analyze if consensus is reached."""
        # Simple heuristic: check if majority agrees
        agree_count = sum(
            1 for op in opinions.values()
            if "[同意]" in op or "同意" in op.lower()
        )
        total = len(opinions)
        return agree_count >= (total * 2 / 3)  # 2/3 majority

    def _summarize_consensus(self, opinions: dict[str, str]) -> str:
        summary = "各方意見摘要:\n"
        for role, opinion in opinions.items():
            # Take first 200 chars of each opinion
            summary += f"- **{role}**: {opinion[:200]}...\n"
        return summary

    async def _escalate(self, session_id: str) -> str:
        """Escalate to human owner when consensus fails."""
        session = self.sessions[session_id]

        escalation_msg = f"""⚠️ **共識無法達成 - 需要您的決策**

**議題**: {session.topic}
**發起者**: {session.initiator}
**參與者**: {', '.join(session.participants)}
**討論輪數**: {session.round_number}

**各方最終意見**:
"""
        for role, opinions in session.opinions.items():
            if opinions:
                escalation_msg += f"\n**{role}** (最新意見):\n{opinions[-1][:300]}\n"

        escalation_msg += "\n請做出最終決定並回覆。"

        logger.warning("consensus_escalated", session_id=session_id)

        if self._escalation_callback:
            await self._escalation_callback(escalation_msg)

        return f"🔺 已升級至人類決策者。\n\n{escalation_msg}"


# Singleton
consensus_manager = ConsensusManager()
