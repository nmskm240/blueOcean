from __future__ import annotations

import streamlit as st

import blueOcean.strategies  # noqa: F401  # Strategy登録のためimportのみ実行
from blueOcean.streamlit_pages import list_strategy_pages


def main() -> None:
    st.set_page_config(page_title="BlueOcean Strategies", layout="wide")
    st.sidebar.title("Strategy ページ")

    pages = list_strategy_pages()
    if not pages:
        st.warning("登録済みのStrategyがありません。decoratorを付与して登録してください。")
        return

    page_titles = [page.title for page in pages]
    selected_title = st.sidebar.radio("表示するStrategy", page_titles, index=0)

    selected_page = next(page for page in pages if page.title == selected_title)
    selected_page.render()


if __name__ == "__main__":
    main()
