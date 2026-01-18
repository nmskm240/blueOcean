import pytest
from peewee import SqliteDatabase

from blueOcean.infra.database.entities import (
    ContextEntity,
    SessionContextEntity,
    SessionEntity,
    StrategySnapshotEntity,
    proxy,
)


@pytest.fixture
def database():
    db = SqliteDatabase(":memory:", pragmas={"foreign_keys": 1})
    proxy.initialize(db)
    db.create_tables(
        [
            SessionEntity,
            StrategySnapshotEntity,
            ContextEntity,
            SessionContextEntity,
        ]
    )
    try:
        yield db
    finally:
        db.drop_tables(
            [
                SessionEntity,
                StrategySnapshotEntity,
                ContextEntity,
                SessionContextEntity,
            ]
        )
        db.close()
