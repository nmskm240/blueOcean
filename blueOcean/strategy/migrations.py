from peewee import SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from blueOcean.strategy.schemas import StrategySchema


def migrate_strategy_schema(database: SqliteDatabase) -> None:
    """Apply additive migrations required by the strategy module."""
    columns = {column.name for column in database.get_columns("strategies")}
    if "definition_key" not in columns:
        migrator = SqliteMigrator(database)
        migrate(
            migrator.add_column(
                "strategies",
                "definition_key",
                StrategySchema.definition_key,
            )
        )
