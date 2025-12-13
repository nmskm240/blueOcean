import streamlit as st

from blueOcean.application import usecases
from blueOcean.application.dto import BacktestConfig, DatetimeRange
from blueOcean.presentation.streamlit import widgets

with st.form("backtest"):
    st.header("Playground")
    source, symbol, timeframe, start_at, end_at = widgets.backtest_settings_form()
    strategy = widgets.strategy_selectbox()
    with st.expander("params"):
        params = widgets.strategy_param_settings_form(strategy)
    submitted = st.form_submit_button("Test")

if submitted:
    with st.spinner("Testing..."):
        config = BacktestConfig(
            symbol=symbol,
            source=source,
            compression=timeframe.value,
            strategy_cls=strategy,
            strategy_args=params,
            cash=10_000,
            time_range=DatetimeRange(start_at=start_at, end_at=end_at),
        )
        worker = usecases.run_bot(config)
        worker.join()
    st.toast("Backtest completed", icon="🎉")
