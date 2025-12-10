import inspect
from pathlib import Path
from typing import Callable

from blueOcean.application.decorators.registry import (
    StrategyClass,
    StrategyPageData,
    strategy_registry,
)


def strategy_page(
    note_paths: list[tuple[str, str]],
) -> Callable[[StrategyClass], StrategyClass]:
    def decorator(cls: StrategyClass) -> StrategyClass:
        notes = []
        for title, path in note_paths:
            p = Path(path)
            content = p.read_text("utf-8") if p.exists() else None
            notes.append((title, content))

        source = inspect.getsource(cls)
        params = [(k, getattr(cls.params, k)) for k in cls.params._getkeys()]

        strategy_registry.append(
            StrategyPageData(cls=cls, notes=notes, source=source, params=params)
        )
        return cls

    return decorator


# def backtestable():
#     def decorator(cls: StrategyClass):
#         params = []
#         for key in cls.params._getkeys():
#             default_val = getattr(cls.params, key)
#             params.append(
#                 StrategyParam(
#                     name=key,
#                     default=default_val,
#                     type=type(default_val),
#                 )
#             )
#         strategy_parameter_map[cls] = params
#         return cls

#     return decorator

__all__ = [
    strategy_registry,
    strategy_page,
]
