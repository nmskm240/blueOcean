"""Loaded strategy registry used by models, routes and the runner."""

from blueOcean.strategy.definitions import (
    STRATEGY_DEFINITIONS,
    StrategyDefinition,
    get_strategy_definition,
)

# Importing built-ins performs decorator-based registration without making the
# definition primitives depend on concrete Backtrader implementations.
from blueOcean.strategy import implementations as _implementations  # noqa: F401,E402

__all__ = [
    "STRATEGY_DEFINITIONS",
    "StrategyDefinition",
    "get_strategy_definition",
]
