from __future__ import annotations
from datetime import datetime, timezone

from peewee import (
    BlobField,
    BooleanField,
    CharField,
    DatabaseProxy,
    DateTimeField,
    IntegerField,
    Model,
)

from blueOcean.models import Account, AccountId, Mt5Connection

proxy = DatabaseProxy()


class AccountSchema(Model):
    id = CharField(primary_key=True)
    name = CharField(unique=True)
    path = CharField()
    login = IntegerField(null=True)
    password_encrypted = BlobField(null=True)
    server = CharField()
    portable = BooleanField(default=False)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    class Meta:
        table_name = "accounts"
        database = proxy

    def to_entity(self) -> Account:
        return Account(
            id=AccountId(self.id),
            name=self.name,
            connection=Mt5Connection(
                path=self.path,
                server=self.server,
                login=self.login,
                encrypted_password=self.password_encrypted,
            ),
            portable=bool(self.portable),
        )
