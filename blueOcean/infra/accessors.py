from __future__ import annotations

from pathlib import Path

from injector import inject
import pandas as pd

from blueOcean.application.accessors import (
    IContextRuntimeDirectoryAccessor,
    IExchangeSymbolAccessor,
)
from blueOcean.domain.context import ContextId


class LocalContextRuntimeDirectoryAccessor(IContextRuntimeDirectoryAccessor):
    @inject
    def __init__(self, id: ContextId):
        self._id = id

    @property
    def metrics(self):
        return pd.read_csv(self.get_or_create_directory() / "metrics.csv")

    def get_or_create_directory(self) -> Path:
        # TODO: ベースディレクトリは設定で変更可能にする
        run_dir = Path("./out") / self._id.value
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir


class ExchangeSymbolDirectoryAccessor(IExchangeSymbolAccessor):
    def __init__(self, data_dir: str | Path = "data"):
        self._data_dir = Path(data_dir)

    @property
    def exchanges(self):
        return sorted(p.name for p in self._data_dir.iterdir() if p.is_dir())

    def symbols_for(self, echange_name):
        exchange_dir = self._data_dir / echange_name
        return sorted(p.name for p in exchange_dir.iterdir() if p.is_dir())
