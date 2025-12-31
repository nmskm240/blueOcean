from typing import overload

from blueOcean.application.dto import AccountCredentialInfo, BotInfo, PlaygroundRunInfo
from blueOcean.domain.account import Account, AccountId, ApiCredential
from blueOcean.domain.bot import Bot
from blueOcean.domain.playground import PlaygroundRun


@overload
def to_account(info: AccountCredentialInfo) -> Account: ...


def to_account(*args):
    match args:
        case (AccountCredentialInfo() as info,) if len(args) == 1:
            return Account(
                id=AccountId(info.account_id),
                credential=ApiCredential(
                    exchange=info.exchange_name,
                    key=info.api_key,
                    secret=info.api_secret,
                    is_sandbox=info.is_sandbox,
                ),
                label=info.label,
            )
        case _:
            raise TypeError("to_account received unsupported arguments")

def to_bot_info(bot: Bot) -> BotInfo:
    return BotInfo(
        bot_id=bot.id.value,
        label=bot.label or "",
        status=bot.status.name,
        mode=bot.context.mode.name,
        source=bot.context.source,
        symbol=bot.context.symbol,
        timeframe=bot.context.timeframe,
        strategy=(
            bot.context.strategy_cls.__name__ if bot.context.strategy_cls else ""
        ),
        started_at=bot.started_at,
        finished_at=bot.finished_at,
    )


def to_playground_run_info(run: PlaygroundRun) -> PlaygroundRunInfo:
    return PlaygroundRunInfo(
        run_id=run.id.value,
        notebook_path=run.notebook_path,
        parameters=run.parameters,
        markdown=run.markdown,
        status=run.status.name,
        executed_at=run.executed_at,
        output_path=run.output_path,
        error_message=run.error_message,
    )
