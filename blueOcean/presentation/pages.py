from abc import ABCMeta, abstractmethod

import flet as ft
from flet_route import Basket, Params
from blueOcean.domain.bot import BotId
from blueOcean.presentation.layout import RootLayout
from blueOcean.presentation.widgets import (
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
    PlaygroundHistoryDetailPageScope,
    PlaygroundHistoryPageScope,
    PlaygroundPageScope,
    Scope,
)
from blueOcean.presentation.utils import parse_with_base64_images_markdown
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
        content_wrapper = ft.Container(
            content=ft.Column(
                controls=[ft.ProgressRing(), ft.Text("Loading...")],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True,
        )

        def load_detail() -> None:
            try:
                self._scope = BotDetailPageScope(self.__parent_scope, BotId(bot_id))
                self._notifier = self._scope.notifier
                state = self._notifier.state
                content_wrapper.content = ft.Column(
                    controls=[
                        ft.Text(
                            (
                                state.info.label
                                or state.info.symbol
                                or state.info.bot_id
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
            except Exception as exc:
                content_wrapper.content = ft.Text(str(exc))
            page.update()

        page.run_thread(load_detail)

        return ft.View(
            route=f"/bots/{bot_id}",
            controls=[
                RootLayout(
                    index=BotTopPage.order,
                    content=content_wrapper,
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


class PlaygroundPage(IPage, RootLayout.IRootNavigationItem):
    order = 4
    route = "/playground"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.PLAY_CIRCLE),
        label="Playground",
    )

    def __init__(self, scope: Scope):
        self._scope = PlaygroundPageScope(scope)
        self._notifier = self._scope.notifier

    def render(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        state = self._notifier.state
        if state.selected_notebook and not state.parameters:
            self._notifier.select_notebook(state.selected_notebook)
            state = self._notifier.state

        parameter_column = ft.Column(spacing=12)
        result_container = ft.Container(expand=True)
        loading_container = ft.Container(
            content=ft.Column(
                controls=[ft.ProgressRing(), ft.Text("実行中...")],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True,
            visible=False,
        )

        def refresh_parameters() -> None:
            parameter_column.controls = [
                ft.TextField(
                    label=parameter.name,
                    value=state.parameter_values.get(parameter.name, ""),
                    on_change=on_parameter_change(parameter.name),
                )
                for parameter in state.parameters
            ]

        def refresh_result() -> None:
            if state.markdown:
                result_container.content = parse_with_base64_images_markdown(
                    state.markdown
                )
            else:
                result_container.content = ft.Text("実行結果はまだありません。")

        def on_parameter_change(name: str):
            def handler(e: ft.ControlEvent) -> None:
                values = dict(self._notifier.state.parameter_values)
                values[name] = e.control.value
                self._notifier.update(parameter_values=values)

            return handler

        def on_notebook_change(e: ft.ControlEvent) -> None:
            self._notifier.select_notebook(e.control.value)
            nonlocal state
            state = self._notifier.state
            refresh_parameters()
            page.update()

        def on_execute(e: ft.ControlEvent) -> None:
            loading_container.visible = True
            result_container.visible = False
            page.update()

            def run():
                self._notifier.execute()
                nonlocal state
                state = self._notifier.state
                refresh_result()
                loading_container.visible = False
                result_container.visible = True
                page.update()

            page.run_thread(run)

        refresh_parameters()
        refresh_result()

        notebook_options = [
            ft.DropdownOption(key=name, text=name) for name in state.notebooks
        ]
        notebook_dropdown = ft.Dropdown(
            label="Notebook",
            options=notebook_options,
            value=state.selected_notebook,
            on_change=on_notebook_change,
            expand=True,
        )

        return ft.View(
            route=self.route,
            controls=[
                RootLayout(
                    index=self.order,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Playground",
                                        theme_style=ft.TextThemeStyle.HEADLINE_LARGE,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.HISTORY,
                                        tooltip="履歴",
                                        on_click=lambda _: page.go(
                                            "/playground/history"
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            notebook_dropdown,
                            ft.Text("Parameters"),
                            parameter_column,
                            ft.ElevatedButton(
                                "実行",
                                icon=ft.Icons.PLAY_ARROW,
                                on_click=on_execute,
                                disabled=not state.selected_notebook,
                            ),
                            ft.Divider(height=1),
                            ft.Text("結果"),
                            loading_container,
                            result_container,
                        ],
                        spacing=12,
                        expand=True,
                    ),
                ),
            ],
        )


class PlaygroundHistoryPage(IPage, RootLayout.IRootNavigationItem):
    order = 5
    route = "/playground/history"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.HISTORY),
        label="Playground History",
    )

    def __init__(self, scope: Scope):
        self._scope = PlaygroundHistoryPageScope(scope)
        self._notifier = self._scope.notifier

    def render(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        self._notifier.refresh()
        state = self._notifier.state

        def open_detail(run_id: str):
            def handler(e: ft.ControlEvent) -> None:
                e.control.page.go(f"/playground/history/{run_id}")

            return handler

        list_view = ft.ListView(
            controls=[
                ft.ListTile(
                    title=ft.Text(run.notebook_path),
                    subtitle=ft.Text(
                        f"{run.executed_at} | {run.status}"
                    ),
                    on_click=open_detail(run.run_id),
                )
                for run in state.runs
            ],
            expand=True,
        )

        return ft.View(
            route=self.route,
            controls=[
                RootLayout(
                    index=self.order,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Playground 履歴",
                                theme_style=ft.TextThemeStyle.HEADLINE_LARGE,
                            ),
                            list_view,
                        ],
                        expand=True,
                    ),
                ),
            ],
        )


class PlaygroundHistoryDetailPage(IPage):
    route = "/playground/history/:run_id"

    def __init__(self, scope: Scope):
        self._scope = PlaygroundHistoryDetailPageScope(scope)
        self._notifier = self._scope.notifier

    def render(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        run_id = params.get("run_id")
        content_wrapper = ft.Container(
            content=ft.Column(
                controls=[ft.ProgressRing(), ft.Text("Loading...")],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True,
        )

        def load_detail() -> None:
            try:
                self._notifier.load(run_id)
                run = self._notifier.state.run
                if run is None:
                    content_wrapper.content = ft.Text("履歴が見つかりません。")
                else:
                    content_wrapper.content = ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "実行結果",
                                        theme_style=ft.TextThemeStyle.HEADLINE_LARGE,
                                    ),
                                    ft.ElevatedButton(
                                        "一覧へ戻る",
                                        on_click=lambda _: page.go(
                                            "/playground/history"
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(run.notebook_path),
                            ft.Text(f"{run.executed_at} | {run.status}"),
                            parse_with_base64_images_markdown(run.markdown),
                        ],
                        expand=True,
                    )
            except Exception as exc:
                content_wrapper.content = ft.Text(str(exc))
            page.update()

        page.run_thread(load_detail)

        return ft.View(
            route=f"/playground/history/{run_id}",
            controls=[
                RootLayout(
                    index=PlaygroundHistoryPage.order,
                    content=content_wrapper,
                ),
            ],
        )
