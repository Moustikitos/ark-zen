# -*- encoding:utf-8 -*-
import os
import io
import sys
import time
import traceback
import threading
import subprocess

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


def checkVersion():
    try:
        peers = zen.dposlib.rest.GET.api.peers(orderBy="version:desc").get(
            "data", []
        )
        if len(peers):
            # pop the very first update
            versions = set([p["version"] for p in peers[1:]])
            last = sorted([int(e) for e in v.split(".")] for v in versions)[-1]
            last = ".".join(["%s" % i for i in last])
            if (last.encode("utf-8") if zen.PY3 else last) \
               not in subprocess.check_output(["ark", "version"]).split()[0]:
                zen.logMsg("your node have to be updated to %s" % last)
                zen.misc.notify("your node have to be upgraded to %s" % last)
            else:
                zen.logMsg("your node is up to date (%s)" % last)
    except Exception as e:
        zen.logMsg(
            "version check error:\n%r\n%s" % (e, traceback.format_exc())
        )


def checkRegistries():
    try:
        for username in [
            name for name in os.listdir(zen.DATA)
            if os.path.isdir(os.path.join(zen.DATA, name))
        ]:
            block_delay = zen.loadJson("%s.json" % username).get(
                "block_delay", False
            )
            blocks = zen.loadJson(
                "%s.forgery" % username,
                folder=os.path.join(zen.DATA, username)
            ).get("blocks", 0)
            if block_delay and blocks >= block_delay:
                zen.logMsg(
                    "%s payroll triggered by block delay : %s [>= %s]" %
                    (username, blocks, block_delay)
                )
                zen.tbw.extract(username)
                zen.tbw.dumpRegistry(username)
                zen.tbw.broadcast(username)
            else:
                zen.tbw.checkApplied(username)
                zen.logMsg(
                    "%s registry checked : %s [< %s]" %
                    (username, blocks, block_delay)
                )
    except Exception as e:
        zen.logMsg(
            "transaction check error:\n%r\n%s" % (e, traceback.format_exc())
        )


def generateCharts():
    try:
        delegates = dict(
            [
                username,
                dict(
                    zen.loadJson(username+".json", zen.JSON),
                    **zen.dposlib.rest.GET.api.delegates(
                        username, returnKey="data")
                    )
                ] for username in [
                    name.split("-")[0] for name in os.listdir(zen.JSON)
                    if name.endswith("-webhook.json")
                ]
        )
        real_blocktime = mixin.deltas()["real blocktime"]
        [
            zen.misc.chartAir(
                delegates[username]["share"], 50, username, real_blocktime
            ) for username in delegates
        ]
        [zen.misc.generateChart(username) for username in delegates]
        zen.misc.chartAir(1., 50, "", real_blocktime)
        zen.logMsg("charts successfully generated")
    except Exception as e:
        zen.logMsg(
            "chart generation error:\n%r\n%s" % (e, traceback.format_exc())
        )


def checkIfForging():
    try:
        usernames = [
            name.split("-")[0] for name in os.listdir(zen.JSON)
            if name.endswith("-webhook.json")
        ]
        delegate_number = zen.dposlib.rest.cfg.activeDelegates
        notification_delay = 10 * 60  # 10 minutes in seconds

        for username in usernames:
            data = zen.dposlib.rest.GET.api.delegates(username) \
                .get("data", {}).get("blocks", {}).get("last", {})
            height = zen.dposlib.rest.GET.api.blockchain() \
                .get("data", {}).get("block", {}).get("height", 0)
            last_block = zen.loadJson(
                "%s.last.block" % username, folder=zen.DATA
            )
            last_round = (data["height"] - 1) // delegate_number
            current_round = (height - 1) // delegate_number

            # if last forged block not found
            if last_block == {}:
                zen.dumpJson(data, "%s.last.block" % username, folder=zen.DATA)
            else:
                # get current height
                # custom parameters
                missed = last_block.get("missed", 0)
                last_notification = last_block.get("notification", 0)
                # blockchain parameters
                diff = current_round - last_round
                now = time.time()
                delay = now - last_notification

                if diff > 1:
                    rank = zen.dposlib.rest.GET.api.delegates(
                        username
                    ).get("data", {}).get("rank", -1)
                    if not rank:
                        zen.logMsg("delegate %s not found" % username)
                    send_notification = (
                        rank <= delegate_number
                    ) and (
                        delay >= notification_delay
                    )
                    # do the possible checks
                    if rank > delegate_number:
                        msg = "%s is not in forging position" % username
                        if delay >= notification_delay:
                            zen.misc.notify(msg)
                            last_block["notification"] = now
                    else:
                        msg = (
                            "%s just missed a block" % username
                        ) if diff == 2 else (
                            "%s is missing blocks (total %d)" %
                            (username, missed + 1)
                        )
                        if send_notification:
                            zen.misc.notify(msg)
                            last_block["notification"] = now
                        last_block["missed"] = missed + 1
                elif missed > 0 or last_notification > 0:
                    msg = "%s is forging again" % username
                    zen.misc.notify(msg)
                    last_block.pop("missed", False)
                    last_block.pop("notification", False)
                else:
                    msg = "%s is forging" % username

                # dump last forged block info
                last_block.update(data)
                zen.dumpJson(
                    last_block, "%s.last.block" % username, folder=zen.DATA
                )

            zen.logMsg(
                "check if forging: %d | %d - %s" %
                (last_round, current_round, msg)
            )

    except Exception as e:
        zen.logMsg(
            "chart generation error:\n%r\n%s" % (e, traceback.format_exc())
        )


