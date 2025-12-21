import multiprocessing
import flet as ft

import blueOcean.core.strategies
from blueOcean.presentation.flet import run

if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        # 既に設定されているなら無視
        pass
    ft.app(run, host="0.0.0.0")
