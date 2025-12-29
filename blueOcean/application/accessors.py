from __future__ import annotations

from abc import ABCMeta, abstractmethod
from pathlib import Path

import pandas as pd


class IBotRuntimeDirectoryAccessor(metaclass=ABCMeta):
    @property
    @abstractmethod
    def metrics(self) -> pd.DataFrame:
        raise NotImplementedError()

    @abstractmethod
    def get_or_create_directory(self) -> Path:
        raise NotImplementedError()


class IExchangeSymbolAccessor(metaclass=ABCMeta):
    @property
    @abstractmethod
    def exchanges(self) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def symbols_for(self, echange_name: str) -> list[str]:
        raise NotImplementedError()
