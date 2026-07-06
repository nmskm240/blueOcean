import pytest

from blueOcean.models import Account, AccountId, Mt5Connection


def test_account_id_create_generates_distinct_cuid_strings():
    first = AccountId.create()
    second = AccountId.create()

    assert isinstance(first.value, str)
    assert first.value
    assert first != second


@pytest.mark.parametrize(
    "path",
    [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"\\trade-host\mt5\terminal64.exe",
        "/opt/metatrader/terminal64",
    ],
)
def test_mt5_connection_accepts_absolute_local_paths(path):
    connection = Mt5Connection(
        path=path,
        server="Broker-Demo",
        login=12345678,
        encrypted_password=b"encrypted-secret",
    )

    assert connection.path == path


@pytest.mark.parametrize(
    ("path", "server", "login", "encrypted_password", "message"),
    [
        ("", "Broker-Demo", 123, b"secret", "ローカルパスは必須"),
        ("terminal64.exe", "Broker-Demo", 123, b"secret", "絶対ローカルパス"),
        ("https://host/terminal64.exe", "Broker-Demo", 123, b"secret", "絶対ローカルパス"),
        (r"C:\MT5\terminal64.exe", "", 123, b"secret", "サーバー名は必須"),
        (r"C:\MT5\terminal64.exe", "Broker-Demo", 0, b"secret", "正の整数"),
        (r"C:\MT5\terminal64.exe", "Broker-Demo", -1, b"secret", "正の整数"),
        (r"C:\MT5\terminal64.exe", "Broker-Demo", None, b"secret", "正の整数"),
        (r"C:\MT5\terminal64.exe", "Broker-Demo", True, b"secret", "正の整数"),
        (r"C:\MT5\terminal64.exe", "Broker-Demo", 123, b"", "暗号化済み"),
        (r"C:\MT5\terminal64.exe", "Broker-Demo", 123, None, "暗号化済み"),
    ],
)
def test_mt5_connection_rejects_invalid_values(path, server, login, encrypted_password, message):
    with pytest.raises(ValueError, match=message):
        Mt5Connection(path, server, login, encrypted_password)


def test_account_generates_id_and_exposes_connection_values():
    connection = Mt5Connection(
        path=r"C:\MT5\terminal64.exe",
        server="Broker-Demo",
        login=12345678,
        encrypted_password=b"encrypted-secret",
    )

    account = Account(id=None, name="Demo", connection=connection, portable=True)

    assert isinstance(account.id, AccountId)
    assert account.name == "Demo"
    assert account.connection is connection
    assert account.has_password is True
    assert account.portable is True


def test_account_preserves_given_id():
    account_id = AccountId("account-1")
    connection = Mt5Connection(
        path=r"C:\MT5\terminal64.exe",
        server="Broker-Live",
        login=98765432,
        encrypted_password=b"encrypted-secret",
    )

    account = Account("Live", connection, False, id=account_id)

    assert account.id is account_id
