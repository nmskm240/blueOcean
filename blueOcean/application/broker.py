import collections

from backtrader.broker import BrokerBase
from backtrader.order import BuyOrder, Order, SellOrder
from backtrader.position import Position

from blueOcean.application.store import IStore
from blueOcean.application.warmup import WarmupState
from blueOcean.infra.logging import logger


class Broker(BrokerBase):
    def __init__(self, store: IStore, warmup_state: WarmupState | None = None):
        super().__init__()
        self._store = store
        if warmup_state is None:
            warmup_state = WarmupState()
            warmup_state.mark_ready()
        self._warmup_state = warmup_state
        self.notifs = collections.deque()
        self.startingcash = self.cash = 0.0
        self.startingvalue = self.value = 0.0

        self.orders: dict[int, Order] = {}
        self.positions: dict[object, Position] = {}

    def getcash(self):
        self.cash = self._store.get_cash()
        return self.cash

    def getvalue(self, datas=None):
        self.value = self._store.get_value()
        return self.value

    def getposition(self, data, clone=True):
        position = self.positions.get(data)
        if not position:
            return None
        return position.clone() if clone else position

    def submit(self, order: Order):
        self.orders[order.ref] = order
        order.submit()
        self.notify(order)

        if not self._warmup_state.is_ready():
            logger.info("Warmup中のため注文は拒否されました。")
            order.reject()
            self.notify(order)
            return order

        self._store.create_order(order)
        order.accept()
        self.notify(order)

        logger.debug(f"Broker order submit. (ref: {order.ref})")

        return order

    def cancel(self, order: Order):
        order = self.orders.get(order.ref, order)
        if order.status == Order.Canceled:
            return

        self._store.cancel_order(order)

        order.cancel()
        self.notify(order)

        return order

    def buy(
        self,
        owner,
        data,
        size,
        price=None,
        plimit=None,
        exectype=None,
        valid=None,
        tradeid=0,
        oco=None,
        trailamount=None,
        trailpercent=None,
        **kwargs,
    ):
        order = BuyOrder(
            owner=owner,
            data=data,
            size=size,
            price=price,
            pricelimit=plimit,
            exectype=exectype,
            valid=valid,
            tradeid=tradeid,
            oco=oco,
            trailamount=trailamount,
            trailpercent=trailpercent,
        )
        order.addinfo(**kwargs)
        order.addcomminfo(self.getcommissioninfo(data))
        return self.submit(order)

    def sell(
        self,
        owner,
        data,
        size,
        price=None,
        plimit=None,
        exectype=None,
        valid=None,
        tradeid=0,
        oco=None,
        trailamount=None,
        trailpercent=None,
        **kwargs,
    ):

        order = SellOrder(
            owner=owner,
            data=data,
            size=size,
            price=price,
            pricelimit=plimit,
            exectype=exectype,
            valid=valid,
            tradeid=tradeid,
            oco=oco,
            trailamount=trailamount,
            trailpercent=trailpercent,
        )
        order.addinfo(**kwargs)
        order.addcomminfo(self.getcommissioninfo(data))
        return self.submit(order)

    def notify(self, order: Order):
        self.notifs.append(order.clone())

    def get_notification(self):
        if not self.notifs:
            return None

        return self.notifs.popleft()

    def next(self):
        self._store.update_account_state()
        self.notifs.append(None)
