from blueOcean.streamlit_pages import (
    clear_strategy_pages,
    list_strategy_pages,
    strategy_page,
)


def setup_function(_function):
    clear_strategy_pages()


def test_strategy_registration_and_parameters():
    @strategy_page(title="テストストラテジー", description="説明")
    class DummyStrategy:
        def __init__(self, length: int, threshold: float = 1.0):
            self.length = length
            self.threshold = threshold

    pages = list_strategy_pages()
    assert len(pages) == 1
    page = pages[0]
    assert page.title == "テストストラテジー"
    assert page.description == "説明"

    params = page.get_parameters()
    assert "length" in params and not params["length"].has_default
    assert params["length"].annotation is int
    assert "threshold" in params and params["threshold"].has_default
    assert params["threshold"].default == 1.0


def test_multiple_strategy_registration_order_preserved():
    @strategy_page(title="Strategy A")
    class StrategyA:
        pass

    @strategy_page(title="Strategy B")
    class StrategyB:
        pass

    titles = [page.title for page in list_strategy_pages()]
    assert titles == ["Strategy A", "Strategy B"]
