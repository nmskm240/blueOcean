from peewee import SqliteDatabase
from playhouse.migrate import SqliteMigrator, migrate

from blueOcean.strategy.schemas import StrategyRunSchema, StrategySchema


def migrate_strategy_schema(database: SqliteDatabase) -> None:
    """Apply additive migrations required by the strategy module."""
    migrator = SqliteMigrator(database)
    strategy_columns = {column.name for column in database.get_columns("strategies")}
    strategy_fields = {
        "definition_key": StrategySchema.definition_key,
        "data_source": StrategySchema.data_source,
        "execution_backend": StrategySchema.execution_backend,
        "history_period": StrategySchema.history_period,
        "initial_cash": StrategySchema.initial_cash,
        "commission": StrategySchema.commission,
    }
    operations = [
        migrator.add_column("strategies", name, field)
        for name, field in strategy_fields.items()
        if name not in strategy_columns
    ]
    run_columns = {column.name for column in database.get_columns("strategy_runs")}
    if "result_json" not in run_columns:
        operations.append(
            migrator.add_column(
                "strategy_runs", "result_json", StrategyRunSchema.result_json
            )
        )
    account_column = next(
        column for column in database.get_columns("strategies") if column.name == "account_id"
    )
    if not account_column.null:
        operations.append(migrator.drop_not_null("strategies", "account_id"))
    if operations:
        migrate(*operations)
