# -*- coding:utf-8 -*-
import os
import sys
import time
import json
import sqlite3
import getpass
import datetime

from collections import OrderedDict

import zen
import pytz
import dposlib

from dposlib import rest
from dposlib.blockchain import slots
from dposlib.util.bin import unhexlify
from zen import loadJson, dumpJson, logMsg, getPublicKeyFromUsername
from zen import misc


def initDb(username):
	sqlite = sqlite3.connect(os.path.join(zen.ROOT, "%s.db" % username))
	sqlite.row_factory = sqlite3.Row
	cursor = sqlite.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS transactions(filename TEXT, timestamp INTEGER, amount INTEGER, address TEXT, id TEXT);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS tx_index ON transactions(id);")
	sqlite.commit()
	return sqlite


def rebuildDb(username):
	sqlite = initDb(username)
	cursor = sqlite.cursor()

	account = rest.GET.api.v2.delegates(username, returnKey="data")
	address =  account.get("address", False)
	if address:

		# transactions = []
		count, pageCount = 0, 1
		while count < pageCount:
			req = rest.GET.api.v2.wallets(address, "transactions", page=count+1)
			if req.get("error", False):
				raise Exception("Api error occured: %r" % req)
			pageCount = req["meta"]["pageCount"]
			logMsg("reading transaction page %s over %s" % (count+1, pageCount))
	
			cursor.executemany(
				"INSERT OR REPLACE INTO transactions(filename, timestamp, amount, address, id) VALUES(?,?,?,?,?);",
				[(
					slots.getRealTime(tx["timestamp"]["epoch"]).strftime("%Y%m%d-%H%M"),
					tx["timestamp"]["epoch"],
					tx["amount"]/100000000.,
					tx.get("recipient", ""),
					tx["id"]
				) for tx in req.get("data", []) if tx.get("type", 100) == 0 and tx.get("vendorField", "") != "" and tx.get("sender", "") == address]
			)

			count += 1
			sqlite.commit()

	sqlite.close()


def printNewLine():
	sys.stdout.write("\n")
	sys.stdout.flush()


def init(**kwargs):
	webhook_peer = kwargs.get("webhook_peer", zen.WEBHOOK_PEER)

	# if no options given, initialize forgers set on the node
	if not len(kwargs):
		root = loadJson("root.json")
		# find delegates secrets and generate publicKeys
		env_folder = os.path.dirname(root["env"])
		if os.path.exists(os.path.join(env_folder, "delegates.json")):
			# ark core v2.1.x
			delegates = loadJson("delegates.json", env_folder)
		else:
			# ark core v2.0.x
			delegates = loadJson("delegates.json", os.path.join(env_folder, "config"))
		pkeys = [dposlib.core.crypto.getKeys(secret)["publicKey"] for secret in delegates["secrets"]]

		for pkey in set(pkeys):
			setDelegate(pkey, webhook_peer, webhook_peer != zen.WEBHOOK_PEER)

	elif "usernames" in kwargs:
		pkeys = []
		for username in kwargs.pop("usernames", []):
			req = rest.GET.api.v2.delegates(username).get("data", {})
			if len(req):
				pkeys.append(req["publicKey"])

		for pkey in pkeys:
			account = setDelegate(pkey, webhook_peer, webhook_peer != zen.WEBHOOK_PEER)
			if account:
				config = loadJson("%s.json" % account["username"])
				config["#1"] = askSecret(account)
				config.update(**kwargs)
				dumpJson(config, "%s.json" % account["username"])

	elif "username" in kwargs:
		username = kwargs.pop("username")
		if getPublicKeyFromUsername(username):
			config = loadJson("%s.json" % username)
			config.update(**kwargs)
			if not(config.get("fee_level", True)):
				config.pop("fee_level", None)
				logMsg("Dynamic fees disabled")
			dumpJson(config, "%s.json" % username)
			logMsg("%s delegate set" % username)
		else:
			logMsg("can not find delegate %s" % username)

	else:
		tbw = loadJson("tbw.json")
		for key in [k for k in ["target_delegate", "fee_coverage"] if k in kwargs]:
			value = kwargs.pop(key)
			if value:
				if key in tbw:
					tbw.pop(key)
					logMsg("%s disabled" % key)
				else:
					tbw[key] = value
					logMsg("%s enabled" % key)
		tbw.update(**kwargs)			
		dumpJson(tbw, "tbw.json")


