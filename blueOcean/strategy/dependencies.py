from blueOcean.container import get_injector
from blueOcean.strategy.services import StrategyService


def get_strategy_service() -> StrategyService:
    return get_injector().get(StrategyService)
