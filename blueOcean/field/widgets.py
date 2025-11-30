import streamlit as st
import ccxt
from blueOcean.field import usecase
from blueOcean.field.decorators import strategy_parameter_map
from blueOcean.ohlcv import CcxtOhlcvFetcher, OhlcvRepository, Timeframe


def ohlcv_fetch_form():
    with st.form("data_fetch"):
        st.header("Data fetch")
        source = st.selectbox("source", ccxt.exchanges)
        symbol = st.text_input("symbol")
        submitted = st.form_submit_button("Fetch")

    if not submitted:
        return

    with st.spinner("Fetching..."):
        repository = OhlcvRepository("data")
        fetcher = CcxtOhlcvFetcher(source)
        uc = usecase.FetchOhlcvUsecase(repository, fetcher)
        uc.call(source, symbol)


def backtest_settings_form():
    source = st.text_input("source")
    symbol = st.text_input("symbol")
    timeframe = st.selectbox("timeframe", [e.name for e in Timeframe])
    col1, col2 = st.columns(2)
    with col1:
        start_at = st.date_input("start_at")
    with col2:
        end_at = st.date_input("end_at")

    return (source, symbol, Timeframe[timeframe], start_at, end_at)


def strategy_selectbox():
    strategy_map = {cls.__name__: cls for cls in strategy_parameter_map.keys()}

    selected = st.selectbox("Strategy", list(strategy_map.keys()))

    return strategy_map[selected]


def strategy_param_settings_form(strategy_class: type):
    parameters = strategy_parameter_map[strategy_class]
    result = {}
    for p in parameters:
        if p.type is int:
            value = st.number_input(p.name, step=1, value=p.default)
        elif p.type is float:
            value = st.number_input(p.name, value=p.default)
        else:
            value = st.text_input(p.name)
        result[p.name] = value
    return result
