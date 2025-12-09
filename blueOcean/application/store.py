from abc import ABCMeta, abstractmethod

from backtrader import Order, Position


class IStore(metaclass=ABCMeta):
    def __init__(self, symbol: str):
        self.symbol = symbol

    @abstractmethod
    def get_cash(self) -> float:
        raise NotImplementedError()

    @abstractmethod
    def get_value(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def create_order(self, order: Order) -> Order:
        raise NotImplementedError()

    @abstractmethod
    def cancel_order(self, order: Order):
        raise NotImplementedError()

    @abstractmethod
    def update_account_state(self):
        raise NotImplementedError()


class IStoreFactory:
    @abstractmethod
    def create(self, source: str) -> IStore:
        raise NotImplementedError()
