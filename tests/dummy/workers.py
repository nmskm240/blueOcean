class DummyWorker:
    def __init__(self, pid: int = 999):
        self.pid = pid
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class DummyLiveWorker:
    def __init__(self, bot_id, context):
        self.bot_id = bot_id
        self.context = context


class DummyBacktestWorker:
    def __init__(self, bot_id, context):
        self.bot_id = bot_id
        self.context = context


class DummyRecoverWorker:
    def __init__(self, pid):
        self.pid = pid
        self.stopped = False

    def start(self):
        raise RuntimeError("RecoverWorker cannot be started in tests")

    def stop(self):
        self.stopped = True
