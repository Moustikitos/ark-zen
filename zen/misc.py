# -*- coding:utf-8 -*-

import os
import zen
import pygal
import datetime
import pygal.style

APPS = {
	"ark-relay": "yarn exec ark relay:start",
	"ark-forger": "yarn exec ark forger:start",
	"zen-srv": "cd ~/ark-zen && pm2 start srv.json -s",
	"zen-chk": "cd ~/ark-zen && pm2 start chk.json -s"
}


def shorten(address, chunk=5):
	return address[:chunk]+"..."+address[-chunk:]


def transactionApplied(id):
	return zen.rest.GET.api.transactions(id).get("data",{}).get("confirmations", 0) >= 10


def regenerateUnapplied(username, filename):
	registry = zen.loadJson("%s.registry" % filename, os.path.join(zen.DATA, username))
	tbw = zen.loadJson("%s.tbw" % filename, os.path.join(zen.TBW, username, "history"))

	for tx in registry.values():
		if not transactionApplied(tx["id"]):
			zen.logMsg('tx %(id)s [%(amount)s --> %(recipientId)s] unapplied' % tx)
		else:
			tbw["weight"].pop(tx["recipientId"], False)
	
	zen.dumpJson(tbw,'%s-unapplied.tbw' % filename, os.path.join(zen.TBW, username))


def loadPages(endpoint, pages=None, quiet=True, nb_tries=10, peer=None, condition=[]):
	if not isinstance(endpoint, zen.rest.EndPoint):
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


def notify(body):
	network = zen.dposlib.core.cfg.network

	pushover = zen.loadJson("pushover.json")
	if pushover != {}:
		pushover["body"] = body
		pushover["network"] = network
		os.system('''
curl -s -F "token=%(token)s" \
	-F "user=%(user)s" \
	-F "title=ark-zen@%(network)s" \
	-F "message=%(body)s" \
	--silent --output /dev/null \
	https://api.pushover.net/1/messages.json
''' % pushover)

	pushbullet = zen.loadJson("pushbullet.json")
	if pushbullet != {}:
		pushbullet["body"] = body
		pushbullet["network"] = network
		os.system('''
curl --header 'Access-Token: %(token)s' \
	--header 'Content-Type: application/json' \
	--data-binary '{"body":"%(body)s","title":"ark-zen@%(network)s","type":"note"}' \
	--request POST \
	--silent --output /dev/null \
	https://api.pushbullet.com/v2/pushes
''' % pushbullet)

	twilio = zen.loadJson("twilio.json")
	if twilio != {}:
		twilio["body"] = body
		os.system('''
curl -X "POST" "https://api.twilio.com/2010-04-01/Accounts/%(sid)s/Messages.json" \
	--data-urlencode "From=%(sender)s" \
	--data-urlencode "Body=%(body)s" \
	--data-urlencode "To=%(receiver)s" \
	--silent --output /dev/null \
	-u "%(sid)s:%(auth)s"
''' % twilio)

	freemobile = zen.loadJson("freemobile.json")
	if freemobile != {}:
		freemobile["msg"] = network + ":\n" + body
		zen.rest.GET.sendmsg(peer="https://smsapi.free-mobile.fr", **freemobile)


def start_pm2_app(appname):
	os.system('''
if echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
    %(pm2_app_cmd)s
else
	echo "(re)starting %(appname)s..."
    pm2 restart %(appname)s -s
fi
''' % {
	"appname": appname,
	"pm2_app_cmd": APPS.get(appname, "echo pm2 cmd line not defined in zen script")
}
)


def stop_pm2_app(appname):
	os.system('''
if ! echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
	echo stoping %(appname)s...
    pm2 stop %(appname)s -s
fi
''' % {"appname": appname}
)


def del_pm2_app(appname):
	os.system('''
if ! echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
	echo deleting %(appname)s...
    pm2 delete %(appname)s -s
fi
''' % {"appname": appname}
)


def chartTimedData(data):

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
	chart.add("block weight % / Ѧ1000 vote", [(d,round(1000*100*v, 3)) for d,v in data])
	return chart.render_data_uri()


def chartAir(share, nb_points=100, username=None):
	info = zen.dposlib.rest.cfg
	_get = zen.dposlib.rest.GET
	try:
		delegates = _get.api.delegates(peer="https://www.arkdelegates.io")["delegates"][:51]
	except:
		delegates = _get.api.delegates()["data"][:51]

	min_vote, max_vote = [int(d.get("voting_power", d.get("votes")))/100000000. for d in sorted(delegates[:info.delegate][::info.delegate-1], key=lambda d:d["rank"], reverse=True)]
	yearly_share = 365 * 24 * info.blockreward * 3600./(info.delegate * info.blocktime)

	chart = pygal.XY(
		title=u'Annual Interest Rate (AIR) for a %d%% sharing delegate' % (share*100),
		legend_at_bottom=True,
		show_legend=False,
		show_x_labels=True,
		show_y_labels=True,
		x_value_formatter=lambda x:"%.3f m%s" % (x/1000000, info.symbol),
		y_value_formatter=lambda y:"%d%%" % y,
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
	x_lst = [min_vote + i*step for i in range(0,nb_points,1)]
	chart.x_labels = x_lst[::10]
	chart.add(
		"%d%% sharing delegate AIR in %%" % (share*100),
		[(v, 100.0*share*yearly_share/v) for v in x_lst],
		show_dots=False,
		stroke_style={'width': 4, 'linecap': 'round', 'linejoin': 'round'}
	)

	try:
		for name, votes, _share in [
			(d["name"], float(d["voting_power"])/100000000., d['payout_percent']) for d in delegates \
			if not d["is_private"] and d["payout_percent"] != None and d["name"] != username
		]:
			chart.add(
				name,
				[(votes, _share*yearly_share/votes)],
				dots_size=3,
				fill=False,
				stroke=False,
				show_legend=False
			)
	except:
		pass

	if username:
		try:
			delegate = [d for d in delegates if d.get("name", d.get("username")) == username][0]
			votes = int(delegate.get("voting_power", delegate.get("votes")))/100000000.
			chart.add(
				username,
				[(votes, delegate.get("payout_percent", share*100)*yearly_share/votes)],
				dots_size=8,
				fill=True,
			)
		except:
			pass

	return chart.render_data_uri()
