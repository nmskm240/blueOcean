from __future__ import annotations

from collections import deque
from typing import Any

import backtrader as bt


class MT5Broker(bt.BrokerBase):
    """Backtrader broker that sends market/limit/stop orders to MT5."""

    params = (("store", None), ("magic", 0), ("comment", "backtrader"), ("deviation", 20))

    def __init__(self, **kwargs) -> None:
        super().__init__()
        if self.p.store is None:
            raise ValueError("MT5Broker requires store=MT5Store(...)")
        self._store = self.p.store
        self._notifications = deque()
        self._orders: dict[int, bt.Order] = {}

    def start(self) -> None:
        super().start()
        self._store.start()

    def stop(self) -> None:
        self._store.stop()
        super().stop()

    def getcash(self) -> float:
        account = self._store.client.account_info()
        return float(account.balance if account else 0.0)

    def getvalue(self, datas=None) -> float:
        account = self._store.client.account_info()
        return float(account.equity if account else 0.0)

    def getposition(self, data, clone=True):
        symbol = getattr(data, "_symbol", data._name)
        positions = self._store.client.positions_get(symbol=symbol) or []
        size = 0.0
        price_value = 0.0
        buy_type = self._store.client.mt5.POSITION_TYPE_BUY
        for position in positions:
            signed = position.volume if position.type == buy_type else -position.volume
            size += signed
            price_value += signed * position.price_open
        price = price_value / size if size else 0.0
        return bt.Position(size=size, price=price)

    def buy(self, owner, data, size, price=None, plimit=None, exectype=None, **kwargs):
        order = bt.BuyOrder(owner=owner, data=data, size=size, price=price,
                            pricelimit=plimit, exectype=exectype)
        order.addinfo(**kwargs)
        return self.submit(order)

    def sell(self, owner, data, size, price=None, plimit=None, exectype=None, **kwargs):
        order = bt.SellOrder(owner=owner, data=data, size=size, price=price,
                             pricelimit=plimit, exectype=exectype)
        order.addinfo(**kwargs)
        return self.submit(order)

    def submit(self, order, check=True):
        order.submit(self)
        self._notify(order)
        return self._transmit(order)

    def _transmit(self, order):
        mt5 = self._store.client.mt5
        symbol = getattr(order.data, "_symbol", order.data._name)
        info = self._store.client.ensure_symbol(symbol)
        tick = self._store.client.symbol_info_tick(symbol)
        is_buy = order.isbuy()
        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_DEAL if order.exectype == bt.Order.Market else mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": abs(float(order.size)),
            "type": self._order_type(order, mt5),
            "price": (tick.ask if is_buy else tick.bid) if order.exectype == bt.Order.Market else order.created.price,
            "deviation": self.p.deviation,
            "magic": self.p.magic,
            "comment": self.p.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": info.filling_mode,
        }
        result = self._store.client.order_send(request)
        if result is None or result.retcode not in {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}:
            order.reject(self)
        else:
            order.addinfo(mt5_order=result.order, mt5_deal=getattr(result, "deal", 0))
            order.accept(self)
            self._orders[order.ref] = order
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                executed_price = float(getattr(result, "price", 0) or request["price"])
                order.execute(
                    order.data.datetime[0], order.size, executed_price,
                    0.0, 0.0, 0.0,
                    order.size, abs(order.size) * executed_price, 0.0,
                    0.0, 0.0, order.size, executed_price,
                )
                order.completed()
        self._notify(order)
        return order

    @staticmethod
    def _order_type(order, mt5):
        if order.exectype == bt.Order.Market:
            return mt5.ORDER_TYPE_BUY if order.isbuy() else mt5.ORDER_TYPE_SELL
        if order.exectype == bt.Order.Limit:
            return mt5.ORDER_TYPE_BUY_LIMIT if order.isbuy() else mt5.ORDER_TYPE_SELL_LIMIT
        if order.exectype == bt.Order.Stop:
            return mt5.ORDER_TYPE_BUY_STOP if order.isbuy() else mt5.ORDER_TYPE_SELL_STOP
        raise ValueError("MT5Broker supports Market, Limit and Stop orders")

    def cancel(self, order):
        ticket = order.info.get("mt5_order")
        if not ticket or not order.alive():
            return order
        mt5 = self._store.client.mt5
        result = self._store.client.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            order.cancel(self)
            self._notify(order)
        return order

    def _notify(self, order) -> None:
        self._notifications.append(order.clone())

    def get_notification(self):
        return self._notifications.popleft() if self._notifications else None
