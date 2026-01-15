from blueOcean.application.dto import BotInfo
from blueOcean.domain.bot import Bot

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
