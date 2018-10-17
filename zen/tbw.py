# -*- coding:utf-8 -*-

from collections import OrderedDict

import os
import dposlib
import getpass

import zen
from zen import loadJson, dumpJson, logMsg, getPublicKeyFromUsername


def init(**kwargs):

	if not len(kwargs):
		root = loadJson("root.json")
		delegates = loadJson("delegates.json", root["env"])
		pkeys = [dposlib.core.crypto.getKeys(secret)["publicKey"] for secret in delegates["secrets"]]

		for pkey in pkeys:
			req = dposlib.rest.GET.api.v2.delegates(pkey, peer=zen.API_PEER).get("data", {})
			account = dposlib.rest.GET.api.v2.wallets(pkey, peer=zen.API_PEER).get("data", {})
			account.update(req)
			if account != {}:
				pkey2 = askSecondSecret(account)
				config = loadJson("%s.forger" % pkey, zen.DATA)
				config.update(**{"pubkey":pkey, "#2":pkey2, "excludes":[account["address"]]})
				dumpJson(config, "%s.forger" % pkey, zen.DATA)
				logMsg("%s delegate set" % account["username"])

				webhook = dposlib.rest.POST.api.webhooks(
					peer=zen.WEBHOOK_PEER,
					event="block.forged",
					target="http://209.250.233.136:5000/block/forged",
					conditions=[{"key": "generatorPublicKey", "condition": "eq", "value": pkey}]
				).get("data", False)

				if webhook:
					dumpJson(webhook, "%s.webhook" % pkey, zen.DATA)
					logMsg("%s webhook set" % account["username"])
			else:
				logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))

	elif "username" in kwargs:
		pkey = getPublicKeyFromUsername(kwargs["username"])
		if pkey:
			config = loadJson("%s.forger" % pkey, zen.DATA)
			config.update(**kwargs)
			dumpJson(config, "%s.forger" % pkey, zen.DATA)
			logMsg("%s delegate set" % pkey)
		else:
			logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))

	else:
		tbw = loadJson("tbw.json")
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
	voters = dposlib.rest.GET.api.v2.delegates(pkey, "voters", peer=zen.API_PEER).get("data", [])
	voters = dict([v["address"], float(v["balance"])] for v in voters if v["address"] not in excludes)
	total_balance = sum(voters.values())
	pairs = [[a,b/total_balance*rewards] for a,b in voters.items() if a not in excludes and b > minvote]
	return OrderedDict(sorted(pairs, key=lambda e:e[-1], reverse=True))


def adjust(username, value):
	pkey = getPublicKeyFromUsername(kwargs["username"])
	folder = os.path.join(zen.DATA, pkey)
	if account:
		forgery = loadJson("%s.forgery" % pkey, folder=folder)
		total = sum(forgery.values())
		dumpJson(
			OrderedDict(sorted([[a, v/total*value] for a,v in forgery.items()], key=lambda e:e[-1], reverse=True)),
			"%s.forgery" % pkey,
			folder=folder
		)
	else:
		logMsg("%s username does not exist" % username)
