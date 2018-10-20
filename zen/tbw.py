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
				username = account["username"]
				logMsg("setting up %s delegate..." % username)
				# ask second secret if any is set
				privkey2 = askSecondSecret(account)
				# load forger configuration and update with minimum data
				config = loadJson("%s.json" % username)
				config.update(**{"pubicKey":pkey, "#2":privkey2, "excludes":[account["address"]]})
				dumpJson(config, "%s.json" % username)
				# create a webhook if no one is set
				webhook = loadJson("%s-webhook.json" % username)
				if not webhook.get("token", False):
					webhook = dposlib.rest.POST.api.webhooks(
						peer=zen.WEBHOOK_PEER,
						event="block.forged",
						target="http://127.0.0.1:5000/block/forged",
						conditions=[{"key": "generatorPublicKey", "condition": "eq", "value": pkey}]
					).get("data", False)
					if webhook:
						dumpJson(webhook, "%s-webhook.json" % username)
						logMsg("%s webhook set" % username)
				else:
					logMsg("webhook already set for delegate %s" % username)	
				logMsg("%s delegate set" % username)
			else:
				logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))

	elif "username" in kwargs:
		username = kwargs.pop("username")
		if getPublicKeyFromUsername(username):
			config = loadJson("%s.json" % username)
			config.update(**kwargs)
			dumpJson(config, "%s.json" % username)
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
	if getPublicKeyFromUsername(username):
		folder = os.path.join(zen.DATA, username)
		forgery = loadJson("%s.forgery" % username, folder=folder)
		total = sum(forgery.values())
		dumpJson(
			{
				"fees": forgery.get("fees", 0.),
				"blocks": forgery.get("blocks", 0),
				"contribution": OrderedDict(sorted([[a, v/total*value] for a,v in forgery.items()], key=lambda e:e[-1], reverse=True))
			},
			"%s.forgery" % username,
			folder=folder
		)
	else:
		logMsg("%s username does not exist" % username)


def extract(username):
	now = datetime.datetime.now(tz=pytz.UTC)

	if getPublicKeyFromUsername(username):
		param = loadJson("%s.json" % username)
		threshold = param.get("threshold", 0.2)
		share =  param.get("share", 1.0)

		forgery = loadJson("%s.forgery" % username, os.path.join(zen.DATA, username))
		data = OrderedDict(sorted([[a,w] for a,w in forgery.get("contribution", {}).items()], key=lambda e:e[-1], reverse=True))
		tbw = OrderedDict([a,w*share] for a,w in data.items() if w >= threshold)
		totalContribution = sum(data.values())

		dumpJson(
			{
				"timestamp": "%s" % now,
				"delegate-share": totalContribution * (1.0-param.get("share", 1.0)),
				"undistributed": sum(w for w in data.values() if w < threshold),
				"distributed": sum(tbw.values()),
				"fees": forgery.get("fees", 0.),
				"weight": OrderedDict(sorted([[a,w/totalContribution] for a,w in tbw.items()], key=lambda e:e[-1], reverse=True))
			},
			"%s.tbw" % now.strftime("%Y-%m-%d"),
			folder=os.path.join(zen.ROOT, "app", ".tbw", username)
		)

		forgery["contribution"] = OrderedDict([a, 0. if a in tbw else w] for a,w in data.items())
		forgery["blocks"] = 0
		forgery["fees"] = 0.
		dumpJson(forgery, "%s.forgery" % username, os.path.join(zen.DATA, username))


def dumpRegistry(username):
	root = loadJson("root.json")

	pkey = getPublicKeyFromUsername(username)
	delegates = loadJson("delegates.json", os.path.join(root["env"], "config"))
	for secret in delegates["secrets"]:
		keys = dposlib.core.crypto.getKeys(secret)
		if keys["publicKey"] == pkey: break
		else: keys = False
	
	if keys:

		config = loadJson("%s.json" % username)
		folder = os.path.join(zen.ROOT, "app", ".tbw", username)
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
					config.get("vendorField", "%s reward" % username)
				)
				transaction.finalize(fee_included=True)
				registry[transaction["id"]] = transaction

			if config.get("funds", False):
				transaction = dposlib.core.transfer(tbw["delegate-share"] + tbw["fees"], config["funds"], "%s share" % username)
				transaction.finalize(fee_included=True)
				registry[transaction["id"]] = transaction

			dumpJson(registry, "%s.registry" % name, os.path.join(zen.DATA, username))
			dposlib.core.Transaction.unlink()

			dumpJson(tbw, name, os.path.join(folder, "history"))
			os.remove(os.path.join(folder, name))


def broadcast(username):

	pass

	