from typing import Type, TypeVar
import backtrader as bt

TStrategy = TypeVar("TStrategy", bound=bt.Strategy)


class StrategyRunner:
    def __init__(self):
        self._analyzers: list[tuple[type, str, dict]] = []

    def add_analyzer(self, analyzer_cls: type, name: str | None = None, **kwargs):
        self._analyzers.append((analyzer_cls, name, kwargs))
        return self

    def run(
        self, strategy: Type[TStrategy], datafeed: bt.feed.DataBase, **strategy_args
    ) -> tuple[TStrategy, bt.Cerebro]:
        cerebro = bt.Cerebro()
        cerebro.adddata(datafeed)
        cerebro.broker.setcash(10_000)
        cerebro.broker.setcommission(leverage=3)
        cerebro.addsizer(bt.sizers.FixedSize, stake=0.1)
        cerebro.addstrategy(strategy, **strategy_args)

        for analyzer_cls, name, kwargs in self._analyzers:
            if name:
                cerebro.addanalyzer(analyzer_cls, _name=name, **kwargs)
            else:
                cerebro.addanalyzer(analyzer_cls, **kwargs)

        result = cerebro.run()[0]
        returns = result.analyzers.timereturn.get_analysis()

        return result, cerebro
