# -*- encoding:utf-8 -*-

import os
import json
import flask

from collections import OrderedDict

import zen
from zen import loadJson, dumpJson, tbw


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
@app.route("/block/forged", methods=["POST"])
def spread():

	if flask.request.method == "POST":

		block = json.loads(flask.request.data).get("data", False)
		if not block:
			raise Exception("Error: can not read data")
		else:
			generatorPublicKey = block["generatorPublicKey"]

		# load previous forged block and save last forged 
		filename = "%s.last.block" % generatorPublicKey
		folder = os.path.join(zen.DATA, generatorPublicKey)
		last_block = loadJson(filename, folder=folder)
		dumpJson(block, filename, folder=folder)
		if last_block.get("id", None) == block["id"]:
			raise Exception("No new block created")

		# check autorization and exit if bad one
		webhook = loadJson("%s.webhook" % generatorPublicKey)
		if not webhook["token"].startswith(flask.request.headers["Authorization"]):
			raise Exception("Not autorized here")

		# find forger information using generatorPublicKey
		forger = loadJson("%s.forger" % generatorPublicKey)
		forgery = loadJson("%s.forgery" % generatorPublicKey, folder=folder)

		# compute the reward distribution
		rewards = tbw.distributeRewards(
			float(block["reward"])/100000000.,
			generatorPublicKey,
			minvote=forger.get("minvote", 0),
			excludes=forger.get("excludes", [])
		)

		# dump true block weight data
		_rwds = forgery.get("rewards", {})
		dumpJson(
			{
				"fees": forgery.get("fees", 0.) + float(block["totalFee"])/100000000.,
				"rewards": OrderedDict(sorted([[a, _rwds.get(a, 0.)+rewards[a]] for a in rewards.keys()], key=lambda e:e[-1], reverse=True))
			},
			"%s.forgery" % generatorPublicKey,
			folder=folder
		)

	return ""
