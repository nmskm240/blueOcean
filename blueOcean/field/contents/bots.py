from time import sleep
import streamlit as st

from blueOcean.logging import logger
from blueOcean.process import _ProcessRepository, ProcessManager

def hoge(i: int):
    while True:
        logger.info(i)
        i += 1
        sleep(1)


pm = ProcessManager(_ProcessRepository())

if st.button("Start"):
    pid = pm.spawn(hoge, 0)
    st.write(pid)
    sleep(10)
    pm.terminate(pid)
