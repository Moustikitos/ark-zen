# -*- coding:utf-8 -*-
import os
import zen
import zen.biom


def post_worker_init(worker):
    for username in [
        n.replace("-webhook.json", "") for n in next(os.walk(zen.JSON))[-1]
        if n.endswith("-webhook.json")
    ]:
        zen.biom.getUsernameKeys(username)
        zen.logMsg("%s secrets loaded and hidden !" % username)

    custom_peers = zen.loadJson("tbw.json").get("custom_peers", [])
    if len(custom_peers) > 0:
        zen.biom.dposlib.core.stop()
        zen.biom.dposlib.rest.cfg.peers = custom_peers


def on_exit(server):
    pass
