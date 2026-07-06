from __future__ import annotations

from typing import Any


class MT5ConnectionError(RuntimeError):
    """Raised when the MetaTrader terminal cannot be reached."""


class MT5Client:
    """Small, injectable wrapper around the official MetaTrader5 module."""

    def __init__(
        self,
        *,
        path: str | None = None,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        timeout: int = 60_000,
        portable: bool = False,
        module: Any | None = None,
    ) -> None:
        if module is None:
            try:
                import MetaTrader5 as module
            except ImportError as exc:
                raise MT5ConnectionError(
                    "MetaTrader5 is not installed. On Windows run: "
                    "uv sync --extra metatrader"
                ) from exc
        self.mt5 = module
        self.path = path
        self.login = login
        self.password = password
        self.server = server
        self.timeout = timeout
        self.portable = portable

    def connect(self) -> None:
        kwargs: dict[str, Any] = {"timeout": self.timeout, "portable": self.portable}
        if self.login is not None:
            kwargs["login"] = self.login
        if self.password is not None:
            kwargs["password"] = self.password
        if self.server is not None:
            kwargs["server"] = self.server
        args = (self.path,) if self.path else ()
        if not self.mt5.initialize(*args, **kwargs):
            raise MT5ConnectionError(f"MT5 initialize failed: {self.last_error()}")

    def shutdown(self) -> None:
        self.mt5.shutdown()

    def last_error(self) -> Any:
        return self.mt5.last_error()

    def ensure_symbol(self, symbol: str) -> Any:
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise MT5ConnectionError(f"Unknown MT5 symbol: {symbol}")
        if not info.visible and not self.mt5.symbol_select(symbol, True):
            raise MT5ConnectionError(f"Could not select MT5 symbol {symbol}: {self.last_error()}")
        return info

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int):
        return self.mt5.copy_rates_from_pos(symbol, timeframe, start, count)

    def symbol_info_tick(self, symbol: str):
        return self.mt5.symbol_info_tick(symbol)

    def account_info(self):
        return self.mt5.account_info()

    def positions_get(self, *, symbol: str | None = None):
        return self.mt5.positions_get(symbol=symbol) if symbol else self.mt5.positions_get()

    def order_send(self, request: dict[str, Any]):
        return self.mt5.order_send(request)

    def timeframe(self, name: str) -> int:
        try:
            return getattr(self.mt5, f"TIMEFRAME_{name}")
        except AttributeError as exc:
            raise ValueError(f"Unsupported MT5 timeframe: {name}") from exc
