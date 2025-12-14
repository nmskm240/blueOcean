import ccxt
import pandas as pd
import streamlit as st

from blueOcean.application import usecases
from blueOcean.domain.account import Account
from blueOcean.presentation.streamlit import widgets


st.title("Accounts")

if "account_created" not in st.session_state:
    st.session_state["account_created"] = False

if "account_updated" not in st.session_state:
    st.session_state["account_updated"] = False

if "account_deleted" not in st.session_state:
    st.session_state["account_deleted"] = False

if "editing_account_id" not in st.session_state:
    st.session_state["editing_account_id"] = None

if st.session_state["account_created"]:
    st.success("API credential registered")
    st.session_state["account_created"] = False

if st.session_state["account_updated"]:
    st.success("API credential updated")
    st.session_state["account_updated"] = False

if st.session_state["account_deleted"]:
    st.success("API credential deleted")
    st.session_state["account_deleted"] = False


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
                usecases.register_api_credential(
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


def show_edit_dialog(account_id: str, account: Account):
    dialog = st.dialog("Edit API credential")

    @dialog
    def _dialog():
        exchanges = ccxt.exchanges
        try:
            initial_index = exchanges.index(account.credential.exchange)
        except ValueError:
            initial_index = 0

        with st.form(f"edit_api_credential_{account_id}"):
            st.header("Edit API Credential")
            exchange = st.selectbox("exchange", exchanges, index=initial_index)
            api_key = st.text_input("API key", value=account.credential.key)
            api_secret = st.text_input(
                "API secret", type="password", value=account.credential.secret
            )
            is_sandbox = st.checkbox(
                "Sandbox mode", value=account.credential.is_sandbox
            )
            label = st.text_input("label", value=account.label)
            submitted = st.form_submit_button("Update")

        if submitted:
            try:
                usecases.update_api_credential(
                    account_id=account_id,
                    exchange=exchange,
                    api_key=api_key,
                    api_secret=api_secret,
                    is_sandbox=is_sandbox,
                    label=label,
                )
                st.session_state["account_updated"] = True
                st.session_state["editing_account_id"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update account: {e}")

    _dialog()


if st.button("Add API credential"):
    show_register_dialog()


raw_accounts = usecases.list_api_credentials()

st.subheader("Registered APIs")
if not raw_accounts:
    st.info("No API credentials registered yet.")
else:
    records = []
    for account_id, account in raw_accounts:
        records.append(
            {
                "id": account_id,
                "Label": account.label,
                "Exchange": account.credential.exchange,
                "Sandbox": "sandbox" if account.credential.is_sandbox else "live",
            }
        )

    options = {f'{row["Label"]} / {row["Exchange"]} ({row["Sandbox"]})': row["id"] for row in records}

    selected_label = st.selectbox(
        "Select account", list(options.keys()), key="account_select"
    )
    selected_id = options[selected_label]
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("Edit selected"):
            st.session_state["editing_account_id"] = selected_id
    with col2:
        if st.button("Delete selected"):
            usecases.delete_api_credential(selected_id)
            st.session_state["account_deleted"] = True
            st.session_state["editing_account_id"] = None
            st.rerun()

    df = pd.DataFrame.from_records(records)
    st.table(df[["Label", "Exchange", "Sandbox"]])

editing_id = st.session_state.get("editing_account_id")
if editing_id is not None and raw_accounts:
    for account_id, account in raw_accounts:
        if account_id == editing_id:
            show_edit_dialog(account_id, account)
            break
