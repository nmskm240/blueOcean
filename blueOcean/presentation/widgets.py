from __future__ import annotations

import base64
import datetime
import io
from typing import Any, Callable, Type

import backtrader as bt
import ccxt
import flet as ft
import matplotlib.pyplot as plt
import pandas as pd
import quantstats as qs

from blueOcean.application.accessors import IExchangeSymbolAccessor
from blueOcean.application.dto import AccountCredentialInfo, BotInfo, TimeReturnPoint
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.presentation.scopes import (
    AccountCredentialDialogScope,
    BacktestDialogScope,
    OhlcvFetchDialogScope,
    Scope,
)
from blueOcean.shared.registries import StrategyRegistry

# region AppBar


class RootAppBar(ft.AppBar):
    def __init__(self, scope: Scope):
        super().__init__()

        self._scope = scope
        self.actions = [
            ft.IconButton(
                icon=ft.Icons.CACHED,
                on_click=self._open_fetcher_dialog,
            )
        ]

    def _open_fetcher_dialog(self, e: ft.ControlEvent) -> None:
        dialog = OhlcvFetchDialog(self._scope)
        e.control.page.overlay.append(dialog)
        dialog.open = True
        e.control.page.update()


# region Dropdown


class TimeframeDropdown(ft.Dropdown):
    def __init__(self, value: Timeframe = Timeframe.ONE_MINUTE):
        super().__init__(
            label="timeframe",
            value=value.name,
            options=[ft.DropdownOption(key=e.name, text=e.name) for e in Timeframe],
        )

    @property
    def parsed_value(self) -> Timeframe:
        return Timeframe[self.value]

class ExchangeDropdown(ft.Dropdown):
    def __init__(self, value: str | None = None, exchanges: list[str] | None = None):
        options = exchanges if exchanges is not None else ccxt.exchanges
        super().__init__(
            label="exchange",
            value=value or "",
            options=[ft.DropdownOption(key=e, text=e) for e in options],
            expand=True,
        )


class SymbolDropdown(ft.Dropdown):
    def __init__(
        self,
        symbols: list[str] = [],
        value: str | None = None,
    ):
        super().__init__(
            label="symbol",
            value=value or (symbols[0] if symbols else None),
            options=[ft.dropdown.Option(key=s, text=s) for s in symbols],
            expand=True,
        )


class AccountDropdown(ft.Dropdown):
    def __init__(
        self,
        accounts: list[AccountCredentialInfo],
        value: str | None = None,
    ):
        super().__init__(
            label="account",
            value=value,
            options=[
                ft.DropdownOption(
                    key=account.account_id,
                    text=account.label or account.exchange_name,
                )
                for account in accounts
            ],
            expand=True,
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
                ft.Icons.DEVELOPER_MODE if info.is_sandbox else ft.Icons.MONEY
            ),
            on_click=on_click,
        )


class BotListTile(ft.ListTile):
    def __init__(
        self,
        info: BotInfo,
        on_click: ft.OptionalControlEventCallable = None,
    ):
        title = info.label or info.symbol or info.bot_id
        subtitle = " | ".join(
            part
            for part in [
                info.mode,
                info.status,
                info.source,
                info.symbol,
                info.timeframe.name,
                info.strategy,
            ]
            if part
        )
        icon = (
            ft.Icons.PLAY_ARROW
            if info.status == "RUNNING"
            else (
                ft.Icons.STOP_CIRCLE if info.status == "STOPPED" else ft.Icons.SMART_TOY
            )
        )

        super().__init__(
            title=ft.Text(title),
            subtitle=ft.Text(subtitle) if subtitle else None,
            leading=ft.Icon(icon),
            on_click=on_click,
        )


class StrategyListTile(ft.ListTile):
    def __init__(
        self,
        name: str,
        strategy_cls: Type[bt.Strategy] | None = None,
        on_click: ft.OptionalControlEventCallable = None,
    ):
        subtitle = strategy_cls.__module__ if strategy_cls else None
        super().__init__(
            title=ft.Text(name),
            subtitle=ft.Text(subtitle) if subtitle else None,
            leading=ft.Icon(ft.Icons.PATTERN),
            on_click=on_click,
        )


# region Reports


