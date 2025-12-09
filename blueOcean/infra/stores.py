from multiprocessing.connection import Connection

from backtrader import Position

from blueOcean.application.store import IStore


class CcxtSpotStore(IStore):
    def __init__(
        self, symbol: str, order_pipe: Connection, account_state_pipe: Connection, quote="USDT"
    ):
        super().__init__(symbol)
        self.order_pipe = order_pipe
        self.account_state_pipe = account_state_pipe
        self.quote = quote

        self._cash = 0
        self._value = 0
        self._positions = []

    def get_cash(self):
        return self._cash

    def get_value(self):
        return self._value

    def get_positions(self) -> list[Position]:
        return self._positions

    def create_order(self, order):
        if order.size == 0:
            return

        msg = {
            "symbol": self.symbol,
            "side": "buy" if order.size > 0 else "sell",
            "amount": abs(order.size),
            "order_ref": order.ref,
        }
        self.order_pipe.send(msg)
        ccxt_order = self.order_pipe.recv()
        order.addinfo(ccxt_order_id=ccxt_order.id)
        return order

    def cancel_order(self, order):
        symbol = self.symbol
        ccxt_id = order.info.get("ccxt_order_id")
        self.exchange.cancel_order(ccxt_id, symbol)

    def update_account_state(self):
        self.account_state_pipe.send(None)
        balance = self.account_state_pipe.recv()
        positions: list[Position] = []
        for symbol, info in balance.items():
            if not isinstance(info, dict):
                continue
            total = float(info.get("total", 0))
            if total > 0 and symbol != self.quote:
                position = Position(size=total)
                positions.append(position)
        self._positions = positions
        self._cash = balance["free"][self.quote]
        self._value = balance["total"][self.quote]
