from cryptography.fernet import Fernet
from pydantic import SecretStr

from blueOcean.container import MT5Module, SecurityModule
from blueOcean.settings import Settings


def make_settings(secret: str) -> Settings:
    return Settings(
        BLUEOCEAN_SECRET_KEY=SecretStr(secret),
        BLUEOCEAN_SQLITE_PATH="data/test.db",
    )


def test_password_cipher_uses_the_configured_fernet_key():
    key = Fernet.generate_key()
    cipher = SecurityModule().password_cipher(make_settings(key.decode()))

    token = Fernet(key).encrypt(b"mt5-password")

    assert cipher.decrypt(token) == b"mt5-password"


def test_password_cipher_rejects_a_non_fernet_secret():
    module = SecurityModule()

    try:
        module.password_cipher(make_settings("not-a-fernet-key"))
    except ValueError as exc:
        assert "Fernet key" in str(exc)
    else:
        raise AssertionError("A non-Fernet secret must be rejected")


def test_worker_manager_uses_configured_startup_timeout():
    settings = Settings(
        BLUEOCEAN_SECRET_KEY=SecretStr(Fernet.generate_key().decode()),
        BLUEOCEAN_SQLITE_PATH="data/test.db",
        BLUEOCEAN_MT5_STARTUP_TIMEOUT_SECONDS=12.5,
    )

    manager = MT5Module().mt5_worker_manager(settings)

    assert manager._startup_timeout == 12.5
