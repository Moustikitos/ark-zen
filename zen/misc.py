# -*- coding:utf-8 -*-

import os
import time
import base64
import datetime

import zen
import zen.tbw
import pygal
import pygal.style

from dposlib.rest import req as uio_req

PM2_PREFFIX_NAMES = {
    "ark": "ark",
    "dark": "ark",
    "prs": "persona"
}

INTEROPERABILITY = {
    "relay": {
        "ark": "yarn exec ark relay:start",
        "dark": "yarn exec ark relay:start",
        "prs": "bash ~/core-control/ccontrol.sh start relay"
    },
    "forger": {
        "ark": "yarn exec ark forger:start",
        "dark": "yarn exec ark forger:start",
        "prs": "bash ~/core-control/ccontrol.sh start forger"
    }
}

APPS = {
    "relay": INTEROPERABILITY["relay"].get(
        zen.rest.cfg.network, "yarn exec ark relay:start"
    ),
    "forger": INTEROPERABILITY["forger"].get(
        zen.rest.cfg.network, "yarn exec ark relay:start"
    ),
    "zen-srv": "cd ~/ark-zen && pm2 start srv.json -s",
    "zen-bg": "cd ~/ark-zen && pm2 start bg.json -s",
}


def shorten(address, chunk=5):
    return address[:chunk]+"..."+address[-chunk:]


def urlWallet(address):
    return zen.rest.cfg.explorer+"/wallets/"+address


def transactionApplied(id):
    data = zen.rest.GET.api.transactions(id).get("data", {})
    if isinstance(data, dict):
        return data.get("confirmations", 0) >= 10
    else:
        return False


def delegateIsForging(username):
    dlgt = zen.rest.GET.api.delegates(username).get("data", {})
    rank = dlgt.get("rank", dlgt.get("attributes", {}).get("rank", -1))
    return rank != -1 and rank <= zen.rest.cfg.activeDelegates


def regenerateUnapplied(username, filename):
    registry = zen.loadJson(
        "%s.registry" % filename, os.path.join(zen.DATA, username)
    )
    tbw = zen.loadJson(
        "%s.tbw" % filename, os.path.join(zen.TBW, username, "history")
    )

    for tx in registry.values():
        if not transactionApplied(tx["id"]):
            zen.logMsg(
                'tx %(id)s [%(amount)s --> %(recipientId)s] unapplied' % tx
            )
        else:
            tbw["weight"].pop(tx["recipientId"], False)

    zen.dumpJson(
        tbw, '%s-unapplied.tbw' % filename, os.path.join(zen.TBW, username)
    )


def loadPages(
    endpoint, pages=None, quiet=True, nb_tries=10, peer=None, condition=[]
):
    if not isinstance(endpoint, uio_req.EndPoint):
        raise Exception("Invalid endpoint class")
    count, pageCount, data = 0, 1, []
    while count < pageCount:
        req = endpoint.__call__(page=count+1, peer=peer)
        if req.get("error", False):
            nb_tries -= 1
            if not quiet:
                zen.logMsg("Api error occured... [%d tries left]" % nb_tries)
            if nb_tries <= 0:
                raise Exception("Api error occured: %r" % req)
        else:
            pageCount = req["meta"]["pageCount"]
            if isinstance(pages, int):
                pageCount = min(pages, pageCount)
            if not quiet:
                zen.logMsg("reading page %s over %s" % (count+1, pageCount))
            data.extend(req.get("data", []))
            count += 1
    return data


def loadCryptoCompareYearData(year, reference, interest):
    req = zen.rest.GET.data.histoday(
        peer="https://min-api.cryptocompare.com",
        fsym=reference,
        tsym=interest,
        limit=365,
        toTs=int(datetime.datetime(year, 12, 31, 23, 59).timestamp())
        )
    if req["Response"] == "Success":
        return req["Data"]
    else:
        raise Exception("can not reach data")


def freemobile_sendmsg(title, body):
    freemobile = zen.loadJson("freemobile.json")
    if freemobile != {}:
        freemobile["msg"] = title + ":\n" + body
        return zen.rest.POST.sendmsg(
            peer="https://smsapi.free-mobile.fr",
            jsonify=freemobile
        )


