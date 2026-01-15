import signal
from abc import ABCMeta, abstractmethod
from multiprocessing import Process
from pathlib import Path

import backtrader as bt
import psutil
from injector import Injector

from blueOcean.application.di import BacktestRuntimeModule
from blueOcean.domain.bot import BacktestContext, BotId, IBotWorker


class BotProcessWorker(Process, IBotWorker, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self._run_directory: Path | None = None

    def launch(self):
        self.start()

    def run(self):
        signal.signal(signal.SIGTERM, self._on_handle_sigterm)

        self._run()

    @abstractmethod
    def _run(self) -> None:
        raise NotImplementedError()

    def _on_handle_sigterm(self, signum, frame):
        self._on_sigterm()
        raise SystemExit()

    def _on_sigterm(self) -> None:
        pass


class BacktestWorker(BotProcessWorker):
    def __init__(self, id: BotId, context: BacktestContext):
        super().__init__()
        self._id = id
        self._context = context

    def _run(self):
        container = Injector([BacktestRuntimeModule(self._id, self._context)])
        self._run_directory = container.get(Path)

        cerebro = container.get(bt.Cerebro)
        cerebro.run(runonce=False)

    def shutdown(self):
        super().terminate()


class RecoverWorker(IBotWorker):
    """起動済みプロセスへの再接続用Worker"""

    def __init__(self, pid):
        self._process = psutil.Process(pid)

    def launch(self):
        raise RuntimeError(f"{self.__class__.__name__} cannot be started")

    def shutdown(self):
        self._process.terminate()
