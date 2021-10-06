# -*- encoding:utf-8 -*-
import os
import io
import sys
import time
import json
import traceback
import threading
import subprocess

import zen
import zen.tbw
import zen.app
import zen.misc
import zen.biom

from dposlib.ark.v2 import mixin

DAEMON = False
STATUS = SEED_STATUS = IS_SYNCING = {}
CHECK_RESULT = {}
ARK_API_PEER = "https://api.ark.io"

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
        peers = zen.biom.dposlib.rest.GET.api.peers(
            orderBy="version:desc"
        ).get("data", [])
        peers = [
            p for p in peers if "@alessiodf/core-bridge-2.7" not in p["ports"]
        ]
        node = zen.biom.dposlib.rest.GET.api.node.configuration(
            peer=zen.API_PEER
        ).get("data", {}).get("core", {}).get("version", False)
        if node and len(peers):
            # pop the very first update
            versions = set([p["version"].split("-")[0] for p in peers[1:]])
            last = sorted([int(e) for e in v.split(".")] for v in versions)[-1]
            last = ".".join(["%s" % i for i in last])
            if node != last:
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
                    **zen.biom.dposlib.rest.GET.api.delegates(
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
                delegates[username].get("share", 1.0), 50,
                username, real_blocktime
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
        delegate_number = zen.biom.dposlib.rest.cfg.activeDelegates
        notification_delay = 10 * 60  # 10 minutes in seconds

        for username in usernames:
            dlgt = zen.biom.dposlib.rest.GET.api.delegates(
                username, peer=ARK_API_PEER
            ).get("data", {})
            data = dlgt.get("blocks", {}).get("last", {})
            height = zen.biom.dposlib.rest.GET.api.blockchain(
                peer=ARK_API_PEER
            ).get("data", {}).get("block", {}).get("height", 0)
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
                    rank = dlgt.get("rank", -1)
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

    env = zen.biom.loadEnv(zen.loadJson("root.json")["env"])
    api_port = env["CORE_API_PORT"]
    IS_SYNCING = zen.biom.dposlib.rest.GET.api.node.syncing(
        peer="http://127.0.0.1:%s" % api_port
    ).get("data", {})
    STATUS = zen.biom.dposlib.rest.GET.api.node.status(
        peer="http://127.0.0.1:%s" % api_port
    ).get("data", {})
    SEED_STATUS = zen.biom.dposlib.rest.GET.api.node.status(
        peer=ARK_API_PEER
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


def start(relay=False):
    global DAEMON, IS_SYNCING, STATUS, SEED_STATUS
    sleep_time = zen.tbw.rest.cfg.blocktime * zen.tbw.rest.cfg.activeDelegates
    sys.path.append(os.path.expanduser("~/.yarn/bin"))

    DAEMON = threading.Event()
    if relay:
        # check health status every minutes
        daemon_1 = setInterval(60)(checkNode)()
        # check updates
        daemon_2 = setInterval(5 * sleep_time)(checkVersion)()
        # check forge
        daemon_3 = setInterval(30)(checkIfForging)()
    # generate svg charts every 3 round
    daemon_4 = setInterval(3 * sleep_time)(generateCharts)()
    # check all registries
    daemon_5 = setInterval(sleep_time)(checkRegistries)()

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
        DAEMON.set()

    if relay:
        daemon_1.set()
        daemon_2.set()
        daemon_3.set()
    daemon_4.set()
    daemon_5.set()

    zen.misc.notify("Background tasks stoped !")


def stop():
    global DAEMON
    if isinstance(DAEMON, threading.Event):
        DAEMON.set()


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
Environment=PATH=$(/usr/bin/yarn global bin):$PATH
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


if __name__ == "__main__":
    import signal

    # pull all secrets from config files so they are not visible
    for username in [
        n.replace("-webhook.json", "") for n in next(os.walk(zen.JSON))[-1]
        if n.endswith("-webhook.json")
    ]:
        zen.biom.getUsernameKeys(username)

    # push back all secrets into config files for next bg task start
    def signal_handler(signal, frame):
        zen.biom.pushBackKeys()
        zen.misc.notify("Background tasks stopped !")
        zen.logMsg("Secrets pushed back.")
        sys.exit(0)

    def show_keys(signal, frame):
        report = {}
        for key, value in [
            (k, v) for k, v in zen.biom.__dict__.items() if k[-2:] in "#1#2"
        ]:
            username, num = key.replace("_", "").split("#")
            if value is not None:
                report[username] = report.get(username, []) + ["puk#" + num]
        msg = "Private keys:\n%s" % json.dumps(report)
        zen.logMsg(msg)
        zen.misc.notify(msg)

    # register CTRL+C signal and SYSTEMCTL terminal signal
    signal.signal(signal.SIGINT, show_keys)
    signal.signal(signal.SIGTERM, signal_handler)

    root = zen.loadJson("root.json")
    zen.biom.dposlib.rest.use(root.get("blockchain", "dark"))
    start(relay="env" in root)
