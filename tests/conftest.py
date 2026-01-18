import pytest
from peewee import SqliteDatabase

from blueOcean.infra.database.entities import entities, proxy


@pytest.fixture
def database():
    db = SqliteDatabase(":memory:", pragmas={"foreign_keys": 1})
    proxy.initialize(db)
    db.create_tables(entities)
    try:
        yield db
    finally:
        db.drop_tables(entities)
        db.close()
