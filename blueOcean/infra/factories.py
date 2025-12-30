import ccxt
from injector import inject

from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.application.store import IStore, IStoreFactory
from blueOcean.domain.account import AccountId
from blueOcean.domain.ohlcv import OhlcvFetcher
from blueOcean.infra.database.repositories import AccountRepository
from blueOcean.infra.fetchers import CcxtOhlcvFetcher
from blueOcean.infra.stores import CcxtSpotStore, OandaStore


class OhlcvFetcherFactory(IOhlcvFetcherFactory):
    @inject
    def __init__(self, account_repository: AccountRepository):
        self._account_repository = account_repository

    def create(self, account_id: AccountId) -> OhlcvFetcher:
        account = self._account_repository.find_by_id(account_id)
        cred = account.credential
        exchange_cls = getattr(ccxt, cred.exchange)
        exchange = exchange_cls({"apiKey": cred.key, "secret": cred.secret})
        exchange.set_sandbox_mode(cred.is_sandbox)
        return CcxtOhlcvFetcher(exchange)


class StoreFactory(IStoreFactory):
    @inject
    def __init__(self, account_repository: AccountRepository):
        self._account_repository = account_repository

    def create(self, account_id: AccountId, symbol: str) -> IStore:
        account = self._account_repository.find_by_id(account_id)
        cred = account.credential

        if cred.exchange.lower() == "oanda":
            environment = "practice" if cred.is_sandbox else "live"
            return OandaStore(
                access_token=cred.key,
                account_id=cred.secret,
                symbol=symbol,
                environment=environment,
            )

        exchange_cls = getattr(ccxt, cred.exchange, None)
        if exchange_cls is None:
            raise RuntimeError(f"Unsupported exchange: {cred.exchange}")
        exchange = exchange_cls({"apiKey": cred.key, "secret": cred.secret})
        exchange.set_sandbox_mode(cred.is_sandbox)
        return CcxtSpotStore(exchange, symbol)
