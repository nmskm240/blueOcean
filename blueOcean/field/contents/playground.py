import streamlit as st
import streamlit.components.v1 as components

from blueOcean.field import usecase, widgets
from blueOcean.ohlcv import OhlcvRepository

with st.form("backtest"):
    st.header("Playground")
    source, symbol, timeframe, start_at, end_at = widgets.backtest_settings_form()
    strategy = widgets.strategy_selectbox()
    with st.expander("params"):
        params = widgets.strategy_param_settings_form(strategy)
    submitted = st.form_submit_button("Test")

if submitted:
    with st.spinner("Testing..."):
        repository = OhlcvRepository("data")
        uc = usecase.BacktestUsecase(
            repository,
            symbol,
            source,
            timeframe,
            start_at,
            end_at,
        )
        result = uc.call(strategy, **params)
    with open(str(result.report_path), "r") as f:
        html = f.read()

    components.html(html, height=1200, scrolling=True)
