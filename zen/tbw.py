# -*- coding:utf-8 -*-

from collections import OrderedDict

import os
import getpass
import datetime

from zen import DATA, LOG
from zen import loadJson, dumpJson, logMsg, restGet
from zen import crypto

import pytz

NAME = os.path.splitext(os.path.basename(__file__))[0]


def init(**kwargs):
	tbw = loadJson("%s.json" % NAME)

	if not len(kwargs):
		root = loadJson("root.json")
		delegates = loadJson("delegates.json", root["env"])
		forgers = {}
		pkeys = [crypto.getKeys(secret)["publicKey"] for secret in delegates["secrets"]]
		for pkey in pkeys:
			req = restGet("api", "delegates", "get", publicKey=pkey)
			if req.get("success", False):
				account = req.get("delegate", {})
				pkey2 = askSecondSecret(account)
				forgers[account["username"]] = {"pubkey":pkey, "#2":pkey2, "excludes":[account["address"]]}
				logMsg("%s delegate set" % account["username"])
			else:
				logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))

		tbw["forgers"] = forgers
	else:
		tbw.update(**kwargs)

	dumpJson(tbw, "%s.json" % NAME)


def askSecondSecret(account):
	if account.get("secondPublicKey", False):
		seed = "01"
		secondPublicKey = crypto.getKeys(None, seed=crypto.unhexlify(seed))["publicKey"]
		while secondPublicKey != account["secondPublicKey"]:
			try:
				secret = getpass.getpass("> enter your second secret: ")
				seed = crypto.hashlib.sha256(secret.encode("utf8") if not isinstance(secret, bytes) else secret).digest()
				secondPublicKey = crypto.getKeys(None, seed=seed)["publicKey"]
				return crypto.hexlify(seed)
			except KeyboardInterrupt:
				break


def getRewards(pkey):
	previous_forge = loadJson("%s.forge" % pkey, DATA)
	forge = restGet("api", "delegates", "forging", "getForgedByAccount", generatorPublicKey=pkey)
	if not len(forge):
		rewards = 0
	else:
		rewards = (int(forge["rewards"]) - int(previous_forge.get("rewards", 0)))/100000000.
	dumpJson(forge, "%s.forge" % pkey, DATA)
	return rewards


def distributeRewards(pkey, minvote=0, excludes=[]):
	rewards = getRewards(pkey)
	if rewards > 0:
		voters = restGet("api", "delegates", "voters", publicKey=pkey).get("accounts", [])
		voters = dict([v["address"], float(v["balance"])] for v in voters if v["address"] not in excludes)
		total_balance = sum(voters.values())
		pairs = [[a,b/total_balance*rewards] for a,b in voters.items() if a not in excludes and b > minvote]
		return OrderedDict(sorted(pairs, key=lambda e:e[-1], reverse=True))
	return OrderedDict()


def adjust(username, value):
	tbw = loadJson("tbw.json")

	forger = tbw["forgers"].get(username, {})
	if forger != {}:
		forgery = loadJson("%s.forgery" % forger["pubkey"], DATA)
		total = sum(forgery.values())
		dumpJson(
			OrderedDict(sorted([[a, v/total*value] for a,v in forgery.items()], key=lambda e:e[-1], reverse=True)),
			"%s.forgery" % forger["pubkey"], DATA
		)
	else:
		logMsg("%s username does not exist" % username)


def configure(username, **kwargs):
	tbw = loadJson("tbw.json")
	try:
		forger = tbw["forgers"][username].update(**kwargs)
	except KeyError:
		logMsg("%s username does not exist" % username)
	dumpJson(tbw, "tbw.json")


def initializeRewards():
	tbw = loadJson("tbw.json")	
	pkeys = [forger["pubkey"] for forger in tbw.get("forgers", {}).values()]
	for pkey in pkeys:
		yield (pkey, getRewards(pkey))


def spread():
	tbw = loadJson("tbw.json")

	for forger in tbw.get("forgers", {}).values():
		forgery = loadJson("%s.forgery" % forger["pubkey"], DATA)
		rewards = distributeRewards(
			forger["pubkey"],
			minvote=forger.get("minvote", 0),
			excludes=forger.get("excludes", [])
		)

		if len(rewards):
			logname = os.path.join(LOG, "%s.log" % forger["pubkey"])
			voters = list(rewards.keys())
			cowards = set(forgery.keys()) - set(voters)
			if len(cowards):
				logMsg("down-voted by : %s" % ", ".join(cowards), logname=logname)
			newcomers = set(voters) - set(forgery.keys())
			if len(newcomers):
				logMsg("up-voted by : %s" % ", ".join(newcomers), logname=logname)
			dumpJson(
				OrderedDict(sorted([[a, forgery.get(a, 0.)+rewards[a]] for a in rewards.keys()], key=lambda e:e[-1], reverse=True)),
				"%s.forgery" % forger["pubkey"], DATA
			)


def extract():
	tbw = loadJson("tbw.json")

	for forger in tbw.get("forgers", {}).values():
		forgery = loadJson("%s.forgery" % forger["pubkey"], DATA)
		data = OrderedDict(sorted([[a,w] for a,w in forgery.items()], key=lambda e:e[-1], reverse=True))
		threshold = forger.get("threshold", 0.)

		dist = OrderedDict([a,w] for a,w in data.items() if w >= threshold)
		amount = sum(dist.values())
		saved = sum(w for w in data.values() if w < threshold)

		now = datetime.datetime.now(tz=pytz.UTC)
		dumpJson(
			{
				"timestamp": "%s" % now,
				"saved": saved,
				"amount": forger.get("share", 1.0)*amount,
				"weight": OrderedDict(sorted([[a,w/amount] for a,w in data.items()], key=lambda e:e[-1], reverse=True))
			},
			"%s.%s.tbw" % (forger["pubkey"], now.strftime("%Y-%m-%d")),
			DATA
		)
		dumpJson(OrderedDict([a, 0. if a in dist else w] for a,w in forgery.items()), "%s.forgery" % forger["pubkey"], DATA)


def forgery():
	pass
