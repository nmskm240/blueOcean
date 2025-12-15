import streamlit as st

from blueOcean.presentation.streamlit import widgets


st.header("Bots")
st.caption("Backtest と Real Trade のエントリーポイント")


col1, col2 = st.columns(2)
with col1:
    if st.button("Run Backtest"):
        widgets.show_backtest_dialog()
with col2:
    if st.button("Run Real Trade"):
        widgets.show_real_trade_dialog()
