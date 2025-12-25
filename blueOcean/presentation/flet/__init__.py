import flet as ft
from flet_route import Routing, path

from blueOcean.presentation.flet.pages import (
    AccountPage,
    BotPage,
    HomePage,
    StrategiesPage,
)
from blueOcean.presentation.scopes import AppScope


def run(page: ft.Page):
    app_scope = AppScope()
    routes = [
        path(HomePage.route, clear=True, view=HomePage.render),
        path(BotPage.route, clear=True, view=BotPage.render),
        path(
            AccountPage.route,
            clear=True,
            view=lambda page, params, basket: AccountPage(app_scope).render(
                page, params, basket
            ),
        ),
        path(StrategiesPage.route, clear=True, view=StrategiesPage.render),
    ]
    Routing(
        page=page,
        app_routes=routes,
        appbar=ft.AppBar(),
    )
    page.scroll = ft.ScrollMode.AUTO
    page.go(page.route)


__all__ = [
    run,
]
