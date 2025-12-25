from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Callable, Type

import backtrader as bt
import ccxt
import flet as ft

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.application.dto import AccountCredentialInfo
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.infra.accessors import ExchangeSymbolDirectoryAccessor
from blueOcean.presentation.scopes import AccountCredentialDialogScope, Scope
from blueOcean.shared.registries import StrategyRegistry

# region Dropdown


class TimeframeDropdown(ft.Dropdown):
    def __init__(self, value: Timeframe = Timeframe.ONE_MINUTE):
        super().__init__(
            label="timeframe",
            value=value,
            options=[ft.DropdownOption(key=e.name, text=e.name) for e in Timeframe],
        )


class ExchangeDropdown(ft.Dropdown):
    def __init__(self, value: str):
        super().__init__(
            label="exchange",
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
            label="symbol",
            value=value or (symbols[0] if symbols else None),
            options=[ft.dropdown.Option(key=s, text=s) for s in symbols],
        )


class StrategyDropdown(ft.Dropdown):
    def __init__(self, value: Type[bt.Strategy] | None = None):
        selected_name = StrategyRegistry.name_of(value) if value else None
        super().__init__(
            label="strategy_type",
            value=selected_name,
            options=[
                ft.DropdownOption(key=name, text=name) for (name, _) in StrategyRegistry
            ],
        )


# region ListTile


class AccountListTile(ft.ListTile):
    def __init__(
        self,
        info: AccountCredentialInfo,
        on_click: ft.OptionalControlEventCallable = None,
    ):
        title = info.label or info.exchange_name
        subtitle = info.exchange_name if info.label else None

        super().__init__(
            title=ft.Text(title),
            subtitle=ft.Text(subtitle) if subtitle else None,
            leading=ft.Icon(
                ft.Icons.DEVELOPER_MODE
                if info.is_sandbox
                else ft.Icons.MONEY
            ),
            on_click=on_click,
        )


# region Field


class StrategyParamField(ft.Column):
    def __init__(
        self,
        strategy: Type[bt.Strategy] | str,
        *,
        on_change: Callable[[dict[str, Any]], None] | None = None,
    ):
        super().__init__(spacing=8)
        if isinstance(strategy, str):
            self._strategy_name = strategy
            self._strategy_cls = StrategyRegistry.resolve(strategy)
        else:
            self._strategy_cls = strategy
            self._strategy_name = StrategyRegistry.name_of(strategy)
        self._on_change = on_change
        self._params = StrategyRegistry.params_of(self._strategy_cls)
        self._fields: dict[str, ft.Control] = {}
        self.controls = self._build_controls()

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, default in self._params:
            control = self._fields.get(name)
            result[name] = self._read_value(control, default)
        return result

    def _build_controls(self) -> list[ft.Control]:
        controls: list[ft.Control] = []
        self._fields = {}
        for name, default in self._params:
            control = self._build_field(name, default)
            self._fields[name] = control
            controls.append(control)
        return controls

    def _build_field(self, name: str, default: Any) -> ft.Control:
        if isinstance(default, bool):
            checkbox = ft.Checkbox(label=name, value=default)
            checkbox.on_change = self._handle_change
            return checkbox

        keyboard_type = None
        if isinstance(default, (int, float)):
            keyboard_type = ft.KeyboardType.NUMBER

        field = ft.TextField(
            label=name,
            value=str(default),
            keyboard_type=keyboard_type,
        )
        field.on_change = self._handle_change
        return field

    def _read_value(self, control: ft.Control | None, default: Any) -> Any:
        if control is None:
            return default
        if isinstance(control, ft.Checkbox):
            return bool(control.value)
        if isinstance(control, ft.TextField):
            raw = control.value or ""
            if isinstance(default, int):
                try:
                    return int(raw)
                except ValueError:
                    return default
            if isinstance(default, float):
                try:
                    return float(raw)
                except ValueError:
                    return default
            return raw
        return default

    def _handle_change(self, _: ft.ControlEvent) -> None:
        if self._on_change is not None:
            self._on_change(self.values())


# region Dialog


