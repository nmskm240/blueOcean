import ccxt
from injector import inject

from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.domain.account import AccountId
from blueOcean.domain.ohlcv import OhlcvFetcher
from blueOcean.infra.database.repositories import AccountRepository
from blueOcean.infra.fetchers import CcxtOhlcvFetcher


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
