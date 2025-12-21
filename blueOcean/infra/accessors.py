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

    def list_exchange_symbols(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        if not self._data_dir.exists():
            return result

        for exchange_dir in sorted(p for p in self._data_dir.iterdir() if p.is_dir()):
            symbols = sorted(p.name for p in exchange_dir.iterdir() if p.is_dir())
            if symbols:
                result[exchange_dir.name] = symbols
        return result
