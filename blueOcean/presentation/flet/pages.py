from abc import ABCMeta, abstractmethod

import flet as ft
from flet_route import Basket, Params
from blueOcean.domain.bot import BotId
from blueOcean.presentation.flet.layout import RootLayout
from blueOcean.presentation.flet.widgets import (
    AccountCredentialDialog,
    AccountListTile,
    BacktestDialog,
    BotListTile,
    QuantstatsReportWidget,
    StrategyListTile,
)
from blueOcean.presentation.scopes import (
    AccountPageScope,
    BotDetailPageScope,
    BotTopPageScope,
    Scope,
)
from blueOcean.shared.registries import StrategyRegistry


class IPage(metaclass=ABCMeta):
    route: str

    @classmethod
    @abstractmethod
    def render(cls, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        raise NotImplementedError()


class HomePage(IPage, RootLayout.IRootNavigationItem):
    order = 0
    route = "/"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.HOME),
        label="Home",
    )

    @classmethod
    def render(cls, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        return ft.View(
            route=cls.route,
            controls=[
                RootLayout(
                    index=cls.order,
                    content=ft.Text("Home"),
                ),
            ],
        )


class BotTopPage(IPage, RootLayout.IRootNavigationItem):
    order = 1
    route = "/bots"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.SMART_TOY),
        label="Bots",
    )

    def __init__(self, scope: Scope):
        self._scope = BotTopPageScope(scope)
        self._notifier = self._scope.notifier

    def render(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:

        return ft.View(
            route=BotTopPage.route,
            floating_action_button=ft.FloatingActionButton(
                icon=ft.Icon(ft.Icons.ADD),
                content=ft.PopupMenuButton(
                    expand=True,
                    items=[
                        ft.PopupMenuItem(
                            content=ft.Text("Backtest"),
                            on_click=self._open_backtest,
                        ),
                        ft.PopupMenuItem(
                            content=ft.Text("Live bot"),
                        ),
                    ],
                ),
            ),
            controls=[
                RootLayout(
                    index=BotTopPage.order,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Bots",
                                theme_style=ft.TextThemeStyle.HEADLINE_LARGE,
                            ),
                            ft.Divider(height=1),
                            ft.ListView(
                                controls=[
                                    BotListTile(
                                        info,
                                        on_click=self._open_detail(info.bot_id),
                                    )
                                    for info in self._notifier.state.bots
                                ]
                            ),
                        ]
                    ),
                ),
            ],
        )

    def _open_backtest(self, e: ft.ControlEvent) -> None:
        backtest_dialog = BacktestDialog(self._scope)
        e.control.page.overlay.append(backtest_dialog)
        backtest_dialog.open = True
        e.control.page.update()

    def _open_detail(self, bot_id: str):
        def handler(e: ft.ControlEvent) -> None:
            e.control.page.go(f"/bots/{bot_id}")

        return handler


class BotDetailPage(IPage):
    route = "/bots/:bot_id"

    def __init__(self, scope: Scope):
        self.__parent_scope = scope

    def render(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        bot_id = params.get("bot_id")
        self._scope = BotDetailPageScope(self.__parent_scope, BotId(bot_id))
        self._notifier = self._scope.notifier
        state = self._notifier.state

        content = ft.Column(
            controls=[
                ft.Text(
                    (
                        state.info.label or state.info.symbol or state.info.bot_id
                        if state.info
                        else bot_id
                    ),
                    theme_style=ft.TextThemeStyle.HEADLINE_LARGE,
                ),
                ft.Divider(height=1),
                QuantstatsReportWidget(state.time_returns),
            ],
            expand=True,
        )

        return ft.View(
            route=f"/bots/{bot_id}",
            controls=[
                RootLayout(
                    index=BotTopPage.order,
                    content=content,
                ),
            ],
        )


class AccountPage(IPage, RootLayout.IRootNavigationItem):
    order = 2
    route = "/accounts"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.GROUP),
        label="Accounts",
    )

    def __init__(self, scope: Scope):
        self._scope = AccountPageScope(scope)
        self._notifier = self._scope.notifier

    def render(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        return ft.View(
            route=self.route,
            controls=[
                RootLayout(
                    index=self.order,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "アカウント",
                                theme_style=ft.TextThemeStyle.HEADLINE_LARGE,
                            ),
                            ft.ElevatedButton(
                                "登録",
                                icon=ft.Icons.ADD,
                                on_click=self._open_regist_dialog,
                            ),
                            ft.Divider(height=1),
                            ft.ListView(
                                controls=[
                                    AccountListTile(info)
                                    for info in self._notifier.state
                                ]
                            ),
                        ]
                    ),
                ),
            ],
        )

    def _open_regist_dialog(self, e: ft.ControlEvent) -> None:
        def on_submit():
            self._notifier.update()
            e.control.page.update()

        dialog = AccountCredentialDialog(self._scope, on_submit=lambda _: on_submit)
        e.control.page.overlay.append(dialog)
        dialog.open = True
        e.control.page.update()


class StrategiesPage(IPage, RootLayout.IRootNavigationItem):
    order = 3
    route = "/strategies"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.PATTERN),
        label="Strategy",
    )

    @classmethod
    def render(cls, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        return ft.View(
            route=cls.route,
            controls=[
                RootLayout(
                    index=cls.order,
                    content=ft.Text("Strategies"),
                ),
            ],
        )
