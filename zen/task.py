# -*- coding:utf-8 -*-

import os
import sys
import time
import subprocess
import shlex

import zen
import zen.biom
import zen.misc

from dposlib.ark import mixin

_GET = zen.biom.dposlib.rest.GET

for path in zen.__path__:
    pass


def _tasks():
    mod = sys.modules[__name__]
    return [
        name for name in dir(mod)
        if not name.startswith("_") and callable(getattr(mod, name))
    ]


def _enableTask(delay, func, **params):
    if func not in ["enableTask", "disableTask"]:
        config = zen.loadJson("root.json")
        params.update(interval=delay)
        config["tasks-enabled"] = dict(
            config.get("tasks-enabled", {}),
            **{func: dict(
                [k.replace("_", "-"), v] for k, v in params.items()
            )}
        )
        zen.dumpJson(config, "root.json")


def _disableTask(func):
    config = zen.loadJson("root.json")
    tasks = config.get("tasks-enabled", {})
    tasks.pop(func, None)
    config["tasks-enabled"] = tasks
    zen.dumpJson(config, "root.json")


def checkRegistries():
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
        else:
            zen.tbw.checkApplied(username)
            zen.logMsg(
                "%s registry checked : %s [< %s]" %
                (username, blocks, block_delay)
            )

        if zen.tbw.dumpRegistry(username):
            zen.tbw.broadcast(username)
            zen.logMsg("%s registry dumped and broadcasted" % username)


def backupData():
    config = zen.loadJson("root.json").get("tasks-enabled", {}).get(
        "backupData", {}
    )
    backup_type = config.get("backup-type", ".tar.bz2")
    backup_number = config.get("backup-number", 5)
    backup_folder = os.path.abspath(
        config.get("backup-folder", zen.__path__[0])
    )
    os.makedirs(backup_folder, exist_ok=True)
    if not zen.biom.archive_data(backup_folder, backup_type):
        zen.logMsg("data backup successfully done")
        backups = [
            os.path.join(backup_folder, name)
            for name in os.listdir(backup_folder) if ".tar" in name
        ]
        if len(backups) > backup_number:
            backups.sort(key=lambda p: os.stat(p).st_mtime)
            for path in backups[:-backup_number]:
                os.remove(path)
        return backups[-1]
    else:
        zen.logMsg("data backup failed")
        return False


def checkVersion():
    peers = _GET.api.peers(orderBy="version:desc")
    peers = [
        p for p in peers.get("data", [])
        if int(p["version"].split(".")[1]) < 10
    ]
    node = _GET.api.node.configuration(peer=zen.API_PEER).get("data", {})\
        .get("core", {}).get("version", False)
    if node and len(peers):
        versions = set([p["version"].split("-")[0] for p in peers])
        last = sorted([int(e) for e in v.split(".")] for v in versions)[-1]
        last = ".".join(["%s" % i for i in last])
        if node != last:
            zen.logMsg("your node have to be updated to %s" % last)
            zen.misc.notify("your node have to be upgraded to %s" % last)
            return False
        else:
            zen.logMsg("your node is up to date (%s)" % last)
    return True


