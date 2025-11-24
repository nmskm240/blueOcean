from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, TypeVar

import streamlit as st

StrategyClass = TypeVar("StrategyClass", bound=type)


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


strategy_pages: List[StrategyPage] = []


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


import blueOcean.strategies
