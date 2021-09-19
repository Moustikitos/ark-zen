# -*- coding:utf-8 -*-
import zen


def post_worker_init(worker):
    # initialize blockchain network
    zen.rest.use(zen.loadJson("root.json").get("blockchain", "dark"))
    # customize blockchain network
    custom_peers = zen.loadJson("tbw.json").get("custom_peers", [])
    if len(custom_peers) > 0:
        zen.dposlib.core.stop()
        zen.dposlib.rest.cfg.peers = custom_peers


def on_exit(server):
    pass
