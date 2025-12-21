from abc import ABCMeta, abstractmethod

import flet as ft
from flet_route import Basket, Params

from blueOcean.presentation.flet.layout import RootLayout


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
            cls.route,
            controls=[
                RootLayout(
                    index=cls.order,
                    content=ft.Text("Home"),
                ),
            ],
        )


class BotPage(IPage, RootLayout.IRootNavigationItem):
    order = 1
    route = "/bots"
    destination = ft.NavigationRailDestination(
        icon=ft.Icon(ft.Icons.SMART_TOY),
        label="Bots",
    )

    @classmethod
    def render(cls, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        return ft.View(
            cls.route,
            controls=[
                RootLayout(
                    index=cls.order,
                    content=ft.Text("Bot"),
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

    @classmethod
    def render(cls, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        return ft.View(
            cls.route,
            controls=[
                RootLayout(
                    index=cls.order,
                    content=ft.Text("Account"),
                ),
            ],
        )


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
            cls.route,
            controls=[
                RootLayout(
                    index=cls.order,
                    content=ft.Text("Strategies"),
                ),
            ],
        )
