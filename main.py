"""
Agent Scrum Team - Main Entry Point

Starts all 8 agents with their Telegram bots and A2A listeners.
"""

import asyncio
import os
import signal
import sys

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


async def main():
    from agents import ALL_AGENTS
    from config.settings import settings
    from telegram.bot import AgentTelegramBot, get_token_for_role

    # Ensure data directory exists
    os.makedirs(os.path.dirname(settings.memory_db_path) or "./data", exist_ok=True)

    # Initialize all agents
    agents_registry: dict = {}
    bots: list[AgentTelegramBot] = []

    logger.info("starting_scrum_team", agents=list(ALL_AGENTS.keys()))

    for role, agent_cls in ALL_AGENTS.items():
        token = get_token_for_role(role)
        if not token:
            logger.warning("skipping_agent_no_token", role=role)
            continue

        agent = agent_cls()
        await agent.initialize()
        agents_registry[role] = agent

        bot = AgentTelegramBot(agent, token)
        bots.append(bot)

        logger.info("agent_ready", role=role, name=agent.NAME)

    if not agents_registry:
        logger.error("no_agents_configured", hint="Set TG_TOKEN_* in .env file")
        sys.exit(1)

    # Set registry references for A2A and consensus
    for bot in bots:
        bot.set_agents_registry(agents_registry)

    # Setup all bots
    for bot in bots:
        await bot.setup()

    # Start all bots and A2A listeners
    tasks = []
    for bot in bots:
        await bot.start()

    for role, agent in agents_registry.items():
        task = asyncio.create_task(agent.start_a2a_listener())
        tasks.append(task)

    logger.info(
        "scrum_team_running",
        active_agents=list(agents_registry.keys()),
        count=len(agents_registry),
    )
    print("\n" + "=" * 50)
    print("🏃 Agent Scrum Team is running!")
    print(f"   Active agents: {len(agents_registry)}")
    for role, agent in agents_registry.items():
        print(f"   • {agent.NAME} ({role})")
    print("=" * 50)
    print("Press Ctrl+C to stop.\n")

    # Graceful shutdown
    stop_event = asyncio.Event()

    def _signal_handler():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()

    # Shutdown
    logger.info("shutting_down")
    for bot in bots:
        await bot.stop()
    for agent in agents_registry.values():
        await agent.shutdown()
    for task in tasks:
        task.cancel()

    logger.info("scrum_team_stopped")


if __name__ == "__main__":
    asyncio.run(main())
