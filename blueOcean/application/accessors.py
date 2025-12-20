from __future__ import annotations

from abc import ABCMeta, abstractmethod
from pathlib import Path

from blueOcean.domain.bot import BotId


class IBotRuntimeDirectoryAccessor(metaclass=ABCMeta):
    @abstractmethod
    def generate_directory(self, bot_id: BotId) -> Path:
        raise NotImplementedError()
