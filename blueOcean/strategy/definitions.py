from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    label: str
    value_type: type
    default: Any
    minimum: float | None = None

    def parse(self, value: Any) -> Any:
        try:
            parsed = self.value_type(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{self.label}の形式が正しくありません") from exc
        if self.minimum is not None and parsed < self.minimum:
            raise ValueError(f"{self.label}は{self.minimum}以上で指定してください")
        return parsed


@dataclass(frozen=True)
class StrategyDefinition:
    key: str
    label: str
    strategy_class: type
    parameters: tuple[ParameterDefinition, ...]

    def validate(self, values: dict) -> dict:
        allowed = {parameter.name for parameter in self.parameters}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"未定義のパラメータです: {', '.join(sorted(unknown))}")
        return {
            parameter.name: parameter.parse(values.get(parameter.name, parameter.default))
            for parameter in self.parameters
        }


STRATEGY_DEFINITIONS: dict[str, StrategyDefinition] = {}


def register_strategy(
    *, key: str, label: str, parameters: tuple[ParameterDefinition, ...]
):
    """Register a Backtrader strategy class for UI, validation and execution."""
    def decorator(strategy_class: type) -> type:
        if key in STRATEGY_DEFINITIONS:
            raise RuntimeError(f"Strategy key is already registered: {key}")
        STRATEGY_DEFINITIONS[key] = StrategyDefinition(
            key=key,
            label=label,
            strategy_class=strategy_class,
            parameters=parameters,
        )
        return strategy_class

    return decorator


def get_strategy_definition(key: str) -> StrategyDefinition:
    try:
        return STRATEGY_DEFINITIONS[key]
    except KeyError as exc:
        raise ValueError("未対応の戦略です") from exc
