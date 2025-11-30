from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar
import inspect

import streamlit as st
from backtrader import Strategy

StrategyClass = TypeVar("StrategyClass", bound=Strategy)


@dataclass
class StrategyPage:
    cls: StrategyClass
    notes: list[tuple[str, str]]

    def render(self) -> None:
        st.title(self.cls.__name__)
        overview, notes = st.tabs(["Overview", "Notes"])
        with overview:
            source = inspect.getsource(self.cls)
            st.code(source)
        with notes:
            note_titles = [title for title, _ in self.notes]
            left, right = st.columns([1, 4])

            with left:
                selected = st.radio("Pages", note_titles)

            with right:
                for title, content in self.notes:
                    if title == selected:
                        st.subheader(title)
                        if content:
                            st.markdown(content, unsafe_allow_html=True)
                        else:
                            st.warning("No contents")


@dataclass
class StrategyParam:
    name: str
    default: any
    type: type


strategy_pages: list[StrategyPage] = []
strategy_parameter_map: dict[StrategyClass, list[StrategyParam]] = {}


def strategy_page(
    note_paths: list[tuple[str, str]],
) -> Callable[[StrategyClass], StrategyClass]:
    def decorator(cls: StrategyClass) -> StrategyClass:
        notes = []
        for title, path in note_paths:
            p = Path(path)
            content = p.read_text(encoding="utf-8") if p.exists() else None
            notes.append((title, content))

        strategy_pages.append(StrategyPage(cls=cls, notes=notes))
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
