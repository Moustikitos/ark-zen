# -*- encoding:utf-8 -*-
import os
import math
import json
import flask
import dposlib

import zen
import zen.tbw
import zen.misc
import zen.biom

DAEMON = zen.tbw.TaskExecutioner()

# create the application instance
app = flask.Flask(__name__)
app.config.update(
    # 300 seconds = 5 minutes lifetime session
    PERMANENT_SESSION_LIFETIME=300,
    # used to encrypt cookies
    # secret key is generated each time app is restarted
    SECRET_KEY=os.urandom(24),
    # JS can't access cookies
    SESSION_COOKIE_HTTPONLY=True,
    # if use of https
    SESSION_COOKIE_SECURE=False,
    # update cookies on each request
    # cookie are outdated after PERMANENT_SESSION_LIFETIME seconds of idle
    SESSION_REFRESH_EACH_REQUEST=True,
    #
    TEMPLATES_AUTO_RELOAD=True
)


@app.route("/block/forged", methods=["POST", "GET"])
def spread():
    if flask.request.method == "POST":
        zen.tbw.TaskExecutioner.JOB.put([
            flask.request.headers["Authorization"],
            json.loads(flask.request.data).get("data", False)
        ])
    return json.dumps({"zen-tbw::block/forged": True})


@app.context_processor
def tweak():
    tbw_config = zen.loadJson("tbw.json")
    token = dposlib.core.cfg.symbol
    return dict(
        url_for=dated_url_for,
        tbw_config=tbw_config,
        _currency=lambda value, fmt="r": flask.Markup(
            ("%" + fmt + "&nbsp;%s") % (round(value, 8), token)
        ),
        _dhm=lambda value: human_dhm(*dhm(value)),
        _address=lambda address: flask.Markup(
            '<span class="not-ellipsed">%s</span>'
            '<span class="ellipsed">%s</span>' %
            (
                address,
                "%s&nbsp;&#x2026;&nbsp;%s" % (address[:5], address[-5:])
            )
        )
    )


def dhm(last_blocks):
    days = \
        last_blocks * zen.biom.dposlib.rest.cfg.blocktime * \
        zen.biom.dposlib.rest.cfg.activeDelegates / (3600.*24)
    hours = (days - math.floor(days)) * 24
    minutes = (hours - math.floor(hours)) * 60
    return math.floor(days), math.floor(hours), math.floor(minutes)


def human_dhm(d, h, m):
    return ("" if d < 1 else ("%d day" % d + ("s " if d > 1 else " "))) + \
           ("" if h < 1 else ("%d hour" % h + ("s " if h > 1 else " "))) + \
           ("" if m < 1 else ("%d minute" % m + ("s" if m > 1 else "")))


########################
# css reload bugfix... #
########################
def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get("filename", False)
        if filename:
            file_path = os.path.join(app.root_path, endpoint, filename)
            try:
                values["q"] = int(os.stat(file_path).st_mtime)
            except OSError:
                pass
    return flask.url_for(endpoint, **values)
########################
