from __future__ import annotations

from pathlib import Path


from blueOcean.application.accessors import IBotRuntimeDirectoryAccessor
from blueOcean.domain.bot import BotId


class LocalBotRuntimeDirectoryAccessor(IBotRuntimeDirectoryAccessor):
    def generate_directory(self, bot_id: BotId) -> Path:
        # TODO: ベースディレクトリは設定で変更可能にする
        run_dir = Path("./out") / bot_id.value
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