def setDelegate(pkey, webhook_peer, public=False):
	printNewLine()
	# for each publicKey, get account data (merge delegate and wallet info)
	req = rest.GET.api.v2.delegates(pkey).get("data", {})
	account = rest.GET.api.v2.wallets(pkey).get("data", {})
	account.update(req)

	if account != {}:
		username = account["username"]
		logMsg("setting up %s delegate..." % username)
		# load forger configuration and update with minimum data
		config = loadJson("%s.json" % username)
		config.update(**{"publicKey":pkey, "#2":askSecondSecret(account)})
		dumpJson(config, "%s.json" % username)
		# create a webhook if no one is set
		webhook = loadJson("%s-webhook.json" % username)
		if not webhook.get("token", False):
			print(webhook_peer, "http://%s:5000/block/forged" % (zen.PUBLIC_IP if public else "127.0.0.1"))
			data = rest.POST.api.webhooks(
				peer=webhook_peer,
				event="block.forged",
				target="http://%s:5000/block/forged" % (zen.PUBLIC_IP if public else "127.0.0.1"),
				conditions=[{"key": "generatorPublicKey", "condition": "eq", "value": pkey}]
			)
			webhook = data.get("data", False)
			if webhook:
				webhook["peer"] = webhook_peer
				dumpJson(webhook, "%s-webhook.json" % username)
				logMsg("%s webhook set" % username)
			else:
				logMsg("error occur on webhook creation:\n%s" % data)
		else:
			logMsg("webhook already set for delegate %s" % username)	
		logMsg("%s delegate set" % username)
		return account
	else:
		logMsg("%s: %s" % (req.get("error", "API Error"), req.get("message", "...")))


def askSecret(account):
	seed = "01"
	publicKey = dposlib.core.crypto.getKeys(None, seed=dposlib.core.crypto.unhexlify(seed))["publicKey"]
	while publicKey != account["publicKey"]:
		try:
			secret = getpass.getpass("> enter %s secret: " % account["username"])
			seed = dposlib.core.crypto.hashlib.sha256(secret.encode("utf8") if not isinstance(secret, bytes) else secret).digest()
			publicKey = dposlib.core.crypto.getKeys(None, seed=seed)["publicKey"]
		except KeyboardInterrupt:
			printNewLine()
			logMsg("delegate configuration skipped")
			sys.exit(1)
	return dposlib.core.crypto.hexlify(seed)


def askSecondSecret(account):
	if account.get("secondPublicKey", False):
		seed = "01"
		secondPublicKey = dposlib.core.crypto.getKeys(None, seed=dposlib.core.crypto.unhexlify(seed))["publicKey"]
		while secondPublicKey != account["secondPublicKey"]:
			try:
				secret = getpass.getpass("> enter %s second secret: " % account["username"])
				seed = dposlib.core.crypto.hashlib.sha256(secret.encode("utf8") if not isinstance(secret, bytes) else secret).digest()
				secondPublicKey = dposlib.core.crypto.getKeys(None, seed=seed)["publicKey"]
			except KeyboardInterrupt:
				printNewLine()
				logMsg("delegate configuration skipped")
				sys.exit(1)
		return dposlib.core.crypto.hexlify(seed)


def distributeRewards(rewards, pkey, minvote=0, excludes=[]):
	minvote *= 100000000
	voters = misc.loadPages(rest.GET.api.v2.delegates.__getattr__(pkey).voters)
	if len(voters) == 0:
		raise Exception("No voter found during distribution computation...")
	voters = dict([v["address"], float(v["balance"])] for v in voters if v["address"] not in excludes and v["balance"] >= minvote)
	total_balance = sum(voters.values())
	return OrderedDict(sorted([[a, b/total_balance*rewards] for a,b in voters.items()], key=lambda e:e[-1], reverse=True))


