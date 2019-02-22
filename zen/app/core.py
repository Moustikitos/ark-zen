# -*- encoding:utf-8 -*-
import os
import math
import json
import flask
import dposlib

from collections import OrderedDict

import zen
import zen.tbw
import zen.misc
from dposlib import rest
from zen import logMsg, loadJson, dumpJson, getUsernameFromPublicKey


# create the application instance 
app = flask.Flask(__name__)
app.config.update(
	# 300 seconds = 5 minutes lifetime session
	PERMANENT_SESSION_LIFETIME = 300,
	# used to encrypt cookies
	# secret key is generated each time app is restarted
	SECRET_KEY = os.urandom(24),
	# JS can't access cookies
	SESSION_COOKIE_HTTPONLY = True,
	# bi use of https
	SESSION_COOKIE_SECURE = False,
	# update cookies on each request
	# cookie are outdated after PERMANENT_SESSION_LIFETIME seconds of idle
	SESSION_REFRESH_EACH_REQUEST = True,
	# 
	TEMPLATES_AUTO_RELOAD = True
)


@app.route("/block/missed", methods=["POST", "GET"])
def check():
	if flask.request.method == "POST":
		data = json.loads(flask.request.data).get("data", False)
		logMsg("missing block :\n%s" % json.dumps(data, indent=2))
		zen.misc.notify("missed a block !\n%s" % json.dumps(data, indent=2))
	return json.dumps({"zen-tbw::block/missed":True}, indent=2)


# compute true block weight
@app.route("/block/forged", methods=["POST", "GET"])
def spread():

	if flask.request.method == "POST":

		block = json.loads(flask.request.data).get("data", False)
		if not block:
			raise Exception("Error: can not read data")
		else:
			generatorPublicKey = block["generatorPublicKey"]
		username = getUsernameFromPublicKey(generatorPublicKey)
		if not username:
			raise Exception("Error: can not reach username")
		
		# check autorization and exit if bad one
		webhook = loadJson("%s-webhook.json" % username)
		if not webhook["token"].startswith(flask.request.headers["Authorization"]):
			raise Exception("not autorized here")

		# at start there is no *.last.block file so must check first 
		filename = "%s.last.block" % username
		folder = os.path.join(zen.DATA, username)
		last_block = loadJson(filename, folder=folder)
		# Because sometime network is not in good health, the spread function
		# can exit with exception. So compare the ids of last forged blocks
		# to compute rewards and fees... 
		rewards = fees = 0.
		blocks = 0
		if last_block.get("id", False):
			# get last forged block from blockchain
			req = rest.GET.api.v2.delegates(generatorPublicKey, "blocks")
			if req.get("error", False):
				# dposlib.core.rotate_peers()
				raise Exception("Api error : %r" % req)
			# compute fees, blocs and rewards from the last saved block
			last_blocks = req.get("data", {})
			logMsg("%s forged %s, last known forged: %s" % (username, block["id"], last_block["id"]))
			for blk in last_blocks:
				# if bc is not synch and response is too bad, also check timestamp
				if blk["id"] == last_block["id"] or blk["timestamp"]["epoch"] < last_block["timestamp"]:
					break
				else:
					logMsg("    getting rewards and fees from block %s..." % blk["id"])
					rewards += float(blk["forged"]["reward"])/100000000.
					fees += float(blk["forged"]["fee"])/100000000.
					blocks += 1
		else:
			dumpJson(block, filename, folder=folder)
			raise Exception("first iteration for %s" % username)

		# find forger information using username
		forger = loadJson("%s.json" % username)
		forgery = loadJson("%s.forgery" % username, folder=folder)

		# compute the reward distribution excluding delegate
		address = dposlib.core.crypto.getAddress(generatorPublicKey)
		excludes = forger.get("excludes", [address])
		if address not in excludes:
			excludes.append(address)
		contributions = zen.tbw.distributeRewards(
			rewards,
			username,
			minvote=forger.get("minimum_vote", 0),
			excludes=excludes
		)
		# from here, all blochain call are finished so
		# dump the last block forged provided by webhook
		dumpJson(block, filename, folder=folder)

		# dump true block weight data
		_ctrb = forgery.get("contributions", {})
		dumpJson(
			{
				"fees": forgery.get("fees", 0.) + fees,
				"blocks": forgery.get("blocks", 0) + blocks,
				"contributions": OrderedDict(sorted([[a, _ctrb.get(a, 0.)+contributions[a]] for a in contributions], key=lambda e:e[-1], reverse=True))
			},
			"%s.forgery" % username,
			folder=folder
		)

		msg = "\n".join(
			["%s downvoted %s [%.8f Arks]" % (zen.misc.shorten(wallet), username, _ctrb[wallet]) for wallet in [w for w in _ctrb if w not in contributions]] + \
			["%s upvoted %s" % (zen.misc.shorten(wallet), username) for wallet in [w for w in contributions if w not in _ctrb]]
		)
		logMsg("checking vote changes..." + msg)
		# notify vote movements
		if msg != "": zen.misc.notify(msg)

		# launch payroll if block delay reach
		block_delay = forger.get("block_delay", False)
		if block_delay:
			test = forgery.get("blocks", 0) + blocks
			if test >= block_delay:
				logMsg("%s payroll triggered by block delay : %s [>= %s]" % (username, test, block_delay))
				zen.tbw.extract(username)
				zen.tbw.dumpRegistry(username)
				zen.tbw.broadcast(username)

	return json.dumps({"zen-tbw::block/forged":True}, indent=2)


@app.context_processor
def tweak():
	tbw_config = zen.loadJson("tbw.json")
	token = tbw_config.get("currency", "t")
	return dict(
		url_for=dated_url_for,
		tbw_config=tbw_config,
		_currency=lambda value: flask.Markup("%.8f&nbsp;%s" % (value, token)),
		_dhm = lambda value: "%d days %02d hours %02d minutes" % dhm(value),
		_address=lambda address: flask.Markup(
			'<span class="not-ellipsed">%s</span><span class="ellipsed">%s</span>' % 
			(address, "%s&nbsp;&#x2026;&nbsp;%s" % (address[:5],address[-5:])))
	)


def dhm(last_blocks):
	days = last_blocks * zen.rest.cfg.blocktime * zen.rest.cfg.delegate / (3600.*24)
	hours = (days - math.floor(days)) * 24
	minutes = (hours - math.floor(hours)) * 60
	return math.floor(days), math.floor(hours), math.floor(minutes)


########################
# css reload bugfix... #
########################
def dated_url_for(endpoint, **values):
	if endpoint == 'static':
		filename = values.get("filename", False)
		if filename:
			file_path = os.path.join(app.root_path, endpoint, filename)
			values["q"] = int(os.stat(file_path).st_mtime)
	return flask.url_for(endpoint, **values)
########################
