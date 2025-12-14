import ccxt
import pandas as pd
import streamlit as st

from blueOcean.application.decorators import strategy_registry
from blueOcean.domain.account import Account
from blueOcean.domain.ohlcv import Timeframe


def ohlcv_fetch_form():
    with st.form("data_fetch"):
        st.header("Data fetch")
        source = st.selectbox("source", ccxt.exchanges)
        symbol = st.text_input("symbol")
        submitted = st.form_submit_button("Fetch")

    return submitted, source, symbol


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


def api_credential_form(
    *,
    form_key: str,
    account: Account | None = None,
    title: str = "API Credential",
    submit_label: str = "Save",
):
    exchanges = ccxt.exchanges
    if account is not None:
        try:
            initial_index = exchanges.index(account.credential.exchange)
        except ValueError:
            initial_index = 0
        api_key_default = account.credential.key
        api_secret_default = account.credential.secret
        is_sandbox_default = account.credential.is_sandbox
        label_default = account.label
    else:
        initial_index = 0
        api_key_default = ""
        api_secret_default = ""
        is_sandbox_default = True
        label_default = ""

    with st.form(form_key):
        st.header(title)
        exchange = st.selectbox("exchange", exchanges, index=initial_index)
        api_key = st.text_input("API key", value=api_key_default)
        api_secret = st.text_input(
            "API secret", type="password", value=api_secret_default
        )
        is_sandbox = st.checkbox("Sandbox mode", value=is_sandbox_default)
        label = st.text_input("label", value=label_default)
        submitted = st.form_submit_button(submit_label)

    return submitted, exchange, api_key, api_secret, is_sandbox, label


def account_table(records):
    if not records:
        return
    df = pd.DataFrame.from_records(records)
    st.table(df[["Label", "Exchange", "Sandbox"]])
