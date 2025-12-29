from abc import ABCMeta

import flet as ft


class RootLayout(ft.Row):
    class IRootNavigationItem(metaclass=ABCMeta):
        destination: ft.NavigationRailDestination
        route: str
        order: int = 0

    def __init__(self, index: int, content: ft.Control):
        super().__init__()
        item_classes = list(RootLayout.IRootNavigationItem.__subclasses__())
        item_classes.sort(key=lambda cls: getattr(cls, "order", 0))
        self.items = item_classes
        self.expand = True
        self.controls = [
            ft.NavigationRail(
                destinations=[e.destination for e in self.items],
                selected_index=index,
                on_change=self._on_navigation_change,
            ),
            ft.VerticalDivider(width=1),
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=24),
                content=ft.Container(
                    width=960,
                    content=content,
                ),
            ),
        ]

    def _on_navigation_change(self, event: ft.ControlEvent):
        selected_index = int(event.data)
        route = self.items[selected_index].route
        self.page.go(route)
