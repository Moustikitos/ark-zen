# -*- coding:utf-8 -*-
import os

from collections import OrderedDict

import zen
import pytz
import dposlib
import getpass
import datetime

from dposlib.util.bin import unhexlify
from zen import loadJson, dumpJson, logMsg, loadEnv, getPublicKeyFromUsername


def init(**kwargs):

	# initialize peers from .env file
	if not zen.WEBHOOK_PEER:
		root = loadJson("root.json")
		env = loadEnv(os.path.join(root["env"], ".env"))
		zen.WEBHOOK_PEER = "http://124.0.0.1:%(ARK_WEBHOOKS_PORT)s" % env
		zen.API_PEER = "http://127.0.0.1:%(ARK_API_PORT)s" % env

	# if no options given, initialize forgers set on the node
	if not len(kwargs):
		root = loadJson("root.json")
		# find delegates secrets and generate publicKeys
		delegates = loadJson("delegates.json", os.path.join(root["env"], "config"))
		pkeys = [dposlib.core.crypto.getKeys(secret)["publicKey"] for secret in delegates["secrets"]]

		for pkey in pkeys:
			# for each publicKey, get account data (merge delegate and wallet info)
			req = dposlib.rest.GET.api.v2.delegates(pkey, peer=zen.API_PEER).get("data", {})
			account = dposlib.rest.GET.api.v2.wallets(pkey, peer=zen.API_PEER).get("data", {})
			account.update(req)
			if account != {}:
				logMsg("setting up %s delegate..." % account["username"])
				# ask second secret if any is set
				pkey2 = askSecondSecret(account)
				# load forger configuration and update with minimum data
				config = loadJson("%s.forger" % pkey)
				config.update(**{"pubkey":pkey, "#2":pkey2, "excludes":[account["address"]]})
				dumpJson(config, "%s.forger" % pkey)
				# create a webhook if no one is set
				webhook = loadJson("%s.webhook" % pkey)
				if not webhook.get("token", False):
					webhook = dposlib.rest.POST.api.webhooks(
						peer=zen.WEBHOOK_PEER,
						event="block.forged",
						target="http://127.0.0.1:5000/block/forged",
						conditions=[{"key": "generatorPublicKey", "condition": "eq", "value": pkey}]
					).get("data", False)
					if webhook:
						dumpJson(webhook, "%s.webhook" % pkey)
						logMsg("%s webhook set" % account["username"])
				else:
					logMsg("webhook already set for delegate %s" % account["username"])	
				logMsg("%s delegate set" % account["username"])
			else:
				logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))

	elif "username" in kwargs:
		username = kwargs.pop("username")
		pkey = getPublicKeyFromUsername(username)
		if pkey:
			config = loadJson("%s.forger" % pkey)
			config.update(**kwargs)
			dumpJson(config, "%s.forger" % pkey)
			logMsg("%s delegate set" % username)
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
				secret = getpass.getpass("> enter %s second secret: " % account["username"])
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
	if pkey:
		folder = os.path.join(zen.DATA, pkey)
		forgery = loadJson("%s.forgery" % pkey, folder=folder)
		total = sum(forgery.values())
		dumpJson(
			OrderedDict(sorted([[a, v/total*value] for a,v in forgery.items()], key=lambda e:e[-1], reverse=True)),
			"%s.forgery" % pkey,
			folder=folder
		)
	else:
		logMsg("%s username does not exist" % username)


def extract(username):
	now = datetime.datetime.now(tz=pytz.UTC)
	pkey = getPublicKeyFromUsername(username)

	if pkey:
		forgery = loadJson("%s.forgery" % pkey, os.path.join(zen.DATA, pkey))
		param = loadJson("%s.forger" % pkey)

		threshold = param.get("threshold", 0.)
		data = OrderedDict(sorted([[a,w] for a,w in forgery.get("rewards", {}).items()], key=lambda e:e[-1], reverse=True))
		tbw = OrderedDict([a,w] for a,w in data.items() if w >= threshold)

		amount = sum(tbw.values())
		dumpJson(
			{
				"timestamp": "%s" % now,
				"undistributed": sum(w for w in data.values() if w < threshold),
				"distributed": param.get("share", 1.0)*amount,
				"fees": forgery.get("fees", 0.),
				"weight": OrderedDict(sorted([[a,w/amount] for a,w in tbw.items()], key=lambda e:e[-1], reverse=True))
			},
			"%s.tbw" % now.strftime("%Y-%m-%d"),
			folder=os.path.join(zen.ROOT, "app", ".tbw", pkey)
		)

		forgery["rewards"] = OrderedDict([a, 0. if a in tbw else w] for a,w in data.items())
		forgery["fees"] = 0.
		dumpJson(forgery, "%s.forgery" % pkey, os.path.join(zen.DATA, pkey))


def dumpRegistry(username):
	root = loadJson("root.json")

	pkey = getPublicKeyFromUsername(username)
	delegates = loadJson("delegates.json", os.path.join(root["env"], "config"))
	for secret in delegates["secrets"]:
		keys = dposlib.core.crypto.getKeys(secret)
		if keys["publicKey"] == pkey: break
		else: keys = False
	
	if keys:

		config = loadJson("%s.forger" % pkey)
		folder = os.path.join(zen.ROOT, "app", ".tbw", pkey)
		if config.get("#2", None):
			secondPrivateKey = dposlib.core.crypto.getKeys(None, seed=dposlib.core.crypto.unhexlify(config["#2"]))["privateKey"]
		else:
			secondPrivateKey = None

		for name in [n for n in os.listdir(folder) if n.endswith(".tbw")]:
			tbw = loadJson(name, folder)
			amount = tbw["distributed"]

			dposlib.core.Transaction.link(keys["privateKey"], secondPrivateKey)
			registry = OrderedDict()
			for address, weight in sorted(tbw["weight"].items(), key=lambda e:e[-1], reverse=True):
				transaction = dposlib.core.transfer(
					amount*weight, address,
					config.get("vendorField", "%s reward" % "username")
				)
				transaction.finalize(fee_included=True)
				registry[transaction["id"]] = transaction

			dumpJson(registry, "%s.registry" % name, os.path.join(zen.DATA, pkey))
			dposlib.core.Transaction.unlink()

			dumpJson(tbw, name, os.path.join(folder, "history"))
			os.remove(os.path.join(folder, name))