def generateCharts():
    delegates = dict(
        [
            username,
            dict(
                zen.loadJson(username+".json", zen.JSON),
                **_GET.api.delegates(username, returnKey="data"))
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
    return True


def checkIfForging():
    config = zen.loadJson("root.json").get("tasks-enabled", {}).get(
        "checkIfForging", {}
    )
    active_delegates = zen.biom.dposlib.rest.cfg.activeDelegates
    notification_delay = config.get("notification-delay", 10 * 60)
    monitored_peer = config.get("monitored-peer", zen.API_PEER)
    usernames = [
        name.split("-")[0] for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]

    for user in usernames:
        dlgt = _GET.api.delegates(user, peer=monitored_peer).get("data", {})
        last_block = dlgt.get("blocks", {}).get("last", {})
        last_computed_block = zen.loadJson(
            "%s.last.block" % user, folder=zen.DATA
        )
        if dlgt and last_computed_block == {}:
            zen.dumpJson(last_block, "%s.last.block" % user, folder=zen.DATA)
            return False
        elif dlgt.get("rank", 52) <= active_delegates:
            blkchn = _GET.api.blockchain(peer=monitored_peer).get("data", {})
            height = blkchn.get("block", {}).get("height", 0)
            current_round = (height - 1) // active_delegates
            dlgt_round = (last_block["height"] - 1) // active_delegates

            diff = current_round - dlgt_round
            missed = last_computed_block.get("missed", 0)
            if diff > 1:
                now = time.time()
                last_computed_block["missed"] = missed + 1
                delay = now - last_computed_block.get("notification", 0)
                msg = ("%s just missed a block" % user) if missed < 1 else (
                    "%s is missing blocks (total %d)" % (user, missed + 1)
                )
                if delay > notification_delay:
                    zen.misc.notify(msg)
                    last_computed_block["notification"] = now
            elif missed > 0:
                msg = "%s is forging again" % user
                zen.misc.notify(msg)
                last_computed_block.pop("notification", False)
                last_computed_block.pop("missed", False)
            else:
                msg = "%s is forging" % user

            last_computed_block.update(last_block)
            zen.dumpJson(
                last_computed_block, "%s.last.block" % user, folder=zen.DATA
            )
            zen.logMsg(
                "round check [delegate:%d | blockchain:%d] - %s" %
                (dlgt_round, current_round, msg)
            )
    return True


def checkNode():
    global REPORT
    REPORT = {}

    root = zen.loadJson("root.json")
    config = root.get("tasks-enabled", {}).get("checkNode", {})

    seed_peer = config.get("seed-peer", False)
    if not seed_peer:
        zen.logMsg("no seed peer defined")
        return "no seed peer defined"

    monitored_peer = config.get("monitored-peer", zen.API_PEER)
    syncing = _GET.api.node.syncing(peer=monitored_peer).get("data", {})
    status = _GET.api.node.status(peer=seed_peer).get("data", {})
    notification_delay = config.get("notification-delay", 5 * 60)

    if syncing == {}:
        msg = "%s not responding" % monitored_peer
        now = time.time()
        if now - REPORT.get("not responding", now) > notification_delay:
            REPORT["not responding"] = time.time()
            zen.logMsg(msg)
            zen.misc.notify(msg)
        return msg
    elif REPORT.pop("not responding", False):
        msg = "%s is active again" % monitored_peer
        zen.logMsg(msg)
        zen.misc.notify(msg)

    if root.get("env", False):
        height = int(
            subprocess.check_output(
                shlex.split(
                    '/usr/bin/psql -qtAX -d ark_mainnet -c '
                    '"SELECT height FROM blocks ORDER BY height DESC LIMIT 1"'
                )
            ).strip()
        )
    else:
        height = syncing["height"]

    height_diff = status.get("now", height) - height

    if syncing.get("syncing", False):
        msg = "%s not synced: height diff %s" % (monitored_peer, height_diff)
        now = time.time()
        if now - REPORT.get("not synced", now) > notification_delay:
            REPORT["not synced"] = time.time()
            zen.logMsg(msg)
            zen.misc.notify(msg)
    elif REPORT.pop("not responding", False):
        msg = "%s synced at height %s" % (monitored_peer, height_diff)
        zen.logMsg(msg)
        zen.misc.notify(msg)
    else:
        msg = "%s synced @ height %s" % (monitored_peer, height)

    return msg


# must be done as bellow because of docstring formating
backupData.__doc__ = f"""
Usage:
    backupData [-f <folder> -n <number> -t <type>] [-0]

Options:
    -t --backup-type=<type>      tar extension [default: .tar.bz2]
    -n --backup-number=<number>  backup number [default: int|5]
    -f --backup-folder=<folder>  backup folder [default: {zen.__path__[0]}]
"""
checkIfForging.__doc__ = f"""
Usage:
    checkIfForging [-p <peer> -d <delay>] [-0]

Options:
    -p --monitored-peer=<peer>       monitored peer [default: {zen.API_PEER}]
    -d --notification-delay=<delay>  minimum delay  [default: int|600]
"""
checkNode.__doc__ = f"""
Usage:
    checkNode [-s <seed> -p <peer> -d <delay>] [-0]

Options:
    -s --seed-peer=<peer>            reference peer
    -p --monitored-peer=<peer>       monitored peer [default: {zen.API_PEER}]
    -d --notification-delay=<delay>  minimum delay  [default: int|300]
"""
