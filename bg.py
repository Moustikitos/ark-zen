# -*- encoding:utf-8 -*-
import os
import time
import traceback
import threading

import zen
import zen.tbw
import zen.misc
import zen.app

from dposlib.ark.v2 import mixin

DAEMON = False
STATUS = SEED_STATUS = IS_SYNCING = {}
CHECK_RESULT = {}


def setInterval(interval):
    """ threaded decorator
    >>> @setInterval(10)
    ... def tick():
    ...     print("Tick")
    >>> event = tick() # print 'Tick' every 10 sec
    >>> type(event)
    <class 'threading.Event'>
    >>> event.set() # stop printing 'Tick' every 10 sec
    """
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


def checkRegistries():
    try:
        for username in [name for name in os.listdir(zen.DATA) if os.path.isdir(os.path.join(zen.DATA, name))]:
            block_delay = zen.loadJson("%s.json" % username).get("block_delay", False)
            blocks = zen.loadJson("%s.forgery" % username, folder=os.path.join(zen.DATA, username)).get("blocks", 0)
            if block_delay and blocks >= block_delay:
                zen.logMsg("%s payroll triggered by block delay : %s [>= %s]" % (username, blocks, block_delay))
                zen.tbw.extract(username)
                zen.tbw.dumpRegistry(username)
                zen.tbw.broadcast(username)
            else:
                zen.tbw.checkApplied(username)
                if zen.tbw.updateRegistryNonces(username):
                    zen.tbw.broadcast(username)
                zen.logMsg("%s registry checked : %s [< %s]" % (username, blocks, block_delay))
    except Exception as e:
        zen.logMsg("transaction check error:\n%r\n%s" % (e, traceback.format_exc()))


def generateCharts():
    try:
        delegates = dict(
            [username, dict(zen.loadJson(username+".json", zen.JSON), **zen.dposlib.rest.GET.api.delegates(username, returnKey="data"))] for \
            username in [name.split("-")[0] for name in os.listdir(zen.JSON) if name.endswith("-webhook.json")]
        )
        real_blocktime = mixin.deltas()["real blocktime"]
        [zen.misc.chartAir(delegates[username]["share"], 50, username, real_blocktime) for username in delegates]
        [zen.misc.generateChart(username) for username in delegates]
        zen.misc.chartAir(1., 50, "", real_blocktime)
        zen.logMsg("charts successfully generated")
    except Exception as e:
        zen.logMsg("chart generation error:\n%r\n%s" % (e, traceback.format_exc()))


def checkNode():
    global IS_SYNCING, STATUS, SEED_STATUS, CHECK_RESULT

    api_port = zen.rest.cfg.ports["core-api"]
    IS_SYNCING = zen.rest.GET.api.node.syncing(peer="http://127.0.0.1:%s" % api_port).get("data", {})
    STATUS = zen.rest.GET.api.node.status(peer="http://127.0.0.1:%s" % api_port).get("data", {})
    SEED_STATUS = zen.rest.GET.api.node.status(peer="https://explorer.ark.io:8443").get("data", {})

    try:
        if STATUS == {}:
            CHECK_RESULT["not responding"] = True
            zen.misc.notify("Your node is not responding")
            zen.logMsg("node is not responding")
        elif CHECK_RESULT.get("not responding", False):
            CHECK_RESULT.pop("not responding")
            zen.misc.notify("Your node is back online")
        else:
            zen.logMsg(zen.json.dumps(STATUS))
            if not STATUS.get("synced"):
                if IS_SYNCING["syncing"]:
                    zen.misc.notify("Your node is syncing... %d blocks from network height" % IS_SYNCING["blocks"])
                else:
                    CHECK_RESULT["not syncing"] = True
                    zen.misc.notify("Your node is not synced and seems stoped at height %d, network is at height %d" % (
                        IS_SYNCING["height"],
                        SEED_STATUS["now"]
                    ))
            elif CHECK_RESULT.get("not syncing", False):
                CHECK_RESULT.pop("not syncing")
                zen.misc.notify("Your node had recovered network height %d" % STATUS["now"])

    except Exception as e:
        zen.logMsg("node check error:\n%r\n%s" % (e, traceback.format_exc()))


def start():
    global DAEMON, IS_SYNCING, STATUS, SEED_STATUS
    sleep_time = zen.rest.cfg.blocktime * zen.rest.cfg.activeDelegates

    data = zen.loadJson("bg-marker.json")
    data["stop"] = False
    zen.dumpJson(data, "bg-marker.json")

    DAEMON = threading.Event()
    # check health status every minutes
    daemon_1 = setInterval(60)(checkNode)()
    # generate svg charts every round
    daemon_2 = setInterval(sleep_time)(generateCharts)()
    # check all registries
    daemon_3 = setInterval(sleep_time)(checkRegistries)()
    zen.logMsg("Background tasks started !")
    zen.misc.notify("Background tasks started !")

    try:
        while not DAEMON.is_set():
            time.sleep(sleep_time)
            zen.logMsg("sleep time finished :\n%s" % zen.json.dumps(CHECK_RESULT))
    except KeyboardInterrupt:
        zen.logMsg("Background tasks interrupted !")

    daemon_1.set()
    daemon_2.set()
    daemon_3.set()
    zen.misc.notify("Background tasks stoped !")


def stop():
    data = zen.loadJson("bg-marker.json")
    data["stop"] = True
    zen.dumpJson(data, "bg-marker.json")


@setInterval(60)
def loop():
    global DAEMON
    data = zen.loadJson("bg-marker.json")
    if data["stop"] and isinstance(DAEMON, threading._Event):
        DAEMON.set()


if __name__ == "__main__":
    loop()
    start()