def checkNode():
    global IS_SYNCING, STATUS, SEED_STATUS, CHECK_RESULT

    # get database height
    # int(
    #     subprocess.check_output(
    #         shlex.split(
    #             'psql -qtAX -d ark_mainnet -c '
    #             '"SELECT height FROM blocks ORDER BY height DESC LIMIT 1"'
    #         )
    #     ).strip()
    # )

    api_port = zen.rest.cfg.ports["core-api"]
    IS_SYNCING = zen.rest.GET.api.node.syncing(
        peer="http://127.0.0.1:%s" % api_port
    ).get("data", {})
    STATUS = zen.rest.GET.api.node.status(
        peer="http://127.0.0.1:%s" % api_port
    ).get("data", {})
    SEED_STATUS = zen.rest.GET.api.node.status(
        peer="https://explorer.ark.io:8443"
    ).get("data", {})

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
                    zen.misc.notify(
                        "Your node is syncing... %d blocks from network height"
                        % IS_SYNCING["blocks"]
                    )
                else:
                    CHECK_RESULT["not syncing"] = True
                    zen.misc.notify(
                        "Your node is not synced and seems stoped at height "
                        "%d, network is at height %d" % (
                            IS_SYNCING["height"], SEED_STATUS["now"]
                        )
                    )
            elif CHECK_RESULT.get("not syncing", False):
                CHECK_RESULT.pop("not syncing")
                zen.misc.notify(
                    "Your node had recovered network height %d" % STATUS["now"]
                )

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
    daemon_2 = setInterval(3 * sleep_time)(generateCharts)()
    # check all registries
    daemon_3 = setInterval(sleep_time)(checkRegistries)()
    # check updates
    daemon_4 = setInterval(5 * sleep_time)(checkVersion)()
    # check forge
    daemon_5 = setInterval(30)(checkIfForging)()
    zen.logMsg("Background tasks started !")
    zen.misc.notify("Background tasks started !")

    try:
        while not DAEMON.is_set():
            time.sleep(sleep_time)
            zen.logMsg(
                "sleep time finished :\n%s" % zen.json.dumps(CHECK_RESULT)
            )
    except KeyboardInterrupt:
        zen.logMsg("Background tasks interrupted !")

    daemon_1.set()
    daemon_2.set()
    daemon_3.set()
    daemon_4.set()
    daemon_5.set()
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


def deploy():
    with io.open("./bg.service", "w") as unit:
        unit.write(u"""[Unit]
Description=Zen bg tasks
After=network.target

[Service]
User=%(usr)s
WorkingDirectory=%(wkd)s
Environment=PYTHONPATH=%(path)s:${HOME}/dpos
Environment=PATH=$(yarn global bin):$PATH
ExecStart=%(exe)s %(mod)s
Restart=always

[Install]
WantedBy=multi-user.target
""" % {
            "usr": os.environ.get("USER", "unknown"),
            "wkd": os.path.normpath(sys.prefix),
            "path": os.path.normpath(os.path.dirname(__file__)),
            "exe": os.path.normpath(os.path.abspath(sys.executable)),
            "mod": os.path.normpath(os.path.abspath(__file__))
        })
    os.system("chmod +x ./bg.service")
    os.system("sudo mv --force ./bg.service /etc/systemd/system")
    os.system("sudo systemctl daemon-reload")
    os.system("sudo systemctl start bg.service")


if __name__ == "__main__":
    loop()
    start()
