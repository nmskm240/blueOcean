import multiprocessing
import flet as ft

import blueOcean.core.strategies
from blueOcean.presentation import app

if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        # 既に設定されているなら無視
        pass
    ft.run(app.run, host="0.0.0.0")
