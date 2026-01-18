from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from injector import inject
from peewee import SqliteDatabase

from blueOcean.domain.context import Context, ContextId, IContextRepository
from blueOcean.domain.ohlcv import IOhlcvRepository, Ohlcv, Timeframe
from blueOcean.domain.session import ISessionRepository, Session, SessionId
from blueOcean.domain.strategy import (
    IStrategySnapshotRepository,
    StrategySnapshot,
    StrategySnapshotId,
)
from blueOcean.infra.database.entities import (
    ContextEntity,
    SessionContextEntity,
    SessionEntity,
    StrategySnapshotEntity,
)
from blueOcean.infra.database.mapper import to_domain, to_entity
from blueOcean.infra.logging import logger


class OhlcvRepository(IOhlcvRepository):
    @inject
    def __init__(self, base_path: str = "./data"):
        self._base_dir = base_path or "./data"
        self.__con = duckdb.connect()

    def _parse_from_symbol_to_dir(self, symbol: str) -> str:
        return symbol.replace("/", "_")

    def save(self, ohlcv, source, symbol):
        df = Ohlcv.to_dataframe(ohlcv)
        df = df.sort_index()

        df["year_month"] = df.index.strftime("%Y-%m")

        for ym, chunk in df.groupby("year_month"):
            symbol_dir = self._parse_from_symbol_to_dir(symbol)
            out_dir = Path(self._base_dir, source, symbol_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = Path(out_dir, f"{ym}.parquet")
            chunk = chunk.drop(columns=["year_month"])
            chunk["time"] = chunk.index
            chunk = chunk[["time", "open", "high", "low", "close", "volume"]]
            table = pa.Table.from_pandas(chunk, preserve_index=False)

            if filename.exists():
                old = pq.read_table(filename).to_pandas()
                merged = (
                    pd.concat([old, chunk], ignore_index=True)
                    .drop_duplicates(subset=["time"])
                    .sort_values("time")
                )
                table = pa.Table.from_pandas(merged, preserve_index=False)

            logger.info(f"{symbol} {ym} parquet update")
            pq.write_table(table, filename)

    def get_latest_timestamp(self, source, symbol):
        symbol_dir = self._parse_from_symbol_to_dir(symbol)
        path = Path(self._base_dir, source, symbol_dir, "*.parquet")

        sql = f"""
            SELECT max(time) AS latest
            FROM read_parquet('{path}')
        """

        try:
            row = self.__con.execute(sql).fetchone()
            return pd.to_datetime(row[0]).to_pydatetime()
        except:
            return None

    def find(
        self,
        symbol,
        source,
        timeframe=Timeframe.ONE_MINUTE,
        start_date=None,
        end_date=None,
    ):
        symbol_dir = self._parse_from_symbol_to_dir(symbol)
        path = Path(self._base_dir, source, symbol_dir, "*.parquet")

        where = []
        if start_date:
            where.append(f"time >= '{start_date.isoformat()}'")
        if end_date:
            where.append(f"time <= '{end_date.isoformat()}'")

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        sql = f"""
                SELECT
                    time_bucket(INTERVAL {timeframe.to_duck()}, time) AS time,
                    first(open) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    last(close) AS close,
                    sum(volume) AS volume
                FROM read_parquet('{path}')
                {where_sql}
                GROUP BY 1
                ORDER BY time
            """
        df = self.__con.execute(sql).df()
        return Ohlcv.from_dataframe(df)


class SessionRepository(ISessionRepository):
    @inject
    def __init__(self, connection: SqliteDatabase):
        self._con = connection

    def save(self, session: Session) -> Session:
        entity = to_entity(session)
        data = entity.__data__.copy()
        (
            SessionEntity.insert(**data)
            .on_conflict(
                conflict_target=[SessionEntity.id],
                update={
                    SessionEntity.name: data["name"],
                    SessionEntity.updated_at: datetime.now(),
                },
            )
            .execute()
        )
        return session

    def get_all(self) -> list[Session]:
        return [to_domain(entity) for entity in SessionEntity.select()]

    def find_by_id(self, id: SessionId) -> Session:
        entity = SessionEntity.get_by_id(id.value)
        return to_domain(entity)

    def find_by_ids(self, *ids: SessionId) -> list[Session]:
        if not ids:
            return []

        id_values = [id.value for id in ids]
        return [
            to_domain(entity)
            for entity in SessionEntity.select().where(SessionEntity.id.in_(id_values))
        ]


class ContextRepository(IContextRepository):
    @inject
    def __init__(self, connection: SqliteDatabase):
        self._con = connection

    def find_by_id(self, id: ContextId) -> Context:
        entity = ContextEntity.get_by_id(id.value)
        return to_domain(entity)

    def find_by_ids(self, *ids: ContextId) -> list[Context]:
        if not ids:
            return []
        id_values = [id.value for id in ids]
        query = ContextEntity.select().where(ContextEntity.id.in_(id_values))
        return [to_domain(entity) for entity in query]

    def find_by_session_id(self, session_id: SessionId) -> list[Context]:
        query = (
            ContextEntity.select()
            .join(SessionContextEntity)
            .where(SessionContextEntity.session_id == session_id.value)
        )
        return [to_domain(entity) for entity in query]

    def save(self, context: Context) -> Context:
        entity = to_entity(context)
        data = entity.__data__.copy()
        (
            ContextEntity.insert(**data)
            .on_conflict(
                conflict_target=[ContextEntity.id],
                update={
                    ContextEntity.source: data["source"],
                    ContextEntity.symbol: data["symbol"],
                    ContextEntity.timeframe: data["timeframe"],
                    ContextEntity.started_at: data["started_at"],
                    ContextEntity.finished_at: data["finished_at"],
                    ContextEntity.strategy_snapshot: data["strategy_snapshot"],
                    ContextEntity.parameters_json: data["parameters_json"],
                },
            )
            .execute()
        )
        return context


class StrategySnapshotRepository(IStrategySnapshotRepository):
    @inject
    def __init__(self, connection: SqliteDatabase):
        self._con = connection

    def find_by_id(self, id: StrategySnapshotId) -> StrategySnapshot:
        entity = StrategySnapshotEntity.get_by_id(id.value)
        return to_domain(entity)

    def find_by_ids(self, *ids: StrategySnapshotId) -> list[StrategySnapshot]:
        if not ids:
            return []
        id_values = [id.value for id in ids]
        query = StrategySnapshotEntity.select().where(
            StrategySnapshotEntity.id.in_(id_values)
        )
        return [to_domain(entity) for entity in query]

    def save(self, snapshot: StrategySnapshot) -> StrategySnapshot:
        entity = to_entity(snapshot)
        data = entity.__data__.copy()
        (
            StrategySnapshotEntity.insert(**data)
            .on_conflict(
                conflict_target=[StrategySnapshotEntity.id],
                update={
                    StrategySnapshotEntity.name: data["name"],
                },
            )
            .execute()
        )
        return snapshot
