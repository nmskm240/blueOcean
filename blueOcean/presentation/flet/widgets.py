from pathlib import Path
from typing import Callable, Type

import backtrader as bt
import ccxt
import flet as ft

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.infra.accessors import ExchangeSymbolDirectoryAccessor
from blueOcean.domain.account import Account
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.shared.registries import StrategyRegistry


class TimeframeDropdown(ft.Dropdown):
    def __init__(self, value: Timeframe = Timeframe.ONE_MINUTE):
        super().__init__(
            value=value,
            options=[ft.DropdownOption(key=e.name, text=e.name) for e in Timeframe],
        )


class ExchangeDropdown(ft.Dropdown):
    def __init__(self, value: str):
        super().__init__(
            value=value,
            # TODO: つかえない取引所を選択肢から外す
            # TODO: ccxt以外にも対応する
            options=[ft.DropdownOption(key=e, text=e) for e in ccxt.exchanges],
        )


class SymbolDropdown(ft.Dropdown):
    def __init__(
        self,
        symbols: list[str],
        value: str | None = None,
    ):
        super().__init__(
            value=value or (symbols[0] if symbols else None),
            options=[ft.dropdown.Option(key=s, text=s) for s in symbols],
        )


class AccountistTile(ft.ListTile):
    def __init__(
        self,
        account: Account,
        on_click: ft.OptionalControlEventCallable,
    ):
        title = account.label or account.credential.exchange
        subtitle = account.credential.exchange if account.label else None

        super().__init__(
            title=ft.Text(title),
            subtitle=ft.Text(subtitle) if subtitle else None,
            leading=ft.Icon(
                ft.Icons.DEVELOPER_MODE
                if account.credential.is_sandbox
                else ft.Icons.MONEY
            ),
            on_click=on_click,
        )


class StrategyDropdown(ft.Dropdown):
    def __init__(self, value: Type[bt.Strategy] | None = None):
        selected_name = StrategyRegistry.name_of(value) if value else None
        super().__init__(
            value=selected_name,
            options=[
                ft.DropdownOption(key=name, text=name) for (name, _) in StrategyRegistry
            ],
        )


class ExchangeSymbolPicker(ft.Control):
    def __init__(
        self,
        *,
        data_dir: str | Path = "data",
        exchange: str | None = None,
        symbol: str | None = None,
        accessor: IExchangeSymbolAccessor | None = None,
        on_change: Callable[[tuple[str, str]], None] | None = None,
    ):
        super().__init__()
        self._accessor = accessor or ExchangeSymbolDirectoryAccessor(data_dir)
        self._initial_exchange = exchange
        self._initial_symbol = symbol
        self._on_change = on_change
        self.exchange_dropdown: ft.Dropdown | None = None
        self.symbol_dropdown: ft.Dropdown | None = None

    def build(self) -> ft.Control:
        mapping = self._accessor.list_exchange_symbols()
        exchanges = list(mapping.keys())
        selected_exchange = (
            self._initial_exchange
            if self._initial_exchange in mapping
            else (exchanges[0] if exchanges else None)
        )
        symbols = mapping.get(selected_exchange, [])
        selected_symbol = (
            self._initial_symbol
            if self._initial_symbol in symbols
            else (symbols[0] if symbols else None)
        )

        self.exchange_dropdown = ft.Dropdown(
            label="exchange",
            value=selected_exchange,
            options=[ft.DropdownOption(key=name, text=name) for name in exchanges],
        )
        self.symbol_dropdown = ft.Dropdown(
            label="symbol",
            value=selected_symbol,
            options=[ft.DropdownOption(key=name, text=name) for name in symbols],
        )

        def _notify() -> None:
            if (
                self._on_change is not None
                and self.exchange_dropdown
                and self.symbol_dropdown
            ):
                self._on_change(self.values())

        def _on_exchange_change(_: ft.ControlEvent) -> None:
            if self.exchange_dropdown is None or self.symbol_dropdown is None:
                return
            current_exchange = self.exchange_dropdown.value
            next_symbols = mapping.get(current_exchange, [])
            self.symbol_dropdown.options = [
                ft.DropdownOption(key=name, text=name) for name in next_symbols
            ]
            self.symbol_dropdown.value = next_symbols[0] if next_symbols else None
            self.symbol_dropdown.update()
            _notify()

        def _on_symbol_change(_: ft.ControlEvent) -> None:
            _notify()

        self.exchange_dropdown.on_change = _on_exchange_change
        self.symbol_dropdown.on_change = _on_symbol_change

        return ft.Row([self.exchange_dropdown, self.symbol_dropdown], spacing=12)

    def values(self) -> tuple[str, str]:
        exchange = self.exchange_dropdown.value if self.exchange_dropdown else None
        symbol = self.symbol_dropdown.value if self.symbol_dropdown else None
        return (exchange or "", symbol or "")
