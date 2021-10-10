# -*- coding:utf-8 -*-
import os
import sys
import time

import zen
import zen.biom
import zen.misc

from dposlib.ark.v2 import mixin

_GET = zen.biom.dposlib.rest.GET


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
            **{func: params}
        )
        zen.dumpJson(config, "root.json")


def _disableTask(func):
    config = zen.loadJson("root.json")
    tasks = config.get("tasks-enabled", {})
    tasks.pop(func, None)
    config["tasks-enabled"] = tasks
    zen.dumpJson(config, "root.json")


def backupData():
    if zen.biom.archive_data():
        zen.logMsg("data backup successfully done")
        return True
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
    api_peer = config.get("api-peer", zen.API_PEER)
    usernames = [
        name.split("-")[0] for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]

    for user in usernames:
        dlgt = _GET.api.delegates(user, peer=api_peer).get("data", {})
        last_block = dlgt.get("blocks", {}).get("last", {})
        last_computed_block = zen.loadJson(
            "%s.last.block" % user, folder=zen.DATA
        )
        if dlgt and last_computed_block == {}:
            zen.dumpJson(last_block, "%s.last.block" % user, folder=zen.DATA)
            return False
        elif dlgt.get("rank", 52) <= active_delegates:
            blkchn = _GET.api.blockchain(peer=api_peer).get("data", {})
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


# def checkNode():
#     global IS_SYNCING, STATUS, SEED_STATUS, CHECK_RESULT

#     # get database height
#     # int(
#     #     subprocess.check_output(
#     #         shlex.split(
#     #             'psql -qtAX -d ark_mainnet -c '
#     #             '"SELECT height FROM blocks ORDER BY height DESC LIMIT 1"'
#     #         )
#     #     ).strip()
#     # )

#     env = zen.biom.loadEnv(zen.loadJson("root.json")["env"])
#     api_port = env["CORE_API_PORT"]
#     IS_SYNCING = _GET.api.node.syncing(
#         peer="http://127.0.0.1:%s" % api_port
#     ).get("data", {})
#     STATUS = _GET.api.node.status(
#         peer="http://127.0.0.1:%s" % api_port
#     ).get("data", {})
#     SEED_STATUS = _GET.api.node.status(
#         peer=ARK_API_PEER
#     ).get("data", {})

#     try:
#         if STATUS == {}:
#             CHECK_RESULT["not responding"] = True
#             zen.misc.notify("Your node is not responding")
#             zen.logMsg("node is not responding")
#         elif CHECK_RESULT.get("not responding", False):
#             CHECK_RESULT.pop("not responding")
#             zen.misc.notify("Your node is back online")
#         else:
#             zen.logMsg(zen.json.dumps(STATUS))
#             if not STATUS.get("synced"):
#                 if IS_SYNCING["syncing"]:
#                     zen.misc.notify(
#                         "Your node is syncing... %d blocks from network height"
#                         % IS_SYNCING["blocks"]
#                     )
#                 else:
#                     CHECK_RESULT["not syncing"] = True
#                     zen.misc.notify(
#                         "Your node is not synced and seems stoped at height "
#                         "%d, network is at height %d" % (
#                             IS_SYNCING["height"], SEED_STATUS["now"]
#                         )
#                     )
#             elif CHECK_RESULT.get("not syncing", False):
#                 CHECK_RESULT.pop("not syncing")
#                 zen.misc.notify(
#                     "Your node had recovered network height %d" % STATUS["now"]
#                 )

#     except Exception as e:
#         zen.logMsg("node check error:\n%r\n%s" % (e, traceback.format_exc()))
