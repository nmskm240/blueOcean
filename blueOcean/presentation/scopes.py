from abc import ABCMeta

from injector import Injector

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.application.di import AppModule, BacktestDialogModule, FetchModule
from blueOcean.presentation.notifiers import (
    AccountCredentialDialogNotifier,
    AccountPageNotifier,
    BacktestDialogNotifier,
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
