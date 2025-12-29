from abc import ABCMeta

from injector import Injector

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.application.di import (
    AppModule,
    BacktestDialogModule,
    BotDetailModule,
    FetchModule,
)
from blueOcean.domain.bot import BotId
from blueOcean.presentation.notifiers import (
    AccountCredentialDialogNotifier,
    AccountPageNotifier,
    BacktestDialogNotifier,
    BotDetailPageNotifier,
    BotTopPageNotifier,
    OhlcvFetchDialogNotifier,
)


class Scope(metaclass=ABCMeta):
    def __init__(self, injector: Injector):
        self._injector = injector


class AppScope(Scope):
    def __init__(self):
        super().__init__(
            Injector(
                [
                    AppModule(),
                    FetchModule(),
                ]
            )
        )


class AccountPageScope(Scope):
    def __init__(self, parent: Scope):
        super().__init__(Injector([], parent=parent._injector))

    @property
    def notifier(self) -> AccountPageNotifier:
        return self._injector.get(AccountPageNotifier)


class BotTopPageScope(Scope):
    def __init__(self, parent: Scope):
        super().__init__(Injector([], parent=parent._injector))

    @property
    def notifier(self) -> BotTopPageNotifier:
        return self._injector.get(BotTopPageNotifier)


class BotDetailPageScope(Scope):
    def __init__(self, parent: Scope, bot_id: BotId):
        super().__init__(
            Injector(
                [
                    BotDetailModule(bot_id),
                ],
                parent=parent._injector,
            )
        )

        self._bot_id = bot_id

    @property
    def bot_id(self) -> BotId:
        return self._bot_id

    @property
    def notifier(self) -> BotDetailPageNotifier:
        return self._injector.get(BotDetailPageNotifier)


class AccountCredentialDialogScope(Scope):
    def __init__(self, parent: Scope):
        super().__init__(Injector([], parent=parent._injector))

    @property
    def notifier(self) -> AccountCredentialDialogNotifier:
        return self._injector.get(AccountCredentialDialogNotifier)


class OhlcvFetchDialogScope(Scope):
    def __init__(self, parent: Scope):
        super().__init__(Injector([], parent=parent._injector))

    @property
    def notifier(self) -> OhlcvFetchDialogNotifier:
        return self._injector.get(OhlcvFetchDialogNotifier)


class BacktestDialogScope(Scope):
    def __init__(self, parent: Scope):
        super().__init__(
            Injector(
                [
                    BacktestDialogModule(),
                ],
                parent=parent._injector,
            )
        )

    @property
    def notifier(self) -> BacktestDialogNotifier:
        return self._injector.get(BacktestDialogNotifier)

    @property
    def exchange_symbol_accessor(self) -> IExchangeSymbolAccessor:
        return self._injector.get(IExchangeSymbolAccessor)
