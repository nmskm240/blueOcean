from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple, TypeVar

from backtrader import Strategy
import streamlit as st

StrategyClass = TypeVar("StrategyClass", bound=Strategy)


@dataclass
class StrategyPage:
    title: str | None
    contents: str | None
    strategy_cls: type

    def render(self) -> None:
        if self.contents:
            st.markdown(self.contents, unsafe_allow_html=True)
        else:
            st.warning("No contents")


@dataclass
class StrategyParam:
    name: str
    default: Any
    type: type


strategy_pages: List[StrategyPage] = []
strategy_parameter_map: Dict[StrategyClass, List[StrategyParam]] = {}


def from_strategy(
    title: str, note_path: str = None
) -> Callable[[StrategyClass], StrategyClass]:
    def decorator(cls: StrategyClass) -> StrategyClass:
        try:
            with open(note_path) as f:
                contents = f.read()
                page = StrategyPage(
                    title=title,
                    contents=contents,
                    strategy_cls=cls,
                )
        except:
            page = StrategyPage(
                title=title,
                contents=None,
                strategy_cls=cls,
            )
        strategy_pages.append(page)
        return cls

    return decorator


def backtestable():
    def decorator(cls: StrategyClass):
        params = []
        for key in cls.params._getkeys():
            default_val = getattr(cls.params, key)
            params.append(
                StrategyParam(
                    name=key,
                    default=default_val,
                    type=type(default_val),
                )
            )
        strategy_parameter_map[cls] = params
        return cls

    return decorator


import blueOcean.strategies
