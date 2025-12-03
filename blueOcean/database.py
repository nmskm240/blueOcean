from datetime import datetime
from injector import Module, provider, singleton
from peewee import (
    SqliteDatabase,
    Model,
    SmallIntegerField,
    IntegerField,
    CharField,
    DateTimeField,
)
from cuid2 import Cuid, DEFAULT_LENGTH

db = SqliteDatabase("data/blueOcean.sqlite3")


# class DatabaseModule(Module):
#     @singleton
#     @provider
#     def provide_db(self):
#         return db


class BaseEntity(Model):
    class Meta:
        database = db


class ProcessEntity(BaseEntity):
    id = CharField(
        max_length=DEFAULT_LENGTH, primary_key=True, default=lambda: Cuid().generate()
    )
    pid = IntegerField(null=False)
    status = SmallIntegerField(null=False, default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "processes"


db.create_tables([ProcessEntity])
