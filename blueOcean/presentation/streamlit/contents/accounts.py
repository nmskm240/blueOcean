import streamlit as st

from blueOcean.application import usecases
from blueOcean.presentation.streamlit import widgets


st.title("Accounts")

(
    submitted,
    exchange,
    api_key,
    api_secret,
    is_sandbox,
    label,
) = widgets.api_credential_form()

if submitted:
    try:
        account_id = usecases.register_api_credential(
            exchange=exchange,
            api_key=api_key,
            api_secret=api_secret,
            is_sandbox=is_sandbox,
            label=label,
        )
        st.success(f"Registered account (id={account_id})")
    except Exception as e:
        st.error(f"Failed to register account: {e}")

