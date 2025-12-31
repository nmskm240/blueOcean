from datetime import datetime
import json
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from injector import inject
from peewee import SqliteDatabase

from blueOcean.domain.account import Account, AccountId
from blueOcean.domain.bot import Bot, BotId, IBotRepository
from blueOcean.domain.playground import (
    PlaygroundRun,
    PlaygroundRunId,
    PlaygroundRunStatus,
    IPlaygroundRunRepository,
)
from blueOcean.domain.ohlcv import IOhlcvRepository, Ohlcv, Timeframe
from blueOcean.infra.database.entities import (
    AccountEntity,
    BotContextEntity,
    BotEntity,
    PlaygroundRunEntity,
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


class AccountRepository:
    @inject
    def __init__(self, connection: SqliteDatabase):
        self.con = connection

    def find_by_id(self, account_id: AccountId) -> Account:
        account_entity = AccountEntity.get_by_id(account_id.value)
        return to_domain(account_entity)

    def get_all(self) -> list[Account]:
        return [to_domain(entity) for entity in AccountEntity.select()]

    def save(self, account: Account) -> Account:
        entity = to_entity(account)

        data = entity.__data__.copy()
        (
            AccountEntity.insert(**data)
            .on_conflict(
                conflict_target=[AccountEntity.id],
                update={
                    AccountEntity.api_key: data["api_key"],
                    AccountEntity.api_secret: data["api_secret"],
                    AccountEntity.exchange_name: data["exchange_name"],
                    AccountEntity.is_sandbox: data["is_sandbox"],
                    AccountEntity.label: data["label"],
                    AccountEntity.updated_at: datetime.now(),
                },
            )
            .execute()
        )
        return account

    def delete_by_id(self, account_id: AccountId) -> None:
        AccountEntity.delete().where(AccountEntity.id == account_id.value).execute()


class BotRepository(IBotRepository):
    @inject
    def __init__(self, connection: SqliteDatabase):
        self._con = connection

    def save(self, bot: Bot) -> Bot:
        bot_entity, context_entity = to_entity(bot)

        bot_data = bot_entity.__data__.copy()
        (
            BotEntity.insert(**bot_data)
            .on_conflict(
                conflict_target=[BotEntity.id],
                update={
                    BotEntity.status: bot_data["status"],
                    BotEntity.pid: bot_data["pid"],
                    BotEntity.label: bot_data["label"],
                    BotEntity.started_at: bot_data["started_at"],
                    BotEntity.finished_at: bot_data["finished_at"],
                    BotEntity.updated_at: datetime.now(),
                },
            )
            .execute()
        )
        context_data = context_entity.__data__.copy()
        (
            BotContextEntity.insert(**context_data)
            .on_conflict_ignore()
            .execute()
        )
        return bot

    def get_all(self) -> list[Bot]:
        bots: list[Bot] = []
        query = BotEntity.select(BotEntity, BotContextEntity).join(BotContextEntity)

        for bot_entity in query:
            context_entity = bot_entity.botcontextentity
            bots.append(to_domain(bot_entity, context_entity))
        return bots


class PlaygroundRunRepository(IPlaygroundRunRepository):
    @inject
    def __init__(self, connection: SqliteDatabase):
        self._con = connection

    def save(self, run: PlaygroundRun) -> PlaygroundRun:
        data = {
            "id": run.id.value,
            "notebook_path": run.notebook_path,
            "parameters_json": json.dumps(run.parameters, ensure_ascii=False),
            "markdown": run.markdown,
            "status": int(run.status),
            "executed_at": run.executed_at,
            "output_path": run.output_path,
            "error_message": run.error_message,
            "created_at": datetime.now(),
        }
        (
            PlaygroundRunEntity.insert(**data)
            .on_conflict(
                conflict_target=[PlaygroundRunEntity.id],
                update={
                    PlaygroundRunEntity.notebook_path: data["notebook_path"],
                    PlaygroundRunEntity.parameters_json: data["parameters_json"],
                    PlaygroundRunEntity.markdown: data["markdown"],
                    PlaygroundRunEntity.status: data["status"],
                    PlaygroundRunEntity.executed_at: data["executed_at"],
                    PlaygroundRunEntity.output_path: data["output_path"],
                    PlaygroundRunEntity.error_message: data["error_message"],
                    PlaygroundRunEntity.created_at: data["created_at"],
                },
            )
            .execute()
        )
        return run

    def find_by_id(self, run_id: PlaygroundRunId) -> PlaygroundRun:
        entity = PlaygroundRunEntity.get_by_id(run_id.value)
        return self._to_domain(entity)

    def get_all(self) -> list[PlaygroundRun]:
        return [self._to_domain(entity) for entity in PlaygroundRunEntity.select()]

    @staticmethod
    def _to_domain(entity: PlaygroundRunEntity) -> PlaygroundRun:
        return PlaygroundRun(
            id=PlaygroundRunId(entity.id),
            notebook_path=entity.notebook_path,
            parameters=json.loads(entity.parameters_json),
            markdown=entity.markdown,
            status=PlaygroundRunStatus(entity.status),
            executed_at=entity.executed_at,
            output_path=entity.output_path,
            error_message=entity.error_message,
        )

    def find_by_id(self, id: BotId) -> Bot:
        query = (
            BotEntity
            .select(BotEntity, BotContextEntity)
            .join(BotContextEntity)
            .where(BotEntity.id == id.value)
        )
        bot_entity = query.get()
        context_entity = bot_entity.botcontextentity
        return to_domain(bot_entity, context_entity)
    
    def find_by_ids(self, *ids: BotId) -> list[Bot]:
        if not ids:
            return []

        id_values = [id.value for id in ids]
        query = (
            BotEntity
            .select(BotEntity, BotContextEntity)
            .join(BotContextEntity)
            .where(BotEntity.id.in_(id_values))
        )
        bots: list[Bot] = []
        for bot_entity in query:
            context_entity = bot_entity.botcontextentity
            bots.append(to_domain(bot_entity, context_entity))
        return bots
