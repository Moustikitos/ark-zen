# -*- encoding:utf-8 -*-
import os
import sys
import time
import json
import pytz
import shutil
import sqlite3
import datetime
import requests

from collections import OrderedDict

from zen import crypto
from zen.chk import getNextForgeRound
from zen.cmn import dumpJson, loadConfig, loadJson, logMsg
from zen.tbw import loadParam

ROOT = os.path.abspath(os.path.dirname(__file__))
NAME = os.path.splitext(os.path.basename(__file__))[0]


def initDb():
	sqlite = sqlite3.connect(os.path.join(ROOT, "%s.db" % NAME))
	sqlite.row_factory = sqlite3.Row
	cursor = sqlite.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS transactions(date TEXT, timestamp INTEGER, amount INTEGER, address TEXT, id TEXT);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS tx_index ON transactions(id);")
	cursor.execute("CREATE TABLE IF NOT EXISTS payrolls(date TEXT, share REAL, amount INTEGER);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS payroll_index ON payrolls(date);")
	sqlite.commit()
	return sqlite


def getTime(begintime, time=None):
	delta = (datetime.datetime.now(pytz.UTC) if not time else time) - begintime
	return delta.total_seconds()


def getRealTime(begintime, epoch=None):
	epoch = getTime() if epoch == None else epoch
	return begintime + datetime.timedelta(seconds=epoch)


def waitFor(**config):
	blocktime = config["blocktime"]
	delegates = config["delegates"]
	rank = delegates
	while rank > 0:
		time.sleep(2*blocktime if rank > 3 else 1)
		forging_queue = requests.get(config["peer"]+"/api/delegates/getNextForgers?limit=%d" % delegates).json().get("delegates", [])
		rank = forging_queue.index(config["publicKey"])


def pay():
	param = loadParam()
	for filename in [os.path.splitext(name)[0] for name in os.listdir(ROOT) if name.endswith(".tbw")]:
		dumpRegistry(filename)
		broadcast(filename, targeting=param.get("targeting", False))


def dumpRegistry(date):
	config = loadConfig()
	tbw = loadJson(os.path.join(ROOT, "%s.tbw"%date))
	param = loadParam()
	_cnf = loadJson(param["node"])
	keys = crypto.getKeys(_cnf["forging"]["secret"][0])
	if param["#2"]:
		keys["secondPrivateKey"] = crypto.getKeys(seed=crypto.unhexlify(param["#2"]))["privateKey"]

	amount = tbw["amount"]
	registry = OrderedDict()
	begintime = datetime.datetime(*config["begin"], tzinfo=pytz.UTC)

	for address, weight in sorted(tbw["weight"].items(), key=lambda e:e[-1], reverse=True):
		delta = datetime.datetime.now(pytz.UTC) - begintime
		payload = dict(
			type=0,
			fee=10000000,
			timestamp=int(delta.total_seconds()),
			amount=int(amount*100000000*weight-10000000),
			recipientId=address,
			senderPublicKey=keys["publicKey"],
			vendorField=param.get("vendorField", "%s reward" % param.get("username", "Delegate"))
		)
		payload["signature"] = crypto.getSignature(payload, keys["privateKey"])
		if "secondPrivateKey" in keys:
			payload["signSignature"] = crypto.getSignature(payload, keys["privateKey"])
		payload["id"] = crypto.getId(payload)
		registry[payload["id"]] = payload

	if param.get("funds", False):
		account = requests.get(config["peer"]+"/api/delegates/get?publicKey=%s" % keys["publicKey"], verify=True, timeout=5).json().get("delegate", {})
		balance = int(requests.get(config["peer"]+"/api/accounts/getBalance?address=%s" % account["address"], verify=True, timeout=5).json().get("balance", 0))/100000000.
		if balance > 0:
			income = balance-tbw["amount"]-tbw["saved"]
			delta = datetime.datetime.now(pytz.UTC) - begintime
			payload = dict(
				type=0,
				fee=10000000,
				timestamp=int(delta.total_seconds()),
				amount=int(income*100000000-10000000),
				recipientId=param["funds"],
				senderPublicKey=keys["publicKey"],
				vendorField="%s share" % param.get("username", "Delegate")
			)
			payload["signature"] = crypto.getSignature(payload, keys["privateKey"])
			if "secondPrivateKey" in keys:
				payload["signSignature"] = crypto.getSignature(payload, keys["privateKey"])
			payload["id"] = crypto.getId(payload)
			registry[payload["id"]] = payload

	dumpJson(registry, os.path.join(ROOT, "%s.registry" % date))

	try: os.makedirs(os.path.join(ROOT, "archive"))
	except: pass
	shutil.move(os.path.join(ROOT, "%s.tbw"%date), os.path.join(ROOT, "archive", "%s.tbw"%date))


