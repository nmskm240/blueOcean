from __future__ import annotations

from abc import ABCMeta, abstractmethod
from pathlib import Path

import ccxt
import pandas as pd
from injector import inject

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.domain.bot import (
    Bot,
    BotContext,
    BotId,
    BotRunMode,
    IBotRepository,
    IBotWorkerFactory,
)
from blueOcean.domain.ohlcv import IOhlcvRepository, Ohlcv
from blueOcean.infra.database.repositories import AccountRepository


class IExchangeService(metaclass=ABCMeta):
    @abstractmethod
    def fetchable_exchanges(self) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def symbols_for(self, exchange_name: str) -> list[str]:
        raise NotImplementedError()


class BotWorkerFactory(IBotWorkerFactory):
    def create(self, id: BotId, context: BotContext):
        match context.mode:
            case BotRunMode.LIVE:
                from blueOcean.application.workers import LiveTradeWorker

                worker = LiveTradeWorker(id, context)
            case BotRunMode.BACKTEST:
                from blueOcean.application.workers import BacktestWorker

                worker = BacktestWorker(id, context)
            case _:
                raise RuntimeError(f"Unsupported run mode. {context.mode}")
        return worker


class BotExecutionService:
    @inject
    def __init__(
        self,
        bot_repository: IBotRepository,
        bot_worker_factory: IBotWorkerFactory,
    ):
        self._bot_repository = bot_repository
        self._bot_worker_factory = bot_worker_factory

    def start(self, context: BotContext):
        bot = Bot.create(context)
        worker = self._bot_worker_factory.create(bot.id, context)

        bot.attach(worker)
        bot.start()
        saved = self._bot_repository.save(bot)
        return saved.id

    def stop(self, id: BotId):
        from blueOcean.application.workers import RecoverWorker

        bot = self._bot_repository.find_by_id(id)
        worker = RecoverWorker(bot.pid)

        bot.attach(worker)
        bot.stop()
        self._bot_repository.save(bot)


class CcxtExchangeService(IExchangeService):
    @inject
    def __init__(
        self,
        account_repository: AccountRepository,
        ohlcv_repository: IOhlcvRepository,
    ):
        self._account_repository = account_repository
        self._ohlcv_repository = ohlcv_repository

    def fetchable_exchanges(self) -> list[str]:
        supported: list[str] = []
        for account in self._account_repository.get_all():
            credential = account.credential
            if not credential.key or not credential.secret:
                continue
            name = credential.exchange
            if name in supported:
                continue
            exchange_cls = getattr(ccxt, name, None)
            if exchange_cls is None:
                continue
            exchange = exchange_cls(
                {
                    "apiKey": credential.key,
                    "secret": credential.secret,
                }
            )
            exchange.set_sandbox_mode(credential.is_sandbox)
            if exchange.has.get("fetchOHLCV"):
                supported.append(name)
        return supported

    def symbols_for(self, exchange_name: str) -> list[str]:
        exchange_cls = getattr(ccxt, exchange_name, None)
        if exchange_cls is None:
            return []
        exchange = exchange_cls()
        markets = exchange.load_markets()
        return sorted(markets.keys())


class BacktestExchangeService(IExchangeService):
    @inject
    def __init__(self, accessor: IExchangeSymbolAccessor):
        self._accessor = accessor

    def fetchable_exchanges(self) -> list[str]:
        return sorted(self._accessor.exchanges)

    def symbols_for(self, exchange_name: str) -> list[str]:
        return sorted(self._accessor.symbols(exchange_name))


class OhlcvCsvImporter:
    required_columns = {"datetime", "open", "high", "low", "close"}

    def load(self, file_path: str) -> list[Ohlcv]:
        path = Path(file_path)
        df = pd.read_csv(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        missing = self.required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        df = df.rename(columns={"datetime": "time"})
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df["time"] = df["time"].dt.tz_convert("UTC").dt.tz_localize(None)

        if "volume" not in df.columns:
            df["volume"] = 0.0

        for column in ["open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        df = df.dropna(subset=["time", "open", "high", "low", "close", "volume"])
        df = df[["time", "open", "high", "low", "close", "volume"]]
        return Ohlcv.from_dataframe(df)
