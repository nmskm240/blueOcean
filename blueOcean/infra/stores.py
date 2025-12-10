import ccxt
from backtrader import Position, Order

from blueOcean.application.store import IStore


class CcxtSpotStore(IStore):
    def __init__(self, exchange: ccxt.Exchange, symbol: str, quote="USDT"):
        super().__init__(symbol)
        self.exchange = exchange
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

        type = "market" if order.exectype == Order.Market else "limit"
        side = "buy" if order.size > 0 else "sell"

        ccxt_order = self.exchange.create_order(
            self.symbol, type, side, abs(order.size), order.plimit
        )
        order.addinfo(ccxt_order_id=ccxt_order.id)
        return order

    def cancel_order(self, order):
        symbol = self.symbol
        ccxt_id = order.info.get("ccxt_order_id")
        self.exchange.cancel_order(ccxt_id, symbol)

    def update_account_state(self):
        balance = self.exchange.fetch_balance()
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
