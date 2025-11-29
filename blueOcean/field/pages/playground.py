import streamlit as st
import streamlit.components.v1 as components

from blueOcean.field import usecase, widgets
from blueOcean.ohlcv import OhlcvRepository

with st.form("backtest"):
    st.header("Playground")
    settings = widgets.backtest_settings_form()
    strategy = widgets.strategy_selectbox()
    params = widgets.strategy_param_settings_form(strategy)
    submitted = st.form_submit_button("Test")

if submitted:
    with st.spinner("Testing..."):
        repository = OhlcvRepository("data")
        uc = usecase.BacktestUsecase(
            repository,
            settings[1],
            settings[0],
            start_at=settings[2],
            end_at=settings[3],
        )
        result = uc.call(strategy, **params)
    with open(str(result.report_path), 'r') as f:
        html = f.read()

    components.html(html, height=1200, scrolling=True)
