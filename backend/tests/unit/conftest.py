"""Unit-test fixtures: reconfigure structlog to avoid PrintLogger/stdlib mismatch."""
import structlog
import pytest


@pytest.fixture(autouse=True, scope="session")
def configure_structlog_for_tests():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
