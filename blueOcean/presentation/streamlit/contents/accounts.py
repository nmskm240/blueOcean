import streamlit as st

from blueOcean.application import usecases
from blueOcean.presentation.streamlit import widgets
from blueOcean.domain.account import Account


st.title("Accounts")

if "account_created" not in st.session_state:
    st.session_state["account_created"] = False

if st.session_state["account_created"]:
    st.success("API credential registered")
    st.session_state["account_created"] = False


def show_register_dialog():
    dialog = st.dialog("Add API credential")

    @dialog
    def _dialog():
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
                st.session_state["account_created"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to register account: {e}")

    _dialog()


if st.button("Add API credential"):
    show_register_dialog()


accounts: list[Account] = usecases.list_api_credentials()

st.subheader("Registered APIs")
if not accounts:
    st.info("No API credentials registered yet.")
else:
    for account in accounts:
        with st.container(border=True):
            st.write(f"Label: {account.label}")
            st.write(f"Exchange: {account.credential.exchange}")
            st.write(f"Sandbox: {account.credential.is_sandbox}")
