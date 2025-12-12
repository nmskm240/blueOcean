import streamlit as st

import blueOcean.core.strategies
from blueOcean.application.decorators import strategy_registry
from blueOcean.presentation.streamlit.contents.strategies import strategy_page


def setup():
    st.set_page_config(page_title="BlueOcean", layout="wide")

    nav = st.navigation(
        {
            "": [
                st.Page(
                    "./blueOcean/presentation/streamlit/contents/top.py",
                    title="Top",
                    default=True,
                ),
                st.Page(
                    "./blueOcean/presentation/streamlit/contents/playground.py",
                    title="Playground",
                ),
                st.Page(
                    "./blueOcean/presentation/streamlit/contents/bots.py", title="Bots"
                ),
            ],
            "Strategies": [
                st.Page(
                    lambda: strategy_page(page_data),
                    title=page_data.cls.__name__,
                    url_path=page_data.cls.__name__,
                )
                for page_data in strategy_registry
            ],
        }
    )
    nav.run()


__all__ = [
    setup,
]
