# -*- coding:utf-8 -*-

from collections import OrderedDict

import os
import dposlib
import getpass

from zen import JSON, DATA, LOG
from zen import loadJson, dumpJson, logMsg, getPeer

import requests


def init(**kwargs):
	tbw = loadJson("tbw.json")
	# get a most valid peer
	_peer = getPeer()

	# by default, initialize forgers
	if not len(kwargs):
		root = loadJson("root.json")
		delegates = loadJson("delegates.json", root["env"])
		forgers = {}
		pkeys = [dposlib.core.crypto.getKeys(secret)["publicKey"] for secret in delegates["secrets"]]
		for pkey in pkeys:
			req = dposlib.rest.GET.api.delegates.get(peer=_peer, publicKey=pkey)
			account = req.get("delegate", {})
			if account != {}:
				pkey2 = askSecondSecret(account)
				forgers[account["username"]] = {"pubkey":pkey, "#2":pkey2, "excludes":[account["address"]]}
				logMsg("%s delegate set" % account["username"])
			else:
				logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))

			webhook = rest.POST.api.webhooks(
				peer="http://127.0.0.1:4004",
				event="block.forged",
				target="http://209.250.233.136:5000/block/forged",
				condition={"key": "generatorPublicKey", "condition": "eq", "value": pkey}
			).json().get("data", False)
			if webhook:
				if "webhhoks" in tbw:
					if pkey not in tbw["webhooks"]:
						tbw["webhooks"][pkey] = webhook
				else:
					tbw["webhooks"] = {pkey:webhook}

		tbw["forgers"] = forgers

	# else store data in tbw config file
	else:
		tbw.update(**kwargs)

	dumpJson(tbw, "tbw.json")


def askSecondSecret(account):
	if account.get("secondPublicKey", False):
		seed = "01"
		secondPublicKey = dposlib.core.crypto.getKeys(None, seed=dposlib.core.crypto.unhexlify(seed))["publicKey"]
		while secondPublicKey != account["secondPublicKey"]:
			try:
				secret = getpass.getpass("> enter your second secret: ")
				seed = dposlib.core.crypto.hashlib.sha256(secret.encode("utf8") if not isinstance(secret, bytes) else secret).digest()
				secondPublicKey = dposlib.core.crypto.getKeys(None, seed=seed)["publicKey"]
				return dposlib.core.crypto.hexlify(seed)
			except KeyboardInterrupt:
				break


def distributeRewards(rewards, pkey, minvote=0, excludes=[]):
	voters = dposlib.rest.GET.api.delegates.voters(peer=getPeer(), publicKey=pkey).get("accounts", [])
	voters = dict([v["address"], float(v["balance"])] for v in voters if v["address"] not in excludes)
	total_balance = sum(voters.values())
	pairs = [[a,b/total_balance*rewards] for a,b in voters.items() if a not in excludes and b > minvote]
	return OrderedDict(sorted(pairs, key=lambda e:e[-1], reverse=True))


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

