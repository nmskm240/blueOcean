import ccxt
from backtrader import Order, Position
from injector import inject
from oandapyV20 import API
import oandapyV20.endpoints.accounts as oanda_accounts
import oandapyV20.endpoints.orders as oanda_orders
import oandapyV20.endpoints.positions as oanda_positions

from blueOcean.application.store import IStore


class CcxtSpotStore(IStore):
    @inject
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

class OandaStore(IStore):
    @inject
    def __init__(
        self,
        access_token: str,
        account_id: str,
        symbol: str,
        environment: str = "practice",
    ):
        super().__init__(symbol)
        self._api = API(access_token=access_token, environment=environment)
        self._account_id = account_id
        self._instrument = self._normalize_instrument(symbol)

        self._cash = 0.0
        self._value = 0.0
        self._margin_available = 0.0
        self._margin_used = 0.0
        self._positions: list[Position] = []

    def create_order(self, order):
        if order.size == 0:
            return

        units = int(order.size)
        if units == 0:
            return

        order_type = "MARKET" if order.exectype == Order.Market else "LIMIT"
        payload: dict[str, dict[str, str]] = {
            "order": {
                "type": order_type,
                "instrument": self._instrument,
                "units": str(units),
            }
        }

        if order_type == "MARKET":
            payload["order"]["timeInForce"] = "FOK"
        else:
            limit_price = order.plimit if order.plimit is not None else order.price
            if limit_price is None:
                return
            payload["order"]["price"] = str(limit_price)
            payload["order"]["timeInForce"] = "GTC"

        request = oanda_orders.OrderCreate(self._account_id, data=payload)
        response = self._api.request(request)
        transaction = response.get("orderCreateTransaction") or response.get(
            "orderFillTransaction"
        )
        if transaction:
            order_id = transaction.get("orderID") or transaction.get("id")
            if order_id:
                order.addinfo(oanda_order_id=order_id)
        return order

    def cancel_order(self, order):
        order_id = order.info.get("oanda_order_id")
        if not order_id:
            return
        request = oanda_orders.OrderCancel(self._account_id, order_id)
        self._api.request(request)

    def update_account_state(self):
        summary = self._api.request(
            oanda_accounts.AccountSummary(self._account_id)
        )
        account = summary.get("account", {})
        balance = float(account.get("balance", 0.0))
        nav = float(account.get("NAV", balance))
        margin_available = float(account.get("marginAvailable", 0.0))
        margin_used = float(account.get("marginUsed", 0.0))

        self._cash = balance
        self._value = nav
        self._margin_available = margin_available
        self._margin_used = margin_used

        positions_response = self._api.request(
            oanda_positions.OpenPositions(self._account_id)
        )
        positions: list[Position] = []
        for item in positions_response.get("positions", []):
            long_units = float(item.get("long", {}).get("units", 0))
            short_units = float(item.get("short", {}).get("units", 0))
            net_units = long_units - short_units
            if net_units == 0:
                continue
            positions.append(Position(size=net_units))
        self._positions = positions

    def get_cash(self):
        return self._cash

    def get_value(self):
        return self._value

    def get_positions(self) -> list[Position]:
        return self._positions

    @staticmethod
    def _normalize_instrument(symbol: str) -> str:
        normalized = symbol.replace("/", "").upper()
        if "_" in normalized:
            return normalized
        if len(normalized) == 6:
            return f"{normalized[:3]}_{normalized[3:]}"
        return normalized
