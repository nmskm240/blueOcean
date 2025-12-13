import streamlit as st

import blueOcean.presentation.streamlit.widgets as widgets
from blueOcean.application import usecases


submitted, source, symbol = widgets.ohlcv_fetch_form()

if submitted:
    with st.spinner("Fetching..."):
        usecases.fetch_ohlcv(source, symbol)
