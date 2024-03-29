# -*- encoding:utf-8 -*-
import os
import zen
import math
import time
import hashlib
import binascii
from collections import OrderedDict

import flask
import dposlib
import dposlib.rest

import zen.misc
from zen.app.core import app
from zen.tbw import initDb


def connect(username):
    if not hasattr(flask.g, username):
        setattr(flask.g, username, initDb(username))
    return getattr(flask.g, username).cursor()


@app.route("/")
def index():
    usernames = [
        name.split("-")[0]
        for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]
    accounts = [
        dposlib.rest.GET.api.delegates(username, returnKey="data")
        for username in usernames
    ]
    return flask.render_template(
        "index.html",
        accounts=[a for a in accounts if a.get("username", False)]
    )


@app.route('/backup/download', methods=["GET", "POST"])
def download_backup():
    if flask.request.method == "POST":
        challenge = zen.loadJson("challenge.json")
        value = flask.request.form.get("value")
        if time.time() > challenge.get("expiration", 0):
            return "", 408
        elif challenge.get("value", "") != value:
            return "", 403
        else:
            backup_folder = os.path.abspath(
                zen.loadJson("root.json").get("tasks-enabled", {}).get(
                    "backupData", {}
                ).get(
                    "backup-folder", zen.__path__[0]
                )
            )
            backups = [
                os.path.join(backup_folder, name)
                for name in os.listdir(backup_folder) if ".tar" in name
            ]
            if not len(backups):
                return "", 404
            backups.sort(key=lambda p: os.stat(p).st_mtime)
            return flask.send_file(backups[-1], as_attachment=True)

    elif flask.request.method == "GET":
        last_chalenge = zen.loadJson("challenge.json")
        if time.time() > last_chalenge.get("expiration", 0):
            challenge = "%s" % int(
                hashlib.sha256(
                    binascii.hexlify(os.urandom(32))
                ).hexdigest()[:5],
                16
            )
            zen.dumpJson(
                {"value": challenge, "expiration": time.time() + 60},
                "challenge.json"
            )
            zen.misc.notify("Your challenge code is:\n%s" % challenge)
        return flask.render_template("backup.html")


@app.route("/faq")
def faq():
    registered_usernames = [
        name.split("-")[0] for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]

    data = dict(
        (k, v) for k, v in dposlib.core.cfg.__dict__.items()
        if not k.startswith('_')
    )
    data["begintime"] = data["begintime"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
    try:
        data["blocktime"] = dposlib.core.mixin.deltas()["real blocktime"]
    except Exception as e:
        zen.logMsg('error occured computing deltas : %s' % e)

    delegates = dict(
        [
            username,
            dict(
                zen.loadJson(username+".json", zen.JSON),
                **dposlib.rest.GET.api.delegates(username, returnKey="data")
            )
        ] for username in registered_usernames
    )

    for username in registered_usernames:
        minvote = delegates[username].get("minimum_vote", 0.) * 100000000
        maxvote = delegates[username].get("maximum_vote", None)
        if isinstance(maxvote, (int, float)):
            maxvote *= 100000000
            _max = lambda v, maxi=maxvote: min(maxi, v)
        else:
            _max = lambda v, maxi=maxvote: v
        _min = lambda v, mini=minvote: v if v >= mini else 0
        delegates[username]["votes"] = sum([
            _min(_max(float(v["balance"]))) for v in
            zen.misc.loadPages(
                dposlib.rest.GET.api.delegates.__getattr__(username).voters
            )
        ])/100000000

    return flask.render_template("faq.html", info=data, delegates=delegates)


@app.route("/<string:username>")
def delegate_index(username):
    if username not in [
        name.split("-")[0] for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]:
        return "", 400

    config = zen.loadJson("%s.json" % username)
    config.pop("#1", False)
    config.pop("#2", False)
    forgery = zen.loadJson(
        "%s.forgery" % username, os.path.join(zen.DATA, username)
    )
    forgery["contributions"] = OrderedDict(
        sorted(
            [item for item in forgery.get("contributions", {}).items()],
            key=lambda i: i[-1],
            reverse=True
        )
    )
    return flask.render_template(
        "delegate.html", username=username, forgery=forgery, config=config
    )


@app.route("/<string:username>/history/<int:page>/<int:n>")
def zen_history(username, page, n):
    if username not in [
        name.split("-")[0] for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]:
        return "", 400

    cursor = connect(username)
    history_folder = os.path.join(zen.ROOT, "app", ".tbw", username, "history")

    tbw_list = [
        r["filename"] for r in cursor.execute(
            "SELECT DISTINCT filename FROM transactions"
        ).fetchall()
    ]
    tbw_list.sort(reverse=True)

    n_tbw = len(tbw_list)
    n_page = int(math.ceil(float(n_tbw) / n))
    start = page*n

    selection = list(sorted(tbw_list, reverse=True))[start:start+n]
    data = dict(
        [name, zen.loadJson(name+".tbw", folder=history_folder)]
        for name in selection
    )

    details = dict(
        [
            name,
            cursor.execute(
                "SELECT * FROM transactions WHERE filename = ? ORDER BY amount"
                " DESC", (name,)
            ).fetchall()
        ] for name in selection
    )

    return flask.render_template(
        "history.html",
        username=username,
        curent_page=page,
        page_number=n_page,
        entry_number=n,
        selection=selection,
        data=data,
        details=details
    )


@app.route("/<string:username>/history/<int:page>/<int:n>/<string:item>")
def zen_details(username, page, n, item):
    if username not in [
        name.split("-")[0] for name in os.listdir(zen.JSON)
        if name.endswith("-webhook.json")
    ]:
        return "", 400

    cursor = connect(username)
    details = cursor.execute(
        "SELECT * FROM transactions WHERE filename = ? ORDER BY amount DESC",
        (item, )
    ).fetchall()

    return flask.render_template(
        "details.html",
        username=username,
        curent_page=page,
        entry_number=n,
        item=item,
        details=details
    )
