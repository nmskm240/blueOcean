from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import quantstats as qs
from injector import inject

from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.application.workers import BacktestWorker, RealTradeWorker
from blueOcean.infra.database.repositories import BotRepository


class WorkerService:
    @inject
    def __init__(self, bot_repository: BotRepository):
        self.bot_workers: dict[str, RealTradeWorker] = {}
        self.bot_repository = bot_repository

    def spawn_real_trade(self, bot_id: str, config: BotConfig) -> RealTradeWorker:
        worker = RealTradeWorker(config)

        worker.start()
        self.bot_workers[bot_id] = worker

        self.bot_repository.save(
            bot_id=bot_id,
            pid=worker.pid,
            status=BotRepository.STATUS_RUNNING,
        )

        return worker

    def stop_real_trade(self, bot_id: str):
        worker = self.bot_workers.get(bot_id)
        if not worker:
            return

        worker.terminate()
        self.bot_repository.update(
            bot_id=bot_id,
            status=BotRepository.STATUS_STOPPED,
        )
        del self.bot_workers[bot_id]

    def spawn_backtest(self, config: BacktestConfig) -> BacktestWorker:
        worker = BacktestWorker(config)
        worker.start()
        return worker


class ReportService:
    def create_bot_run_paths(self, symbol: str) -> tuple[Path, Path, Path]:
        now = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        run_dir = Path("./out") / "bot" / f"{symbol}_{now}"
        run_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = run_dir / "metrics.csv"
        report_path = run_dir / "quantstats_report.html"
        return run_dir, metrics_path, report_path

    def create_backtest_run_paths(self, symbol: str) -> tuple[Path, Path, Path]:
        now = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        run_dir = Path("./out") / "backtest" / f"{symbol}_{now}"
        run_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = run_dir / "metrics.csv"
        report_path = run_dir / "quantstats_report.html"
        return run_dir, metrics_path, report_path

    def create_report_from_metrics(self, metrics_path: Path, output_path: Path) -> None:
        metrics_path = Path(metrics_path)
        if not metrics_path.exists():
            return

        df = pd.read_csv(metrics_path)
        if df.empty:
            return

        required_cols = {"timestamp", "analyzer", "value"}
        if not required_cols.issubset(df.columns):
            return

        df = df[df["analyzer"] == "timereturn"].copy()
        if df.empty:
            return

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        returns = pd.Series(df["value"].values, index=df["timestamp"])

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        qs.reports.html(returns, output=str(output_path))
