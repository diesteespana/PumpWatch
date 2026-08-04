"""
APScheduler configuration for PumpWatch background jobs.

- AsyncIOScheduler: shares FastAPI's event loop, no thread overhead
- max_instances=1 per job: no overlapping detection cycles
- misfire_grace_time=30: allows a slow cycle to finish before skipping
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            job_defaults={
                "misfire_grace_time": 30,
                "coalesce": True,
                "max_instances": 1,
            }
        )
    return _scheduler


async def start_scheduler() -> None:
    settings = get_settings()
    scheduler = get_scheduler()

    from app.blockchain.address_registry import AddressRegistry
    from app.blockchain.block_tracker import BlockTracker
    from app.blockchain.chain_service import EthereumChainService
    from app.blockchain.factory import create_blockchain_provider
    from app.blockchain.price_oracle import CoinGeckoPriceOracle
    from app.database.redis import get_redis_client
    from app.database.session import AsyncSessionLocal
    from app.events.engine import DefaultDetectionEngine
    from app.events.threshold import ThresholdConfig
    from app.notifications.channels.discord import DiscordChannel
    from app.notifications.channels.email import EmailChannel
    from app.notifications.channels.telegram import TelegramChannel
    from app.notifications.rate_limiter import NotificationRateLimiter
    from app.notifications.service import DefaultNotificationService
    from app.repositories.event import EventRepository
    from app.repositories.wallet import WalletRepository
    from app.services.detection_service import DetectionService

    redis_client = get_redis_client()

    # Shared, long-lived objects (safe to reuse across cycles)
    provider = create_blockchain_provider()
    price_oracle = CoinGeckoPriceOracle(
        redis_client=redis_client,
        api_key=settings.coingecko_api_key,
    )
    block_tracker = BlockTracker(redis_client=redis_client, chain="ethereum")
    address_registry = AddressRegistry()
    threshold_config = ThresholdConfig.from_settings()
    rate_limiter = NotificationRateLimiter(redis_client=redis_client)

    chain_service = EthereumChainService(
        provider=provider,
        price_oracle=price_oracle,
        block_tracker=block_tracker,
        address_registry=address_registry,
    )

    async def poll_ethereum() -> None:
        async with AsyncSessionLocal() as session:
            wallet_repo = WalletRepository(session)
            event_repo = EventRepository(session)

            watched_addresses = await wallet_repo.get_all_tracked_addresses("ethereum")

            engine = DefaultDetectionEngine(
                event_repo=event_repo,
                config=threshold_config,
            )

            notifier = DefaultNotificationService(
                session=session,
                rate_limiter=rate_limiter,
            )
            notifier.register_channel(TelegramChannel())
            notifier.register_channel(DiscordChannel())
            notifier.register_channel(EmailChannel())

            service = DetectionService(
                chain_service=chain_service,
                detection_engine=engine,
                notification_service=notifier,
            )

            events = await service.run_cycle(watched_addresses)
            if events:
                logger.info("scheduler_cycle_events", count=len(events))

    scheduler.add_job(
        poll_ethereum,
        trigger=IntervalTrigger(seconds=settings.blockchain_poll_interval_seconds),
        id="ethereum_poll",
        name="Ethereum detection + notification cycle",
        replace_existing=True,
    )

    async def score_wallets() -> None:
        from app.services.analytics_service import WalletAnalyticsService
        async with AsyncSessionLocal() as session:
            svc = WalletAnalyticsService(session)
            scored = await svc.score_all_tracked_wallets()
            if scored:
                logger.info("wallet_scoring_complete", count=scored)

    scheduler.add_job(
        score_wallets,
        trigger=IntervalTrigger(hours=1),
        id="wallet_scoring",
        name="Hourly wallet heuristic scoring",
        replace_existing=True,
    )

    async def run_strategies() -> None:
        from app.services.risk_management_service import RiskManagementService
        from app.services.strategy_engine_service import StrategyEngineService
        from app.repositories.paper_trading import PaperPortfolioRepository
        async with AsyncSessionLocal() as session:
            engine = StrategyEngineService(session)
            trades = await engine.run_all_active()

            # After strategy trades, run risk checks on all portfolios
            from sqlalchemy import select
            from app.models.paper_trading import PaperPortfolio
            result = await session.execute(
                select(PaperPortfolio.id).where(PaperPortfolio.is_active.is_(True))
            )
            portfolio_ids = result.scalars().all()
            for portfolio_id in portfolio_ids:
                risk_svc = RiskManagementService(session)
                await risk_svc.run_checks_for_portfolio(portfolio_id)

            await session.commit()
            if trades:
                logger.info("strategy_engine_cycle", trades_fired=trades)

    scheduler.add_job(
        run_strategies,
        trigger=IntervalTrigger(minutes=5),
        id="strategy_engine",
        name="Strategy evaluation + risk management (5-min cycle)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "scheduler_started",
        interval_seconds=settings.blockchain_poll_interval_seconds,
        provider=settings.active_blockchain_provider,
    )


async def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
