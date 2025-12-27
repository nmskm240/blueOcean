from __future__ import annotations

from pathlib import Path


from blueOcean.application.accessors import (
    IBotRuntimeDirectoryAccessor,
    IExchangeSymbolAccessor,
)
from blueOcean.domain.bot import BotId


class LocalBotRuntimeDirectoryAccessor(IBotRuntimeDirectoryAccessor):
    def generate_directory(self, bot_id: BotId) -> Path:
        # TODO: ベースディレクトリは設定で変更可能にする
        run_dir = Path("./out") / bot_id.value
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
    