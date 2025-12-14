from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import quantstats as qs
from injector import inject

from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.infra.database.repositories import BotRepository


class WorkerService:
    @inject
    def __init__(self, bot_repository: BotRepository):
        self.bot_workers = {}
        self.bot_repository = bot_repository

    def spawn_real_trade(self, bot_id: str, config: BotConfig):
        from blueOcean.application.workers import RealTradeWorker

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

    def spawn_backtest(self, config: BacktestConfig):
        from blueOcean.application.workers import BacktestWorker

        worker = BacktestWorker(config)
        worker.start()
        return worker


class ReportService:
    def __init__(self, run_type: str):
        now = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        run_dir = Path("./out") / f"{run_type}_{now}"
        run_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir: Path = run_dir
        self.metrics_path: Path = run_dir / "metrics.csv"
        self.report_path: Path = run_dir / "quantstats_report.html"

    def save_run_metadata(self, config: BacktestConfig | BotConfig, mode: str) -> None:
        data: dict[str, object] = {
            "mode": mode,
            "created_at": datetime.now(tz=UTC).isoformat(),
            "strategy": getattr(
                config.strategy_cls, "__name__", str(config.strategy_cls)
            ),
            "params": config.strategy_args,
        }
        data.update(config.to_metadata())

        meta_path = self.run_dir / "meta.json"
        meta_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def create_report(
        self,
        metrics_path: Path | None = None,
        output_path: Path | None = None,
    ) -> None:
        # デフォルトは自身が管理するパスを使用する
        metrics_path = Path(metrics_path or self.metrics_path)
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

        output_path = Path(output_path or self.report_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        qs.reports.html(returns, output=str(output_path))
