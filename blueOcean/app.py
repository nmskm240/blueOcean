from contextlib import asynccontextmanager

from fastapi import FastAPI
from peewee import SqliteDatabase

from blueOcean.container import get_injector
from blueOcean.database.schemas import AccountSchema, proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = get_injector().get(SqliteDatabase)
    proxy.initialize(database)
    with database.connection_context():
        database.create_tables([AccountSchema], safe=True)
        yield