class BacktestDialog(ft.AlertDialog):
    def __init__(self):
        self._notifier = BacktestNotifier()

        super().__init__()
        self.title = ft.Text("Backtest")
        self.modal = True
        self.strategy_dropdown = StrategyDropdown()
        self.param_container = ft.Container()

        if self.strategy_dropdown.value is None and self.strategy_dropdown.options:
            self.strategy_dropdown.value = self.strategy_dropdown.options[0].key

        self._set_param_field(self.strategy_dropdown.value)
        self.strategy_dropdown.on_change = self._on_strategy_change

        self.content = ft.Column(
            [
                ExchangeSymbolPicker(),
                DateRangePicker(),
                TimeframeDropdown(),
                self.strategy_dropdown,
                ft.ExpansionTile(
                    title=ft.Text("Params"),
                    controls=[
                        self.param_container,
                    ],
                ),
            ],
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self.actions = [
            ft.TextButton("Cancel", on_click=self._on_cancel),
            ft.TextButton("Start", on_click=self._on_start),
        ]

    def _set_param_field(self, strategy_name: str | None) -> None:
        if strategy_name:
            self.param_container.content = StrategyParamField(strategy_name)
        else:
            self.param_container.content = ft.Text("No strategy available.")

    def _on_strategy_change(self, _: ft.ControlEvent) -> None:
        self._set_param_field(self.strategy_dropdown.value)
        self.param_container.update()

    def _on_cancel(self, _: ft.ControlEvent):
        self._close()

    def _on_start(self, _: ft.ControlEvent):
        self._notifier.on_request_backtest()
        self._close()

    def _close(self) -> None:
        self.open = False
        if self.page:
            self.page.update()


class FetcherSettingDialog(ft.AlertDialog):
    def __init__(
        self,
        *,
        exchange_options: list[str] | None = None,
        default_exchange: str | None = None,
        default_symbol: str | None = None,
        on_submit: Callable[[str, str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        super().__init__(modal=True)
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        exchanges = exchange_options or list(ccxt.exchanges)
        initial_exchange = default_exchange if default_exchange in exchanges else None
        self.exchange_dropdown = ft.Dropdown(
            label="exchange",
            value=initial_exchange or (exchanges[0] if exchanges else None),
            options=[ft.DropdownOption(key=e, text=e) for e in exchanges],
            autofocus=True,
        )
        self.symbol_field = ft.TextField(
            label="symbol", value=default_symbol or "", hint_text="e.g. BTC/USDT"
        )
        self.actions = [
            ft.TextButton("キャンセル", on_click=self._handle_cancel),
            ft.ElevatedButton("保存", on_click=self._handle_submit),
        ]
        self.content = ft.Column(
            controls=[
                ft.Text("Fetcher settings", weight=ft.FontWeight.BOLD, size=16),
                ft.Text(
                    "取引所とシンボルの組み合わせを選択してください。",
                    color=ft.colors.GREY_700,
                ),
                self.exchange_dropdown,
                self.symbol_field,
            ],
            tight=True,
            width=360,
            spacing=12,
        )

    def _handle_submit(self, _: ft.ControlEvent) -> None:
        if self._on_submit is not None:
            self._on_submit(self.exchange_dropdown.value or "", self.symbol_field.value)
        self.open = False
        self.update()

    def _handle_cancel(self, _: ft.ControlEvent) -> None:
        if self._on_cancel is not None:
            self._on_cancel()
        self.open = False
        self.update()

class AccountCredentialDialog(ft.AlertDialog):
    def __init__(
        self,
        scope: Scope,
        on_submit: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        super().__init__(modal=True)
        self._scope = AccountCredentialDialogScope(scope)
        self._notifier = self._scope.notifier
        self._on_submit = on_submit
        self._on_cancel = on_cancel

        self.label_field = ft.TextField(label="label")
        self.exchange_dropdown = ft.Dropdown(
            label="exchange",
            options=[ft.DropdownOption(key=e, text=e) for e in ccxt.exchanges],
        )
        self.key_field = ft.TextField(label="api key")
        self.secret_field = ft.TextField(
            label="api secret",
            password=True,
            can_reveal_password=True,
        )
        self.sandbox_switch = ft.Switch(label="is sandbox")
        self.actions = [
            ft.TextButton("キャンセル", on_click=self._handle_cancel),
            ft.ElevatedButton("保存", on_click=self._handle_submit),
        ]
        self.content = ft.Column(
            controls=[
                ft.Text("API設定", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.Text(
                    "取引所APIの認証情報を入力してください。",
                    theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                ),
                self.exchange_dropdown,
                self.label_field,
                self.key_field,
                self.secret_field,
                self.sandbox_switch,
            ],
            tight=True,
        )

    def _handle_submit(self, _: ft.ControlEvent) -> None:
        self._notifier.update(
            exchange_name=self.exchange_dropdown.value,
            label=self.label_field.value,
            api_key=self.key_field.value,
            api_secret=self.secret_field.value,
            is_sandbox=self.sandbox_switch.value,
        )
        res = self._notifier.submit()
        if self._on_submit is not None:
            self._on_submit(res)
        self.open = False
        self.update()

    def _handle_cancel(self, _: ft.ControlEvent) -> None:
        if self._on_cancel is not None:
            self._on_cancel()
        self.open = False
        self.update()


# region Picker


class DateRangePicker(ft.Row):
    def __init__(
        self,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
        on_change: callable | None = None,
    ):
        super().__init__(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self.on_change = on_change
        self.start_date: datetime.date | None = start
        self.end_date: datetime.date | None = end

        self.start_picker = ft.DatePicker(
            field_label_text="start_at",
            value=start,
            on_change=self._on_start_change,
        )
        self.end_picker = ft.DatePicker(
            field_label_text="end_at",
            value=end,
            on_change=self._on_end_change,
        )

        self.start_button = ft.OutlinedButton(
            text=self._label_start(),
            icon=ft.Icons.EVENT,
            on_click=lambda _: self._open(self.start_picker),
        )
        self.end_button = ft.OutlinedButton(
            text=self._label_end(),
            icon=ft.Icons.EVENT,
            on_click=lambda _: self._open(self.end_picker),
        )

        self.controls = [
            self.start_button,
            ft.Text("〜"),
            self.end_button,
        ]

    def _open(self, picker: ft.DatePicker):
        if picker not in self.page.overlay:
            self.page.overlay.append(picker)
        picker.open = True
        self.page.update()

    def _label_start(self) -> str:
        return self.start_date.strftime("%Y-%m-%d") if self.start_date else "Start date"

    def _label_end(self) -> str:
        return self.end_date.strftime("%Y-%m-%d") if self.end_date else "End date"

    def _on_start_change(self, e: ft.ControlEvent):
        self.start_date = e.control.value

        # start > end の場合は end を追従させる
        if self.end_date and self.start_date and self.start_date > self.end_date:
            self.end_date = self.start_date
            self.end_picker.value = self.end_date
            self.end_button.text = self._label_end()

        self.start_button.text = self._label_start()
        self._emit_change()

    def _on_end_change(self, e: ft.ControlEvent):
        self.end_date = e.control.value

        # end < start の場合は start を追従させる
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date
            self.start_picker.value = self.start_date
            self.start_button.text = self._label_start()

        self.end_button.text = self._label_end()
        self._emit_change()

    def _emit_change(self):
        if self.on_change:
            self.on_change(self.start_date, self.end_date)
        self.update()

    def value(self) -> tuple[datetime.date | None, datetime.date | None]:
        return self.start_date, self.end_date


class ExchangeSymbolPicker(ft.Row):
    def __init__(
        self,
        *,
        data_dir: str | Path = "data",
        exchange: str | None = None,
        symbol: str | None = None,
        accessor: IExchangeSymbolAccessor | None = None,
        on_change: Callable[[tuple[str, str]], None] | None = None,
    ):
        super().__init__(spacing=12)
        self._accessor = accessor or ExchangeSymbolDirectoryAccessor(data_dir)
        self._initial_exchange = exchange
        self._initial_symbol = symbol
        self._on_change = on_change
        self.exchange_dropdown: ft.Dropdown | None = None
        self.symbol_dropdown: ft.Dropdown | None = None

        self._build_controls()

    def _build_controls(self) -> None:
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
        self.controls = [self.exchange_dropdown, self.symbol_dropdown]

    def values(self) -> tuple[str, str]:
        exchange = self.exchange_dropdown.value if self.exchange_dropdown else None
        symbol = self.symbol_dropdown.value if self.symbol_dropdown else None
        return (exchange or "", symbol or "")
