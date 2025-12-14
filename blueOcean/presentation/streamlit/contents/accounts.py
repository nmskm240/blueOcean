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
        ) = widgets.api_credential_form(
            form_key="api_credential",
            account=None,
            title="API Credential",
            submit_label="Save",
        )

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
        (
            submitted,
            exchange,
            api_key,
            api_secret,
            is_sandbox,
            label,
        ) = widgets.api_credential_form(
            form_key=f"edit_api_credential_{account_id}",
            account=account,
            title="Edit API Credential",
            submit_label="Update",
        )
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
    for account in raw_accounts:
        account_id = account.id.value or ""
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
            for account in raw_accounts:
                if account.id.value == selected_id:
                    show_edit_dialog(selected_id, account)
                    break
    with col2:
        if st.button("Delete selected"):
            usecases.delete_api_credential(selected_id)
            st.session_state["account_deleted"] = True
            st.rerun()

    widgets.account_table(records)
