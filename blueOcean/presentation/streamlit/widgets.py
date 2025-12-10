import ccxt
import streamlit as st

from blueOcean.application import usecase
from blueOcean.application.decorators import strategy_registry
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.infra.database.repositories import OhlcvRepository
from blueOcean.infra.fetchers import CcxtOhlcvFetcher


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
    strategy_map = {
        page_data.cls.__name__: page_data.cls for page_data in strategy_registry
    }

    selected = st.selectbox("Strategy", list(strategy_map.keys()))

    return strategy_map[selected]


def strategy_param_settings_form(strategy_class: type):
    strategy_map = {page_data.cls: page_data for page_data in strategy_registry}
    parameters = strategy_map[strategy_class].params
    result = {}
    for p in parameters:
        name = p[0]
        default_value = p[1]
        if type(default_value) is int:
            value = st.number_input(name, step=1, value=default_value)
        elif type(default_value) is float:
            value = st.number_input(name, value=default_value)
        else:
            value = st.text_input(name, value=default_value)
        result[name] = value
    return result
