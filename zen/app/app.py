# -*- encoding:utf-8 -*-

import os
import json
import flask
import dposlib

from collections import OrderedDict

import zen
import zen.tbw
from zen import loadJson, dumpJson, getUsernameFromPublicKey


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
	SESSION_REFRESH_EACH_REQUEST = True
)


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
		if not username: return ""
		
		# load previous forged block and save last forged 
		filename = "%s.last.block" % username
		folder = os.path.join(zen.DATA, username)
		last_block = loadJson(filename, folder=folder)
		dumpJson(block, filename, folder=folder)
		if last_block.get("id", None) == block["id"]:
			raise Exception("No new block created")

		# check autorization and exit if bad one
		webhook = loadJson("%s-webhook.json" % username)
		if not webhook["token"].startswith(flask.request.headers["Authorization"]):
			raise Exception("Not autorized here")

		# find forger information using username
		forger = loadJson("%s.json" % username)
		forgery = loadJson("%s.forgery" % username, folder=folder)

		# compute the reward distribution excluding delegate
		address = dposlib.core.crypto.getAddress(generatorPublicKey)
		excludes = forger.get("excludes", [address])
		if address not in excludes:
			excludes.append(address)
		contributions = zen.tbw.distributeRewards(
			float(block["reward"])/100000000.,
			generatorPublicKey,
			minvote=forger.get("minvote", 0),
			excludes=excludes
		)

		# dump true block weight data
		_ctrb = forgery.get("contributions", {})
		dumpJson(
			{
				"fees": forgery.get("fees", 0.) + float(block["totalFee"])/100000000.,
				"blocks": forgery.get("blocks", 0) + 1,
				"contributions": OrderedDict(sorted([[a, _ctrb.get(a, 0.)+contributions[a]] for a in contributions.keys()], key=lambda e:e[-1], reverse=True))
			},
			"%s.forgery" % username,
			folder=folder
		)

		# launch payroll if block delay reach
		block_delay = forger.get("block_delay", False)
		if block_delay:
			if (forgery.get("blocks", 0) + 1) >= block_delay:
				zen.tbw.extract(username)
				zen.tbw.dumpRegistry(username)
				zen.tbw.broadcast(username)

	return "<h1>Zen True Block Weight is running</h1>"
