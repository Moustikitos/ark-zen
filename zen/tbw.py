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
import zen.misc

from dposlib import rest
from dposlib.blockchain import slots
from dposlib.util.bin import unhexlify
from zen import loadJson, dumpJson, logMsg, getPublicKeyFromUsername


def initDb(username):
	sqlite = sqlite3.connect(os.path.join(zen.ROOT, "%s.db" % username))
	sqlite.row_factory = sqlite3.Row
	cursor = sqlite.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS transactions(filename TEXT, timestamp INTEGER, amount INTEGER, address TEXT, id TEXT);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS tx_index ON transactions(id);")
	cursor.execute("CREATE TABLE IF NOT EXISTS dilution(timestamp REAL, value REAL);")
	sqlite.commit()
	return sqlite


def rebuildDb(username):
	sqlite = initDb(username)
	cursor = sqlite.cursor()

	account = rest.GET.api.delegates(username, returnKey="data")
	address =  account.get("address", False)
	if address:

		# transactions = []
		count, pageCount = 0, 1
		while count < pageCount:
			req = rest.GET.api.wallets(address, "transactions", page=count+1)
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
	root = loadJson("root.json")

	# if no options given, initialize forgers set on the node
	if not len(kwargs):
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
			req = rest.GET.api.delegates(username).get("data", {})
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

		max_per_sender = int(kwargs.pop("max_per_sender", False))
		if max_per_sender != False:
			env = zen.loadEnv(root["env"])
			env["CORE_TRANSACTION_POOL_MAX_PER_SENDER"] = max_per_sender
			zen.dumpEnv(env, root["env"])
			zen.logMsg("env parameter CORE_TRANSACTION_POOL_MAX_PER_SENDER set to %d \n    ark-core-relay have to be restarted" % (max_per_sender))

		tbw.update(**kwargs)
		dumpJson(tbw, "tbw.json")


def setDelegate(pkey, webhook_peer, public=False):
	printNewLine()
	# for each publicKey, get account data (merge delegate and wallet info)
	req = rest.GET.api.delegates(pkey).get("data", {})
	account = rest.GET.api.wallets(pkey).get("data", {})
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
	voters = zen.misc.loadPages(rest.GET.api.delegates.__getattr__(pkey).voters)
	if len(voters) == 0:
		raise Exception("No voter found during distribution computation...")
	voters = dict([v["address"], float(v["balance"])] for v in voters if v["address"] not in excludes and v["balance"] >= minvote)
	total_balance = sum(voters.values())
	# ARK Vote Dilution
	dilution_value = 100000000.0 / total_balance
	sqlite = initDb(pkey)
	req = sqlite.execute("SELECT * FROM dilution ORDER BY timestamp DESC LIMIT 1").fetchall()
	# this sql command remove double values in value column keeping the first one 
	# DELETE FROM dilution WHERE timestamp NOT IN
	# (SELECT MIN(timestamp) as timestamp FROM dilution GROUP BY value)
	if len(req):
		value = req[0]["value"]
		if value != dilution_value:
			sqlite.execute("INSERT INTO dilution(timestamp, value) VALUES(?,?);", (time.time(), dilution_value))
			sqlite.commit()
	else:
		sqlite.execute("INSERT INTO dilution(timestamp, value) VALUES(?,?);", (time.time(), dilution_value))
		sqlite.commit()
	sqlite.close()
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
		tbw = OrderedDict([a,w*share] for a,w in data.items() if w*share >= threshold)
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

		# reset forgery keeping unpaind voters
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


def broadcast(username, chunk_size=30):
	# initialize options
	tbw = loadJson("tbw.json")
	chunk_size = max(5, tbw.get("chunk_size", chunk_size))
	folder = os.path.join(zen.DATA, username)

	# proceed all registry file found in username folder
	for name in [n for n in os.listdir(folder) if n.endswith(".registry")]:
		registry = loadJson(name, folder=folder)
		transactions = list(registry.values())
		for chunk in (transactions[x:x+chunk_size] for x in range(0, len(transactions), chunk_size)):
			response = rest.POST.api.transactions(transactions=chunk, peer=zen.API_PEER)
			logMsg("broadcasting chunk of transactions...\n%s" % json.dumps(response, indent=2))
	zen.misc.notify("New payroll started : %d transactions sent to delegate node..." % len(transactions))


def checkApplied(username):
	folder = os.path.join(zen.DATA, username)
	sqlite = initDb(username)
	cursor = sqlite.cursor()

	for name in [n for n in os.listdir(folder) if n.endswith(".registry")]:
		full_registry = loadJson(name, folder=folder)
		# try to lad a milestone first, if no one exists
		registry = loadJson(name+".milestone", folder=folder)
		# if void dict returned by loadJson, then load registry file
		if not len(registry):
			registry = dict(full_registry) #loadJson(name, folder=folder)
			logMsg("starting transaction check from %s..." % name)
		else:
			# misc.notify("Transactions are about to be checked (%d)..." % len(registry))
			logMsg("resuming transaction check from %s..." % (name+".milestone"))

		start = time.time()
		transactions = list(registry.values())
		for tx in [t for t in transactions if t["id"] in registry]:
			if zen.misc.transactionApplied(tx["id"]):
				logMsg("transaction %(id)s <type %(type)s> applied" % registry.pop(tx["id"]))
				if "reward" in tx["vendorField"]:
					cursor.execute(
						"INSERT OR REPLACE INTO transactions(filename, timestamp, amount, address, id) VALUES(?,?,?,?,?);",
						(os.path.splitext(name)[0], tx["timestamp"], tx["amount"]/100000000., tx["recipientId"], tx["id"])
					)
			# set a milestone every 5 seconds
			if (time.time() - start) > 5.:
				sqlite.commit()
				dumpJson(registry, name+".milestone", folder=folder)
				logMsg("milestone set (%d transaction left to check)" % len(registry))
				start = time.time()

		if len(registry) == 0:
			dumpJson(dict([tx["id"],tx] for tx in transactions), name, folder=os.path.join(folder, "backup"))
			try:
				os.remove(os.path.join(folder, name))
				os.remove(os.path.join(folder, name+".milestone"))
			except:
				pass
			checked_tx = full_registry.values()
			zen.misc.notify("Payroll successfully broadcasted !\n%.8f %s sent trough %d transactions" % (
				sum([tx["amount"] for tx in checked_tx])/100000000.,
				dposlib.rest.cfg.symbol,
				len(checked_tx)
			))
		else:
			zen.misc.notify("Transactions are still to be checked (%d)..." % len(registry))

		sqlite.commit()