def broadcast(date, targeting=False, tx_per_block=50, tx_per_req=10):
	config = loadConfig()
	sqlite = initDb()
	cursor = sqlite.cursor()

	registry = loadJson(os.path.join(ROOT, "%s.registry" % date))
	transactions = [tx for tx in registry.values()]
	seed = config["peer"]

	logMsg("Broadcasting %d transactions..." % len(registry))
	
	sliced = [transactions[i:i+tx_per_block] for i in range(0,len(transactions),tx_per_block)]
	while len(registry):
		for slc in sliced:
			if targeting:
				sys.stdout.write("Waiting for delegate...\n")
				waitFor(**config)
			for txs in [slc[i:i+tx_per_req] for i in range(0,len(slc), tx_per_req)]:
				str_txs = ["transaction(type=%(type)d, amount=%(amount)d address=%(recipientId)s)"%tx for tx in txs]
				result = requests.post(
					seed+"/peer/transactions",
					json={"transactions":txs},
					headers={
						"nethash":config["nethash"],
						"version":config["version"],
						"port":"%d"%config["port"]
					}
				).json()

				if result.get("success", False):
					sys.stdout.write("\n".join("%s -> %s" % (a,b) for a,b in zip(str_txs, result["transactionIds"])) + "\n")
				else:
					pass

			time.sleep(config["blocktime"]*2)

			for txid in list(registry.keys()):
				if requests.get(seed+"/api/transactions/get?id=%s"%txid).json().get("success", False):
					tx = registry.pop(txid)
					cursor.execute(
						"INSERT OR REPLACE INTO transactions(date, timestamp, amount, address, id) VALUES(?,?,?,?,?);",
						(date, tx["timestamp"], tx["amount"]/100000000., tx["recipientId"], tx["id"])
					)
		sqlite.commit()
	os.remove(os.path.join(ROOT, "%s.registry" % date))


def build():
	config = loadConfig()
	sqlite = initDb()
	cursor = sqlite.cursor()
	seed = config["peer"]

	tbw_config = loadJson(os.path.join(ROOT, "tbw.json"))
	_cnf = loadJson(tbw_config["node"])
	secret = _cnf["forging"]["secret"][0]
	keys = crypto.getKeys(secret)
	account = requests.get(seed+"/api/delegates/get?publicKey=%s" % keys["publicKey"], verify=True, timeout=5).json().get("delegate", {})
	address = account["address"]
	begintime = datetime.datetime(*config["begin"], tzinfo=pytz.UTC)

	offset = 0
	transactions = []
	search = requests.get(seed+"/api/transactions?senderId=%s&limit=50&offset=%d"%(address, offset)).json().get("transactions", [])
	while len(search) == 50:
		transactions.extend([t for t in search if t["type"] == 0])
		offset += 50
		search = requests.get(seed+"/api/transactions?senderId=%s&limit=50&offset=%d"%(address, offset)).json().get("transactions", [])
	transactions.extend(search)

	for tx in transactions:
		date = getRealTime(begintime, tx["timestamp"])
		cursor.execute(
			"INSERT OR REPLACE INTO transactions(date, timestamp, amount, address, id) VALUES(?,?,?,?,?);",
			(date.strftime("%Y-%m-%d"), tx["timestamp"], tx["amount"]/100000000., tx["recipientId"], tx["id"])
		)
	sqlite.commit()
