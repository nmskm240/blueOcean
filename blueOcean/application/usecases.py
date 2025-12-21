from __future__ import annotations

from injector import Injector

from blueOcean.application.di import (
    AppDatabaseModule,
    BotRuntimeModule,
    FetcherModule,
)
from blueOcean.application.dto import IBotConfig
from blueOcean.application.services import BotExecutionService
from blueOcean.domain.account import Account, AccountId, ApiCredential
from blueOcean.domain.bot import BotId, BotRunMode
from blueOcean.domain.ohlcv import IOhlcvRepository, OhlcvFetcher
from blueOcean.infra.database.repositories import AccountRepository, BotRepository


def fetch_ohlcv(source: str, symbol: str):
    container = Injector([FetcherModule])
    repository = container.get(IOhlcvRepository)
    fetcher = container.get(OhlcvFetcher)

    latest_at = repository.get_latest_timestamp(source, symbol)

    for batch in fetcher.fetch_ohlcv(symbol, latest_at):
        repository.save(batch, source, symbol)


def run_bot(config: IBotConfig):
    context = config.to_context()
    container = Injector([BotRuntimeModule()])
    service = container.get(BotExecutionService)
    service.start(context)


def export_report(bot_id: BotId) -> None:
    # TODO: 本番稼働の異常終了用のレポート作成処理
    raise NotImplementedError()


def register_api_credential(
    exchange: str,
    api_key: str,
    api_secret: str,
    is_sandbox: bool,
    label: str,
) -> str:
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)

    account = Account(
        id=AccountId.empty(),
        credential=ApiCredential(
            exchange=exchange,
            key=api_key,
            secret=api_secret,
            is_sandbox=is_sandbox,
        ),
        label=label,
    )

    saved = repository.save(account)
    return saved.id.value or ""


def list_api_credentials():
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)
    return repository.get_all()


def update_api_credential(
    account_id: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    is_sandbox: bool,
    label: str,
) -> None:
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)

    account = Account(
        id=AccountId(account_id),
        credential=ApiCredential(
            exchange=exchange,
            key=api_key,
            secret=api_secret,
            is_sandbox=is_sandbox,
        ),
        label=label,
    )

    repository.save(account)


def delete_api_credential(account_id: str) -> None:
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)
    repository.delete_by_id(AccountId(account_id))


def list_bots():
    container = Injector([AppDatabaseModule()])
    repository = container.get(BotRepository)
    bots = repository.get_all()
    records = []
    for bot in bots:
        if bot.mode is not BotRunMode.LIVE:
            continue
        records.append(
            {
                "id": bot.id.value,
                "label": bot.label or bot.context.strategy_cls,
                "status": int(bot.status),
                "strategy_name": bot.context.strategy_cls,
                "account_id": (
                    bot.context.account_id.value
                    if bot.context.account_id is not None
                    else ""
                ),
                "created_at": bot.started_at,
                "updated_at": bot.finished_at or bot.started_at,
            }
        )
    return records
