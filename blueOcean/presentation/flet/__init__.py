import flet as ft
from flet_route import Routing, path

from blueOcean.presentation.flet.pages import AccountPage, BotPage, HomePage, StrategiesPage


def run(page: ft.Page):
    routes = [
        path(HomePage.route, clear=True, view=HomePage.render),
        path(BotPage.route, clear=True, view=BotPage.render),
        path(AccountPage.route, clear=True, view=AccountPage.render),
        path(StrategiesPage.route, clear=True, view=StrategiesPage.render),
    ]
    Routing(page=page, app_routes=routes)
    page.scroll = ft.ScrollMode.AUTO
    page.go(page.route)


__all__ = [
    run,
]
