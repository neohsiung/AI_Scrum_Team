"""Central configuration for Agent Scrum Team."""

from pydantic_settings import BaseSettings
from pydantic import Field


class AgentConfig(BaseSettings):
    """Per-agent configuration loaded from environment."""

    # Claude API
    claude_api_key: str = Field(default="", alias="CLAUDE_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-20250514", alias="CLAUDE_MODEL")
    claude_max_tokens: int = Field(default=4096, alias="CLAUDE_MAX_TOKENS")

    # Redis for A2A message bus
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # SQLite memory storage path
    memory_db_path: str = Field(default="./data/memory.db", alias="MEMORY_DB_PATH")

    # Telegram Bot Tokens (one per agent)
    telegram_token_scrum_master: str = Field(default="", alias="TG_TOKEN_SCRUM_MASTER")
    telegram_token_product_owner: str = Field(default="", alias="TG_TOKEN_PRODUCT_OWNER")
    telegram_token_tech_lead: str = Field(default="", alias="TG_TOKEN_TECH_LEAD")
    telegram_token_backend: str = Field(default="", alias="TG_TOKEN_BACKEND")
    telegram_token_frontend: str = Field(default="", alias="TG_TOKEN_FRONTEND")
    telegram_token_app: str = Field(default="", alias="TG_TOKEN_APP")
    telegram_token_qa: str = Field(default="", alias="TG_TOKEN_QA")
    telegram_token_devops: str = Field(default="", alias="TG_TOKEN_DEVOPS")

    # Telegram owner chat ID (your personal chat ID for escalation)
    telegram_owner_chat_id: str = Field(default="", alias="TG_OWNER_CHAT_ID")

    # Consensus settings
    max_consensus_rounds: int = Field(default=3, alias="MAX_CONSENSUS_ROUNDS")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = AgentConfig()
