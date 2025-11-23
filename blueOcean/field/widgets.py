import streamlit as st
import ccxt
from blueOcean.ohlcv import CcxtOhlcvFetcher, OhlcvRepository


def ohlcv_fetch_form():
    with st.form("data_fetch"):
        st.header("Data fetch")
        source = st.selectbox("source", ccxt.exchanges)
        symbol = st.text_input("symbol")
        submitted = st.form_submit_button("Fetch")

    if not submitted:
        return

    with st.spinner("Fetching..."):
        # TODO: DI化してfetcher.fetchだけにしたほうが綺麗かも
        repository = OhlcvRepository("../data")
        latest_at = repository.get_latest_timestamp(source, symbol)
        fetcher = CcxtOhlcvFetcher(source)
        for batch in fetcher.fetch_ohlcv(symbol, latest_at):
            repository.save(batch, source, symbol)