class QuantstatsReportWidget(ft.Column):
    def __init__(self, time_returns: list[TimeReturnPoint]):
        super().__init__(spacing=12, expand=True)
        self._time_returns = time_returns
        self.controls = self._build_controls()

    def _build_controls(self) -> list[ft.Control]:
        returns = self._build_returns()
        if returns is None or returns.empty:
            return [ft.Text("Report not found.")]

        report = self._build_report(returns)
        report_items = [
            ft.Text(
                f"Total return: {self._format_value(report['total_return'], True)}"
            ),
            ft.Text(f"CAGR: {self._format_value(report['cagr'], True)}"),
            ft.Text(f"Sharpe: {self._format_value(report['sharpe'], False)}"),
            ft.Text(f"Sortino: {self._format_value(report['sortino'], False)}"),
            ft.Text(f"Volatility: {self._format_value(report['volatility'], True)}"),
            ft.Text(
                f"Max drawdown: {self._format_value(report['max_drawdown'], True)}"
            ),
            ft.Text(f"Win rate: {self._format_value(report['win_rate'], True)}"),
        ]

        return [
            ft.Column(controls=report_items, spacing=4),
            ft.Divider(height=1),
            self._build_equity_image(returns),
            self._build_drawdown_image(returns),
        ]

    def _build_returns(self) -> pd.Series | None:
        if not self._time_returns:
            return None
        returns = pd.Series(
            [point.value for point in self._time_returns],
            index=pd.to_datetime([point.timestamp for point in self._time_returns]),
            dtype=float,
        ).sort_index()
        return returns

    def _build_report(self, returns: pd.Series) -> dict[str, float | None]:
        return {
            "total_return": self._safe_stat(qs.stats.comp, returns),
            "cagr": self._safe_stat(qs.stats.cagr, returns),
            "sharpe": self._safe_stat(qs.stats.sharpe, returns),
            "sortino": self._safe_stat(qs.stats.sortino, returns),
            "volatility": self._safe_stat(qs.stats.volatility, returns),
            "max_drawdown": self._safe_stat(qs.stats.max_drawdown, returns),
            "win_rate": self._safe_stat(qs.stats.win_rate, returns),
        }

    def _build_equity_image(self, returns: pd.Series) -> ft.Image:
        equity = (1 + returns).cumprod()
        return self._build_line_chart(
            equity.index,
            equity.values,
            title="Equity Curve",
        )

    def _build_drawdown_image(self, returns: pd.Series) -> ft.Image:
        equity = (1 + returns).cumprod()
        drawdown = equity / equity.cummax() - 1
        return self._build_line_chart(
            drawdown.index,
            drawdown.values,
            title="Drawdown",
        )

    def _build_line_chart(self, x, y, title: str) -> ft.Image:
        fig, ax = plt.subplots(figsize=(8, 2.6))
        ax.plot(x, y, linewidth=1.4)
        ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=120)
        plt.close(fig)
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("ascii")
        return ft.Image(src=encoded, expand=True)

    def _safe_stat(self, fn, *args, **kwargs) -> float | None:
        try:
            value = fn(*args, **kwargs)
        except Exception:
            return None
        if value is None:
            return None
        return float(value)

    def _format_value(self, value: float | None, as_percent: bool) -> str:
        if value is None:
            return "-"
        return f"{value:.2%}" if as_percent else f"{value:.3f}"


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
    def __init__(self, scope: Scope):
        super().__init__()
        self._scope = BacktestDialogScope(scope)
        self._notifier = self._scope.notifier

        self.title = ft.Text("Backtest")
        self.modal = True

        self.exchange_symbol_picker = ExchangeSymbolPicker(
            self._scope.exchange_symbol_accessor
        )
        self.date_range_picker = DateRangePicker()
        self.timeframe_dropdown = TimeframeDropdown()
        self.strategy_dropdown = StrategyDropdown()
        self.param_container = ft.Container()

        if self.strategy_dropdown.value is None and self.strategy_dropdown.options:
            self.strategy_dropdown.value = self.strategy_dropdown.options[0].key

        self._set_param_field(self.strategy_dropdown.value)
        self.strategy_dropdown.on_select = self._on_strategy_change

        self.content = ft.Column(
            [
                self.exchange_symbol_picker,
                self.date_range_picker,
                self.timeframe_dropdown,
                ft.Divider(),
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
            ft.TextButton("Start", on_click=self._handle_on_submit),
        ]

    def _set_param_field(self, strategy_name: str | None) -> None:
        if strategy_name:
            self.param_container.content = StrategyParamField(strategy_name)
        else:
            self.param_container.content = ft.Text("No strategy available.")

    def _on_strategy_change(self, e: ft.ControlEvent) -> None:
        self._set_param_field(e.control.value)
        self.param_container.update()

    def _on_cancel(self, _: ft.ControlEvent):
        self._handle_on_close()

    def _handle_on_submit(self, _: ft.ControlEvent):
        exchange, symbol = self.exchange_symbol_picker.values()
        start_date, end_date = self.date_range_picker.value()
        strategy_args: dict[str, Any] = {}
        if isinstance(self.param_container.content, StrategyParamField):
            strategy_args = self.param_container.content.values()
        self._notifier.update(
            source=exchange,
            symbol=symbol,
            timeframe=self.timeframe_dropdown.parsed_value,
            strategy=self.strategy_dropdown.value,
            strategy_args=strategy_args,
            start_date=start_date,
            end_date=end_date,
        )
        self._notifier.on_request_backtest()
        self._handle_on_close()

    def _handle_on_close(self) -> None:
        self.open = False
        if self.page:
            self.page.update()


class OhlcvFetchDialog(ft.AlertDialog):
    def __init__(
        self,
        scope: Scope,
        on_submit: Callable[[], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ):
        super().__init__(modal=True)
        self._scope = OhlcvFetchDialogScope(scope)
        self._notifier = self._scope.notifier
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        state = self._notifier.state
        self._account_exchange_map = {
            account.account_id: account.exchange_name for account in state.accounts
        }
        self.account_dropdown = AccountDropdown(
            accounts=state.accounts,
            value=state.account or None,
        )
        self.symbol_textfield = ft.TextField(
            label="symbol",
        )
        self.actions = [
            ft.TextButton("キャンセル", on_click=self._handle_cancel),
            ft.ElevatedButton(
                "保存",
                on_click=self._handle_submit,
                disabled=not state.accounts,
            ),
        ]
        self.content = ft.Column(
            controls=[
                ft.Text(
                    "価格データ保存",
                    theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                ),
                ft.Text(
                    "取引所とシンボルの組み合わせを選択してください。",
                    theme_style=ft.TextThemeStyle.BODY_MEDIUM,
                ),
                self.account_dropdown,
                self.symbol_textfield,
            ],
            tight=True,
            width=360,
            spacing=12,
        )

    def _handle_submit(self, _: ft.ControlEvent) -> None:
        self._notifier.update(
            account=self.account_dropdown.value or None,
            symbol=self.symbol_textfield.value,
        )
        self._notifier.submit()
        if self._on_submit is not None:
            self._on_submit()
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
        state = self._notifier.state

        self.label_field = ft.TextField(label="label")
        self.exchange_dropdown = ft.Dropdown(
            label="exchange",
            options=[ft.DropdownOption(key=e, text=e) for e in state.exchange_options],
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
            drift=AccountCredentialInfo(
                exchange_name=self.exchange_dropdown.value,
                label=self.label_field.value,
                api_key=self.key_field.value,
                api_secret=self.secret_field.value,
                is_sandbox=self.sandbox_switch.value,
            )
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
            content=self._label_start(),
            icon=ft.Icons.EVENT,
            on_click=lambda _: self._open(self.start_picker),
        )
        self.end_button = ft.OutlinedButton(
            content=self._label_end(),
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
            self.end_button.content = self._label_end()

        self.start_button.content = self._label_start()
        self._emit_change()

    def _on_end_change(self, e: ft.ControlEvent):
        self.end_date = e.control.value

        # end < start の場合は start を追従させる
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date
            self.start_picker.value = self.start_date
            self.start_button.content = self._label_start()

        self.end_button.content = self._label_end()
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
        accessor: IExchangeSymbolAccessor,
        on_change: Callable[[tuple[str, str]], None] | None = None,
    ):
        super().__init__(spacing=12)
        self._accessor = accessor
        self._on_change = on_change

        self.exchange_dropdown = ft.Dropdown(
            label="exchange",
            options=[ft.DropdownOption(key=e, text=e) for e in accessor.exchanges],
            on_select=self._handle_changed_exchange,
            expand=True,
        )
        self.symbol_dropdown = ft.Dropdown(
            label="symbol",
            expand=True,
            disabled=True,
        )

        self.controls = [self.exchange_dropdown, self.symbol_dropdown]

    def _handle_changed_exchange(self, e: ft.ControlEvent):
        exchange = e.control.value
        self.symbol_dropdown.options = [
            ft.DropdownOption(key=symbol, text=symbol)
            for symbol in self._accessor.symbols_for(exchange)
        ]
        self.symbol_dropdown.value = None
        self.symbol_dropdown.disabled = not bool(exchange)
        self.symbol_dropdown.update()

    def values(self) -> tuple[str, str]:
        exchange = self.exchange_dropdown.value
        symbol = self.symbol_dropdown.value
        return (exchange or "", symbol or "")
