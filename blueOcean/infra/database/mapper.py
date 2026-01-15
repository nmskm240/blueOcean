import json
from datetime import datetime
from typing import overload

from blueOcean.domain.bot import (
    BacktestContext,
    Bot,
    BotId,
    BotRunMode,
    BotStatus,
)
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.infra.database.entities import BotContextEntity, BotEntity
from blueOcean.shared.registries import StrategyRegistry


@overload
def to_domain(bot_entity: BotEntity, context_entity: BotContextEntity) -> Bot: ...


def to_domain(*args):
    if (
        len(args) == 2
        and isinstance(args[0], BotEntity)
        and isinstance(args[1], BotContextEntity)
    ):
        return _bot_entity_to_domain(args[0], args[1])
    raise TypeError("to_domain received unsupported arguments")


@overload
def to_entity(bot: Bot) -> tuple[BotEntity, BotContextEntity]: ...


def to_entity(*args):
    if len(args) == 1 and isinstance(args[0], Bot):
        return _bot_to_entity(args[0])
    raise TypeError("to_entity received unsupported arguments")


# region bots


def _bot_entity_to_domain(
    bot_entity: BotEntity, context_entity: BotContextEntity
) -> Bot:
    mode = BotRunMode(context_entity.mode)
    match mode:
        case BotRunMode.BACKTEST:
            context = BacktestContext(
                strategy_cls=StrategyRegistry.resolve(context_entity.strategy_name),
                strategy_args=json.loads(context_entity.strategy_args),
                source=context_entity.source,
                symbol=context_entity.symbol,
                timeframe=Timeframe.from_compression(context_entity.timeframe),
                start_at=context_entity.started_at,
                end_at=context_entity.finished_at,
            )
        case _:
            raise ValueError()
    return Bot(
        id=BotId(bot_entity.id),
        status=BotStatus(bot_entity.status),
        context=context,
        worker=None,
        pid=bot_entity.pid,
        label=bot_entity.label,
        started_at=bot_entity.started_at,
        finished_at=bot_entity.finished_at,
    )


def _bot_to_entity(bot: Bot) -> tuple[BotEntity, BotContextEntity]:
    context = bot.context

    bot_entity = BotEntity(
        id=bot.id.value,
        status=bot.status.value,
        pid=bot.pid,
        label=bot.label,
        started_at = bot.started_at,
        finished_at = bot.finished_at,
        updated_at=datetime.now(),
    )

    context_entity = BotContextEntity(
        bot_id=bot.id.value,
        mode=context.mode.value,
        strategy_name=StrategyRegistry.name_of(context.strategy_cls),
        strategy_args=json.dumps(context.strategy_args),
        source=context.source,
        symbol=context.symbol,
        timeframe=context.timeframe.value,
    )

    if isinstance(context, BacktestContext):
        context_entity.started_at = context.start_at
        context_entity.finished_at = context.end_at

    return (bot_entity, context_entity)
