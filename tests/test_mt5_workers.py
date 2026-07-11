from queue import Queue

from blueOcean.metatrader.workers import MT5WorkerManager


class FakeEvent:
    def __init__(self):
        self.was_set = False

    def set(self):
        self.was_set = True


class FakeProcess:
    next_pid = 1000

    def __init__(self, *, target, args, name, daemon):
        self.args = args
        self.name = name
        self.pid = None
        self.exitcode = None
        self.alive = False

    def start(self):
        self.pid = FakeProcess.next_pid
        FakeProcess.next_pid += 1
        self.alive = True

    def is_alive(self):
        return self.alive

    def join(self, timeout):
        if self.args[1].was_set:
            self.alive = False
            self.exitcode = 0

    def terminate(self):
        self.alive = False
        self.exitcode = -15


class FakeContext:
    def Event(self):
        return FakeEvent()

    def Queue(self):
        return Queue()

    def Process(self, **kwargs):
        return FakeProcess(**kwargs)


def test_manager_starts_only_one_worker_per_account_and_stops_it():
    terminal_pid_sets = iter([set(), {42}])
    terminated = []
    manager = MT5WorkerManager(
        context=FakeContext(),
        terminal_pids=lambda path: next(terminal_pid_sets),
        terminate_terminals=terminated.append,
        startup_timeout=None,
    )
    first = manager.start("account-1", {"path": r"C:\MT5\terminal64.exe"})
    second = manager.start("account-1", {"path": r"C:\MT5\terminal64.exe"})

    assert first.state == "starting"
    assert second.pid == first.pid
    assert manager.stop("account-1").state == "stopped"
    assert terminated == [{42}]
    assert manager.get_status("account-1").state == "stopped"


def test_manager_reports_worker_messages():
    manager = MT5WorkerManager(
        context=FakeContext(), terminal_pids=lambda path: set(), startup_timeout=None
    )
    manager.start("ready", {})
    manager._workers["ready"].status_queue.put(("running", None))
    manager.start("broken", {})
    manager._workers["broken"].status_queue.put(("error", "login failed"))

    assert manager.get_status("ready").state == "running"
    broken = manager.get_status("broken")
    assert broken.state == "error"
    assert broken.error == "login failed"


def test_stop_does_not_terminate_a_terminal_that_was_already_running():
    terminated = []
    manager = MT5WorkerManager(
        context=FakeContext(),
        terminal_pids=lambda path: {42},
        terminate_terminals=terminated.append,
        startup_timeout=None,
    )

    manager.start("account-1", {"path": r"C:\MT5\terminal64.exe"})
    manager.stop("account-1")

    assert terminated == [set()]


def test_startup_watchdog_marks_timeout_and_stops_owned_terminal():
    terminal_pid_sets = iter([set(), {77}])
    terminated = []
    manager = MT5WorkerManager(
        context=FakeContext(),
        terminal_pids=lambda path: next(terminal_pid_sets),
        terminate_terminals=terminated.append,
        startup_timeout=None,
    )

    manager.start("slow", {"path": r"C:\MT5\terminal64.exe"})
    manager._startup_timeout = 0
    manager._watch_startup("slow", manager._workers["slow"])
    status = manager.get_status("slow")

    assert status.state == "error"
    assert status.error == "MT5 startup timed out after 0 seconds"
    assert status.pid is None
    assert terminated == [{77}]
