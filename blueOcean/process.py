from __future__ import annotations
from datetime import datetime
from enum import IntEnum
from multiprocessing import Process
from injector import inject
from peewee import Database
import psutil

from blueOcean.database import ProcessEntity


class ProcessStatus(IntEnum):
    NONE = 0
    STARTED = 1
    KILLED = 2


PROCESS_TAG = "blueOcean_runtime"


class ProcessManager:
    # @inject
    def __init__(self, repository: _ProcessRepository):
        self._repository = repository

    def spawn(self, target, *args) -> int:
        process = Process(target=_child_wrapper, args=(PROCESS_TAG, target, args))
        process.start()
        pid = process.pid

        entity = ProcessEntity(pid=pid, status=ProcessStatus.STARTED.value)
        self._repository.save(entity, force_insert=True)
        return pid

    def is_alive(self, pid: int):
        try:
            p = psutil.Process(pid)
            if not p.is_running():
                return False

            return any(PROCESS_TAG in arg for arg in p.cmdline())
        except psutil.NoSuchProcess:
            return False

    def terminate(self, pid: int):
        entity = self._repository.find_active_by_pid(pid)
        if not entity:
            return False
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=5)
        except psutil.TimeoutExpired:
            p.kill()
        except psutil.NoSuchProcess:
            pass

        entity.status = ProcessStatus.KILLED
        entity.save()
        return True


def _child_wrapper(name: str, target, args):
    import sys

    sys.argv.insert(0, name)
    target(*args)


class _ProcessRepository:
    # @inject
    # def __init__(self, db: Database):
    #     self._db = db

    def save(self, entity: ProcessEntity, force_insert=False):
        entity.updated_at = datetime.now()
        entity.save(force_insert=force_insert)

    def find_by_id(self, id: str) -> ProcessEntity:
        return ProcessEntity.get_or_none(ProcessEntity.id == id)

    def find_by_status(self, status: ProcessStatus) -> list[ProcessEntity]:
        return list(ProcessEntity.select().where(ProcessEntity.status == status))

    def find_active_by_pid(self, pid: int) -> ProcessEntity | None:
        return (
            ProcessEntity.select()
            .where(
                (ProcessEntity.pid == pid)
                & (ProcessEntity.status == ProcessStatus.STARTED)
            )
            .order_by(ProcessEntity.created_at.desc())
            .first()
        )
