from dataclasses import asdict, dataclass, field

from injector import inject

from blueOcean.strategy.models import StrategyConfig, StrategyRun
from blueOcean.strategy.registry import STRATEGY_DEFINITIONS, StrategyDefinition
from blueOcean.strategy.repositories import StrategyRepository, StrategyRunRepository
from blueOcean.strategy.supervisor import StrategySupervisor


@dataclass(frozen=True)
class CreateStrategyConfig:
    name: str
    definition_key: str
    account_id: str
    symbol: str
    timeframe: str
    mode: str = "paper"
    parameters: dict = field(default_factory=dict)


class StrategyService:
    """Application boundary shared by HTTP API and server-rendered pages."""

    @inject
    def __init__(
        self,
        strategies: StrategyRepository,
        runs: StrategyRunRepository,
        supervisor: StrategySupervisor,
    ) -> None:
        self._strategies = strategies
        self._runs = runs
        self._supervisor = supervisor

    def definitions(self) -> list[StrategyDefinition]:
        return list(STRATEGY_DEFINITIONS.values())

    def list_strategies(self) -> list[StrategyConfig]:
        return self._strategies.list()

    def get_strategy(self, strategy_id: str) -> StrategyConfig:
        return self._strategies.get(strategy_id)

    def create_strategy(self, command: CreateStrategyConfig) -> StrategyConfig:
        return self._strategies.save(StrategyConfig(**asdict(command)))

    def list_runs(self) -> list[StrategyRun]:
        return self._runs.list()

    def get_run(self, run_id: str) -> StrategyRun:
        return self._runs.get(run_id)

    def start_run(self, strategy_id: str) -> StrategyRun:
        return self._supervisor.start(strategy_id)

    def stop_run(self, run_id: str) -> StrategyRun:
        return self._supervisor.stop(run_id)
