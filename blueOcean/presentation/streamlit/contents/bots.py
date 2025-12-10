import streamlit as st

from blueOcean.application.services import WorkerService
from blueOcean.presentation.streamlit import widgets

st.title("Bot real running test")

source = st.text_input("source")
symbol = st.text_input("symbol")
strategy_cls = widgets.strategy_selectbox()
strategy_args = widgets.strategy_param_settings_form(strategy_cls)

if st.button("Run"):
    with st.spinner("Testing..."):
        service = WorkerService()
        p = service.spawn_bot("hoge", source, symbol, strategy_cls, strategy_args)
        st.success(f"(PID={p.pid})")
