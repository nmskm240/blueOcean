from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from injector import inject
from peewee import SqliteDatabase

from blueOcean.domain.account import Account
from blueOcean.domain.ohlcv import IOhlcvRepository, Ohlcv, Timeframe
from blueOcean.infra.database.entities import AccountEntity, BotEntity
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


class AccountRepository:
    @inject
    def __init__(self, connection: SqliteDatabase):
        self.con = connection

    def get(self, id: str) -> Account:
        account_entity = AccountEntity.get(AccountEntity.id == id)
        return account_entity.to_domain()

    def list(self) -> list[Account]:
        return [entity.to_domain() for entity in AccountEntity.select()]

    def create_account(self, account: Account) -> str:
        entity = AccountEntity.from_domain(account)
        return entity.id


class BotRepository:
    STATUS_STOPPED = 0
    STATUS_RUNNING = 1

    @inject
    def __init__(self, connection: SqliteDatabase):
        self.con = connection

    def save(self, bot_id: str, pid: int, status: int) -> None:
        now = datetime.now()
        (
            BotEntity.update(
                pid=pid,
                status=status,
                updated_at=now,
            )
            .where(BotEntity.id == bot_id)
            .execute()
        )

    def update(
        self,
        bot_id: str,
        *,
        pid: int | None = None,
        status: int | None = None,
    ) -> None:
        values: dict[str, object] = {"updated_at": datetime.now()}
        if pid is not None:
            values["pid"] = pid
        if status is not None:
            values["status"] = status

        (BotEntity.update(**values).where(BotEntity.id == bot_id).execute())
