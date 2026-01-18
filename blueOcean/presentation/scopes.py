from abc import ABCMeta

from injector import Injector

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.application.di import (
    AppModule,
    BacktestDialogModule,
    FetchModule,
    SessionDetailModule,
)
from blueOcean.presentation.notifiers import (
    BacktestDialogNotifier,
    OhlcvFetchDialogNotifier,
    SessionDetailPageNotifier,
    SessionTopPageNotifier,
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


class SessionTopPageScope(Scope):
    def __init__(self, parent: Scope):
        super().__init__(Injector([], parent=parent._injector))

    @property
    def notifier(self) -> SessionTopPageNotifier:
        return self._injector.get(SessionTopPageNotifier)


class SessionDetailPageScope(Scope):
    def __init__(self, parent: Scope, session_id: str):
        super().__init__(
            Injector(
                [
                    SessionDetailModule(session_id),
                ],
                parent=parent._injector,
            )
        )

        self._session_id = session_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def notifier(self) -> SessionDetailPageNotifier:
        return self._injector.get(SessionDetailPageNotifier)


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
