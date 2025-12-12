import multiprocessing

from blueOcean.presentation import streamlit

if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        # 既に設定されているなら無視
        pass
    streamlit.setup()
