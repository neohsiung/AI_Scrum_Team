"""
Memory system for agents - short-term (ephemeral) and long-term (persistent) layers.

Short-term memory: In-memory conversation buffer (recent context window)
Long-term memory: SQLite-backed persistent storage (learnings, skills, decisions)
"""

import json
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

import aiosqlite


class MemoryType(str, Enum):
    LEARNING = "learning"         # Things the agent has learned
    SKILL = "skill"               # Skills the agent has developed
    DECISION = "decision"         # Decisions made
    FEEDBACK = "feedback"         # Feedback from owner or peers
    GROWTH = "growth"             # Self-growth records
    TASK = "task"                 # Task history
    INTERACTION = "interaction"   # A2A interaction records


@dataclass
class MemoryEntry:
    agent_id: str
    memory_type: MemoryType
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ShortTermMemory:
    """In-memory conversation buffer with sliding window."""

    def __init__(self, max_messages: int = 50):
        self._buffer: deque[dict] = deque(maxlen=max_messages)

    def add(self, role: str, content: str, metadata: dict | None = None):
        self._buffer.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })

    def get_recent(self, n: int = 20) -> list[dict]:
        return list(self._buffer)[-n:]

    def get_context_for_claude(self) -> list[dict]:
        """Format short-term memory as Claude API messages."""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._buffer
            if m["role"] in ("user", "assistant")
        ]

    def clear(self):
        self._buffer.clear()


class LongTermMemory:
    """SQLite-backed persistent memory per agent."""

    def __init__(self, db_path: str, agent_id: str):
        self.db_path = db_path
        self.agent_id = agent_id

    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    timestamp REAL NOT NULL,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_agent
                ON memories(agent_id, memory_type)
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS growth_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    skill_area TEXT NOT NULL,
                    level REAL DEFAULT 0.0,
                    description TEXT,
                    updated_at REAL NOT NULL
                )
            """)
            await db.commit()

    async def store(self, entry: MemoryEntry, importance: float = 0.5):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO memories (agent_id, memory_type, content, metadata, timestamp, importance)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry.agent_id,
                    entry.memory_type.value,
                    entry.content,
                    json.dumps(entry.metadata, ensure_ascii=False),
                    entry.timestamp,
                    importance,
                ),
            )
            await db.commit()

    async def recall(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 10,
        keyword: str | None = None,
    ) -> list[dict]:
        """Retrieve memories, optionally filtered by type and keyword."""
        query = "SELECT * FROM memories WHERE agent_id = ?"
        params: list = [self.agent_id]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type.value)

        if keyword:
            query += " AND content LIKE ?"
            params.append(f"%{keyword}%")

        query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_growth_summary(self) -> list[dict]:
        """Get agent's skill growth summary."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM growth_log WHERE agent_id = ? ORDER BY level DESC",
                (self.agent_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_growth(self, skill_area: str, level: float, description: str):
        """Update or insert a growth record for a skill area."""
        async with aiosqlite.connect(self.db_path) as db:
            existing = await db.execute(
                "SELECT id FROM growth_log WHERE agent_id = ? AND skill_area = ?",
                (self.agent_id, skill_area),
            )
            row = await existing.fetchone()
            if row:
                await db.execute(
                    "UPDATE growth_log SET level = ?, description = ?, updated_at = ? WHERE id = ?",
                    (level, description, time.time(), row[0]),
                )
            else:
                await db.execute(
                    "INSERT INTO growth_log (agent_id, skill_area, level, description, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (self.agent_id, skill_area, level, description, time.time()),
                )
            await db.commit()