def pushbullet_pushes(title, body):
    pushbullet = zen.loadJson("pushbullet.json")
    if pushbullet != {}:
        return zen.rest.POST.v2.pushes(
            peer="https://api.pushbullet.com",
            body=body, title=title, type="note",
            headers={
                'Access-Token': pushbullet["token"],
            }
        )


def pushover_messages(title, body):
    pushover = zen.loadJson("pushover.json")
    if pushover != {}:
        return zen.rest.POST(
            "1", "messages.json",
            peer="https://api.pushover.net",
            urlencode=dict(
                message=body,
                title=title,
                **pushover
            )
        )


def twilio_messages(title, body):
    twilio = zen.loadJson("twilio.json")
    if twilio != {}:
        authentication = base64.b64encode(
            ("%s:%s" % (twilio["sid"], twilio["auth"])).encode('utf-8')
        )
        return zen.rest.POST(
            "2010-04-01", "Accounts", twilio["sid"], "Messages.json",
            peer="https://api.twilio.com",
            urlencode={
                "From": twilio["sender"],
                "To": twilio["receiver"],
                "Body": body,
            },
            headers={
                "Authorization": "Basic %s" % authentication.decode('ascii')
            }
        )


def notify(body):
    title = "ark-zen@%s" % zen.dposlib.core.cfg.network
    body = body.decode("utf-8") if isinstance(body, bytes) else body

    for func in [
        freemobile_sendmsg,
        pushbullet_pushes,
        pushover_messages,
        twilio_messages
    ]:
        response = func(title, body)
        if isinstance(response, dict):
            zen.logMsg(
                "%s: notification response:\n%s" % (func.__name__, response)
            )
            if response.get("status", 1000) < 300:
                return response


def start_pm2_app(appname):
    _appname = appname
    if appname in INTEROPERABILITY:
        appname = PM2_PREFFIX_NAMES[zen.rest.cfg.network]+"-"+appname
    os.system(r'''
if echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
    %(pm2_app_cmd)s
else
    echo "(re)starting %(appname)s..."
    pm2 restart %(appname)s -s
fi
''' % {
            "appname": appname,
            "pm2_app_cmd": APPS.get(
                _appname, "echo pm2 cmd line not defined in zen script"
            )
        }
    )


def stop_pm2_app(appname):
    if appname in INTEROPERABILITY:
        appname = PM2_PREFFIX_NAMES[zen.rest.cfg.network]+"-"+appname
    os.system(r'''
if ! echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
    echo stoping %(appname)s...
    pm2 stop %(appname)s -s
fi
''' % {"appname": appname}
    )


def del_pm2_app(appname):
    if appname in INTEROPERABILITY:
        appname = PM2_PREFFIX_NAMES[zen.rest.cfg.network]+"-"+appname
    os.system(r'''
if ! echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
    echo deleting %(appname)s...
    pm2 delete %(appname)s -s
fi
''' % {"appname": appname}
    )


def generateChart(username):
    cursor = zen.tbw.initDb(username)
    timestamp = time.time() - (30*24*60*60)
    return chartTimedData(
        (
            [
                datetime.datetime.fromtimestamp(row["timestamp"]),
                row["value"]
            ] for row in cursor.execute(
                "SELECT * FROM dilution WHERE timestamp > ? "
                "ORDER BY timestamp DESC", (timestamp, )
            ).fetchall()
        ),
        username
    )


def chartTimedData(data, username=""):

    chart = pygal.DateTimeLine(
        fill=True,
        show_legend=False,
        show_x_labels=False,
        show_y_labels=False,
        width=1024,
        x_label_rotation=25, truncate_label=-1,
        x_value_formatter=lambda dt: dt.strftime('%m/%d/%y-%Hh%M'),
        style=pygal.style.LightStyle
    )
    chart.add(
        "block weight % / Ѧ1000 vote",
        [(d, round(1000*100*v, 4)) for d, v in data]
    )

    chart.render_to_file(
        os.path.join(zen.ROOT, "app", "static", "ctd_%s.svg" % username)
    )
    # return chart.render_data_uri()


