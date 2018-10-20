# -*- encoding:utf-8 -*-

import os
import json
import flask
import dposlib

from collections import OrderedDict

import zen
import zen.tbw
from zen import loadJson, dumpJson, generatorPublicKey


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

		# compute the reward distribution
		contributions = zen.tbw.distributeRewards(
			float(block["reward"])/100000000.,
			generatorPublicKey,
			minvote=forger.get("minvote", 0),
			excludes=forger.get("excludes", [])
		)

		# dump true block weight data
		_ctrb = forgery.get("contribution", {})
		dumpJson(
			{
				"fees": forgery.get("fees", 0.) + float(block["totalFee"])/100000000.,
				"blocks": forgery.get("blocks", 0) + 1,
				"contribution": OrderedDict(sorted([[a, _ctrb.get(a, 0.)+contributions[a]] for a in contributions.keys()], key=lambda e:e[-1], reverse=True))
			},
			"%s.forgery" % username,
			folder=folder
		)

	return ""

	# else:

	# 	root = loadJson("root.json")
	# 	# find delegates secrets and generate publicKeys
	# 	delegates = loadJson("delegates.json", os.path.join(root["env"], "config"))
	# 	pkeys = [dposlib.core.crypto.getKeys(secret)["publicKey"] for secret in delegates["secrets"]]

	# 	result = ""
	# 	for pkey in pkeys:
	# 		result += "%s<br>" % pkey
	# 		result += "<br>".join(json.dumps(loadJson("%s.forgery" % pkey, folder=os.path.join(zen.DATA, pkey)), indent=2).split("\n"))

	# 	return result
