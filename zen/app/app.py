# -*- encoding:utf-8 -*-

import os
import flask

from zen import ROOT, DATA, LOG
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

	tbw_data = loadJson("tbw.json")

	data = flask.requests.data
	webhook = tbw_data["webhook"][data.generatorPublicKey]
	if not webhook["token"].endswith(request.headers.autorization):
		return

	forger = tbw_data["forgers"][data.generatorPublicKey]
	forgery = loadJson("%s.forgery" % forger["pubkey"], DATA)

	rewards = tbw.distributeRewards(
		data.rewards,
		data.generatorPublicKey,
		minvote=forger.get("minvote", 0),
		excludes=forger.get("excludes", [])
	)

	# logname = os.path.join(LOG, "%s.log" % forger["pubkey"])

	# voters = list(rewards.keys())
	# cowards = set(forgery.keys()) - set(voters)
	# if len(cowards):
	# 	logMsg("down-voted by : %s" % ", ".join(cowards), logname=logname)

	# newcomers = set(voters) - set(forgery.keys())
	# if len(newcomers):
	# 	logMsg("up-voted by : %s" % ", ".join(newcomers), logname=logname)

	dumpJson(
		OrderedDict(sorted([[a, forgery.get(a, 0.)+rewards[a]] for a in rewards.keys()], key=lambda e:e[-1], reverse=True)),
		"%s.forgery" % forger["pubkey"], DATA
	)
