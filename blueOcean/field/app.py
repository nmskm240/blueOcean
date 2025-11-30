import streamlit as st

from blueOcean.field.decorators import strategy_pages

st.set_page_config(page_title="BlueOcean", layout="wide")

nav = st.navigation(
    {
        "": [
            st.Page("./contents/top.py", title="Top", default=True),
            st.Page("./contents/playground.py", title="Playground"),
        ],
        "Strategies": [
            st.Page(p.render, title=p.cls.__name__, url_path=p.cls.__name__)
            for p in strategy_pages
        ],
    }
)
nav.run()
