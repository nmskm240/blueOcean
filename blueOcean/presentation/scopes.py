from abc import ABCMeta

from injector import Injector

from blueOcean.application.di import AppModule
from blueOcean.presentation.notifiers import (
    AccountCredentialDialogNotifier,
    AccountPageNotifier,
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
