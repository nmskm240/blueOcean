import streamlit as st

from blueOcean.application.decorators.registry import StrategyPageData


def strategy_page(data: StrategyPageData):
    st.title(data.cls.__name__)

    overview, notes = st.tabs(["Overview", "Notes"])

    with overview:
        st.code(data.source)

    with notes:
        titles = [t for t, _ in data.notes]
        left, right = st.columns([1, 4])
        with left:
            selected = st.radio("Pages", titles)
        with right:
            for title, content in data.notes:
                if title == selected:
                    st.subheader(title)
                    st.markdown(content or "No contents", unsafe_allow_html=True)