def adjust(username, value):
	if getPublicKeyFromUsername(username):
		folder = os.path.join(zen.DATA, username)
		forgery = loadJson("%s.forgery" % username, folder=folder)
		total = sum(forgery["contributions"].values())
		dumpJson(
			{
				"fees": forgery.get("fees", 0.),
				"blocks": forgery.get("blocks", 0),
				"contributions": OrderedDict(sorted([[a, v/total*value] for a,v in forgery["contributions"].items()], key=lambda e:e[-1], reverse=True))
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
		share = param.get("share", 1.0)

		forgery = loadJson("%s.forgery" % username, os.path.join(zen.DATA, username))
		data = OrderedDict(sorted([[a,w] for a,w in forgery.get("contributions", {}).items()], key=lambda e:e[-1], reverse=True))
		tbw = OrderedDict([a,w*share] for a,w in data.items() if w >= threshold)
		totalDistributed = sum(tbw.values())

		dumpJson(
			{
				"timestamp": "%s" % now,
				"delegate-share": round(forgery.get("blocks", 0.) * dposlib.rest.cfg.blockreward * (1.0 - share), 8),
				"undistributed": round(sum(w for w in data.values() if w < threshold), 8),
				"distributed": round(totalDistributed, 8),
				"fees": round(forgery.get("fees", 0.), 8),
				"weight": OrderedDict(sorted([[a,s/totalDistributed] for a,s in tbw.items()], key=lambda e:e[-1], reverse=True))
			},
			"%s.tbw" % now.strftime("%Y%m%d-%H%M"),
			folder=os.path.join(zen.ROOT, "app", ".tbw", username)
		)

		forgery["contributions"] = OrderedDict([a, 0. if a in tbw else w] for a,w in data.items())
		forgery["blocks"] = 0
		forgery["fees"] = 0.
		dumpJson(forgery, "%s.forgery" % username, os.path.join(zen.DATA, username))


def dumpRegistry(username, fee_coverage=False):
	root = loadJson("root.json")
	tbw = loadJson("tbw.json")

	config = loadJson("%s.json" % username)
	if "#1" in config:
		keys = dposlib.core.crypto.getKeys(None, seed=dposlib.core.crypto.unhexlify(config["#1"]))
	else:
		pkey = getPublicKeyFromUsername(username)
		delegates = loadJson("delegates.json", os.path.join(root["env"], "config"))
		if delegates == {}:
			delegates = loadJson("delegates.json", os.path.dirname(root["env"]))
		for secret in delegates["secrets"]:
			keys = dposlib.core.crypto.getKeys(secret)
			if keys["publicKey"] == pkey: break
			else: keys = False
	
	if keys:
		dposlib.core.Transaction._publicKey = keys["publicKey"]
		dposlib.core.Transaction._privateKey = keys["privateKey"]

		config = loadJson("%s.json" % username)
		folder = os.path.join(zen.ROOT, "app", ".tbw", username)

		fee_level = config.get("fee_level", False)
		if fee_level:
			dposlib.core.Transaction.setDynamicFee(fee_level)
			if isinstance(fee_level, int):
				fee_level = ((rest.cfg.doffsets.get("transfer", 0) + 153 + len("%s reward" % username)) * fee_level) / 100000000.0
			else:
				fee_level = rest.cfg.feestats[0].get(fee_level, 10000000.0) / 100000000.0
		else:
			dposlib.core.Transaction.setStaticFee()
			fee_level = 0.1

		if config.get("#2", None):
			secondKeys = dposlib.core.crypto.getKeys(None, seed=dposlib.core.crypto.unhexlify(config["#2"]))
			dposlib.core.Transaction._secondPublicKey = secondKeys["publicKey"]
			dposlib.core.Transaction._secondPrivateKey = secondKeys["privateKey"]

		for name in [n for n in os.listdir(folder) if n.endswith(".tbw")]:
			data = loadJson(name, folder) 
			amount = data["distributed"]
			fee_covered = tbw.get("fee_coverage", fee_coverage) and (data["fees"]/fee_level) > len(data["weight"])

			totalFees, registry = 0, OrderedDict()
			timestamp = slots.getTime()
			for address, weight in sorted(data["weight"].items(), key=lambda e:e[-1], reverse=True):
				transaction = dposlib.core.transfer(
					round(amount*weight, 8), address,
					config.get("vendorField", "%s reward" % username)
				)
				transaction["timestamp"] = timestamp
				transaction.finalize(fee_included=not fee_covered)
				totalFees += transaction["fee"]
				registry[transaction["id"]] = transaction

			if config.get("wallet", False):
				transaction = dposlib.core.transfer(
					round(data["delegate-share"] + data["fees"]-(totalFees/100000000.0 if fee_covered else 0), 8),
					config["wallet"], "%s share" % username
				)
				transaction.finalize(fee_included=True)
				registry[transaction["id"]] = transaction

			dumpJson(registry, "%s.registry" % os.path.splitext(name)[0], os.path.join(zen.DATA, username))

			if fee_covered: data["covered fees"] = totalFees/100000000.0
			dumpJson(data, name, os.path.join(folder, "history"))
			os.remove(os.path.join(folder, name))

		dposlib.core.Transaction.unlink()


def broadcast(username, target_delegate=False, chunk_size=15):
	# initialize options
	tbw = loadJson("tbw.json")
	target_delegate = tbw.get("target_delegate", target_delegate)
	chunk_size = max(5, tbw.get("chunk_size", chunk_size))

	# proceed all registry file found in username folder
	sqlite = initDb(username)
	cursor = sqlite.cursor()
	folder = os.path.join(zen.DATA, username)

	for name in [n for n in os.listdir(folder) if n.endswith(".registry")]:
		registry = loadJson(name, folder=folder)
		transactions = list(registry.values())

		chunks = iter([transactions[x:x+chunk_size] for x in range(0, len(transactions), chunk_size)])
		stop_while = False
		while not stop_while:
			nb_blocks = incr = 0
			if target_delegate:
				incr = chunk_size
				waitFor(transactions[0]["senderPublicKey"])
			limit = time.time() + rest.cfg.blocktime - 2
			while time.time() < limit and nb_blocks <= 150: # 150 = max tx/block
				try:
					chunk = next(chunks)
				except StopIteration:
					stop_while = True
				else:
					response = rest.POST.api.transactions(transactions=chunk, peer=zen.API_PEER)
					logMsg("broadcasting chunk of transactions...\n%s" % json.dumps(response, indent=2))
					nb_blocks += incr

		tries = 0
		while len(registry) > 0 and tries < 5:
			logMsg("[check #%d] waiting %s seconds..." % (tries+1, rest.cfg.blocktime))
			time.sleep(rest.cfg.blocktime)
			for tx in [t for t in transactions if t["id"] in registry]:
				if rest.GET.api.v2.transactions(tx["id"]).get("data", {}).get("confirmations", 0) >= 1:
					logMsg("transaction %(id)s <type %(type)s> applied" % registry.pop(tx["id"]))
					if "reward" in tx["vendorField"]:
						cursor.execute(
							"INSERT OR REPLACE INTO transactions(filename, timestamp, amount, address, id) VALUES(?,?,?,?,?);",
							(os.path.splitext(name)[0], tx["timestamp"], tx["amount"]/100000000., tx["recipientId"], tx["id"])
						)
			tries += 1

		if tries >=5:
			logMsg("action finished, network was too bad or the fees are to high")
		else:
			dumpJson(dict([tx["id"],tx] for tx in transactions), name, folder=os.path.join(folder, "backup"))
			os.remove(os.path.join(folder, name))
			misc.notify("Payroll successfully broadcasted !")

		sqlite.commit()


def waitFor(pkey):
	logMsg("waiting for forger...")
	rank = rest.cfg.delegate
	while rank > 0:
		time.sleep(2*rest.cfg.blocktime if rank > 3 else 1)
		try: forging_queue = rest.GET.api.v1.delegates.getNextForgers(limit=rest.cfg.delegate).get("delegates", [])
		except: break
		try: rank = forging_queue.index(pkey)
		except ValueError: break
