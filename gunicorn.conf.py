# -*- coding:utf-8 -*-
import zen
import zen.biom


def post_worker_init(worker):
    custom_peers = zen.loadJson("tbw.json").get("custom_peers", [])
    if len(custom_peers) > 0:
        zen.biom.dposlib.core.stop()
        zen.biom.dposlib.rest.cfg.peers = custom_peers


def on_exit(server):
    pass
