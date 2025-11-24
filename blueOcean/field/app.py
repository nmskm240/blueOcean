import streamlit as st

from blueOcean.field.pages.strategies import strategy_pages

nav = st.navigation(
    {
        "": [
            st.Page("./pages/top.py", title="Top", default=True),
        ],
        "Strategies": [st.Page(p.render, title=p.title, url_path=p.strategy_cls.__name__) for p in strategy_pages],
    }
)
nav.run()
