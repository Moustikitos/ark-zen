# -*- encoding:utf-8 -*-

import os
import io
import sys
import json
import importlib
import traceback
import threading

import zen
import zen.tbw
import zen.misc
import zen.biom
import zen.task

RELEASE = threading.Event()
REPORT = {}


def setInterval(interval):
    def decorator(function):
        """Main decorator function."""
        def wrapper(*args, **kwargs):
            """Helper function to create thread."""
            stopped = threading.Event()

            # executed in another thread
            def _loop():
                """Thread entry point."""
                # until stopped
                while not stopped.wait(interval):
                    function(*args, **kwargs)
            t = threading.Thread(target=_loop)
            # stop if the program exits
            t.daemon = True
            t.start()
            return stopped
        return wrapper
    return decorator


def deploy():
    normpath = os.path.normpath

    with io.open("./bg.service", "w") as unit:
        unit.write(u"""[Unit]
Description=Zen bg tasks
After=network.target

[Service]
User=%(usr)s
WorkingDirectory=%(wkd)s
Environment=PYTHONPATH=%(path)s
ExecStart=%(exe)s %(mod)s
Restart=always

[Install]
WantedBy=multi-user.target
""" % {
            "usr": os.environ.get("USER", "unknown"),
            "wkd": normpath(sys.prefix),
            "path": normpath(os.path.dirname(__file__)),
            "mod": normpath(os.path.abspath(__file__)),
            "exe": normpath(sys.executable)
        })

    os.system("chmod +x ./bg.service")
    os.system("sudo mv --force ./bg.service /etc/systemd/system")
    os.system("sudo systemctl daemon-reload")
    if not os.system("sudo systemctl restart bg"):
        os.system("sudo systemctl start bg")


def _launcher(func):
    name = func.__name__
    try:
        REPORT[name] = func()
    except Exception as error:
        zen.LOG.error(
            "%s exception:\n%r\n%s" %
            (func.__name__, error, traceback.format_exc())
        )
        REPORT[name] = "%r" % error


def start():
    info = zen.loadJson("root.json")
    tasks = info.get("tasks-enabled", {})
    sleep_time = info.get("sleep-time", 60*5)

    daemons = []
    for task, params in tasks.items():
        func = getattr(zen.task, task)
        if callable(func):
            daemons.append(setInterval(params["interval"])(_launcher)(func))
            zen.LOG.info(
                "%s daemon set: interval=%ss" % (task, params["interval"])
            )
            importlib.reload(zen.task)

    RELEASE.clear()
    while not RELEASE.is_set():
        RELEASE.wait(timeout=float(sleep_time))
        zen.LOG.info(
            "Sleep time finished :\n%s" % json.dumps(REPORT, indent=2)
        )

    for daemon in daemons:
        daemon.set()


if __name__ == "__main__":
    import signal

    def exit_handler(*args, **kwargs):
        RELEASE.set()
        zen.biom.push_keys()
        zen.LOG.info("Background tasks stopped !")
        zen.misc.notify("Background tasks stopped !")

    def show_hidden(*args, **kwargs):
        report = {}
        for key, value in [
            (k, v) for k, v in zen.biom.__dict__.items() if "#" in k
        ]:
            uname_mrk, num = key.replace("_", "").split("#")
            if value is not None:
                report[uname_mrk] = report.get(uname_mrk, []) + ["puk#" + num]
        msg = "Loaded private keys = %s" % json.dumps(report)
        zen.LOG.info(msg)
        zen.misc.notify(msg)

    signal.signal(signal.SIGTERM, exit_handler)
    if "win" not in sys.platform:
        signal.signal(signal.SIGUSR1, show_hidden)

    zen.LOG.info("Background tasks started !")
    zen.misc.notify("Background tasks started !")
    try:
        zen.biom.pull_keys()
        start()
    except KeyboardInterrupt:
        exit_handler()