def chartAir(share, nb_points=100, username="", blocktime=None):
    info = zen.dposlib.rest.cfg
    _get = zen.dposlib.rest.GET
    blocktime = info.blocktime if not blocktime else blocktime

    delegates = _get.api.delegates()["data"][:51]
    min_vote, max_vote = [
        int(d["votes"])/100000000.
        for d in sorted(
            delegates[:info.activeDelegates][::info.activeDelegates-1],
            key=lambda d: d["votes"],
            reverse=True
        )
    ]

    yearly_share = \
        365 * 24 * info.blockreward * 3600./(info.activeDelegates * blocktime)

    chart = pygal.XY(
        title=u'Public delegates Annual Interest Rate (AIR)',
        legend_at_bottom=True,
        show_legend=False,
        show_x_labels=True,
        show_y_labels=True,
        x_value_formatter=lambda x: "%.2f m%s" % (x/1000000, info.symbol),
        y_value_formatter=lambda y: "%d%%" % y,
        x_label_rotation=20,
        x_title="Delegate vote power",
        y_title="Annual Interest Rate in %",
        style=pygal.style.DefaultStyle(
            label_font_size=15,
            major_label_font_size=15,
            value_label_font_size=15,
            value_font_size=15,
            tooltip_font_size=10,
            legend_font_size=15,
            title_font_size=20
        ),
        human_readable=True
    )

    step = (max_vote-min_vote)/nb_points
    x_lst = [min_vote + i*step for i in range(0, nb_points, 1)]
    chart.x_labels = x_lst[::10]
    chart.add(
        "%d%% sharing delegate AIR in %%" % (share*100),
        [(v, 100.0*share*yearly_share/v) for v in x_lst],
        show_dots=False,
        stroke_style={
            'width': 4, 'linecap': 'round', 'linejoin': 'round'
        }
    )

    if zen.rest.cfg.network == "ark":
        try:
            arkdelegates = _get.api.delegates(
                peer="https://arkdelegates.live", limit=51
            )["data"][:51]
            data = dict(
                [d["name"], d["payout_percent"]] for d in arkdelegates
                if not d["is_private"] and d["payout_percent"] not in [None, 0]
            )
            delegates = [
                dict(d, payout_percent=data[d["username"]]) for d in delegates
                if d["username"] in data
            ]

            for name, votes, _share in [
                (
                    d["username"],
                    float(d["votes"])/100000000.,
                    d["payout_percent"]
                ) for d in delegates if d["username"] != username
            ]:
                chart.add(
                    name,
                    [(votes, _share*yearly_share/votes)],
                    dots_size=3,
                    fill=False,
                    stroke=False,
                    show_legend=False
                )
        except Exception as e:
            zen.logMsg('error occured using arkdelegates.io API : %r' % e)

    if username not in ["", None]:
        forger = zen.loadJson("%s.json" % username)
        try:
            minvote = forger.get("minimum_vote", 0.) * 100000000
            maxvote = forger.get("maximum_vote", None)
            if isinstance(maxvote, (int, float)):
                maxvote *= 100000000
                _max = lambda v, maxi=maxvote: min(maxi, v)
            else:
                _max = lambda v, maxi=maxvote: v
            _min = lambda v, mini=minvote: v if v >= mini else 0

            vote_weights = [
                float(v["balance"]) for v in zen.misc.loadPages(
                    zen.rest.GET.api.delegates.__getattr__(username).voters
                )
            ]
            real_votes = sum(vote_weights) / 100000000
            votes = sum(
                [_min(_max(weight)) for weight in vote_weights]
            )/100000000

            delegate = [
                d for d in delegates
                if d.get("name", d.get("username")) == username
            ][0]
            chart.add(
                username,
                [(
                    real_votes,
                    delegate.get(
                        "payout_percent", share * 100
                    ) * yearly_share / votes
                )],
                dots_size=8,
                fill=True,
            )
        except Exception as e:
            zen.logMsg('error occured trying to put delegate details : %r' % e)

    chart.render_to_file(
        os.path.join(zen.ROOT, "app", "static", "air_%s.svg" % username)
    )
    # return chart.render_data_uri()
