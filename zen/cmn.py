# -*- encoding:utf-8 -*-
from zen import crypto

import io
import os
import sys
import json
import shlex
import getpass
import requests
import datetime
import subprocess

__PY3__ = True if sys.version_info[0] >= 3 else False
ROOT = os.path.abspath(os.path.dirname(__file__))
NAME = os.path.splitext(os.path.basename(__file__))[0]

input = raw_input if not __PY3__ else input


def loadJson(path):
	if os.path.exists(path):
		with io.open(path) as in_:
			data = json.load(in_)
	else:
		data = {}
	return data


def dumpJson(data, path):
	with io.open(path, "w" if __PY3__ else "wb") as out:
		json.dump(data, out, indent=4)


def loadConfig():
	return loadJson(os.path.join(ROOT, NAME+".json"))	


def dumpConfig(data):
	dumpJson(data, os.path.join(ROOT, NAME+".json"))


def findBlockchains():
	try:
		return [os.path.splitext(name)[0] for name in os.listdir(os.path.join(ROOT, "cfg")) if name.endswith(".json")]
	except:
		return []

def chooseItem(msg, *elem):
	n = len(elem)
	if n > 1:
		sys.stdout.write(msg + "\n")
		for i in range(n):
			sys.stdout.write("    %d - %s\n" % (i + 1, elem[i]))
		sys.stdout.write("    0 - quit\n")
		i = -1
		while i < 0 or i > n:
			try:
				i = input("Choose an item: [1-%d]> " % n)
				i = int(i)
			except:
				i = -1
		if i == 0:
			# Quit without making a selection
			return False
		return elem[i - 1]
	elif n == 1:
		return elem[0]
	else:
		sys.stdout.write("Nothing to choose...\n")
		return False


def setup():
	config = loadConfig()
	tbw_config = loadJson(os.path.join(ROOT, "tbw.json"))
	
	# select available network
	items = findBlockchains()
	blockchain = chooseItem("%d blockchain found:"%len(items), *items)
	if not blockchain:
		raise Exception("No blockchain selected")
	config["blockchain"] = blockchain
	blockchain_json = loadJson(os.path.join(ROOT, "cfg", blockchain+".json"))
	config["cmd"] = {
		"rebuild": blockchain_json.pop("rebuild", []),
		"restart": blockchain_json.pop("restart", []),
		"nodeheight": blockchain_json.pop("nodeheight", [])
	}

	# ask network config file
	node = tbw_config.get("node", "_._")
	while not os.path.exists(node):
		node = input("> enter config file path: ")
	tbw_config["node"] = os.path.normpath(os.path.abspath(node))

	_cnf = loadJson(tbw_config["node"])
	config["port"] = _cnf.get("port", None)
	config["network"] = _cnf.get("network", None)
	config["nethash"] = _cnf.get("nethash", None)
	config["version"] = _cnf.get("version", None)
	config["database"] = _cnf.get("db", {}).get("database", None)
	config["seeds"] = ["http://%(ip)s:%(port)s" % item for item in _cnf.get("peers", {}).get("list", [])]
	config["peer"] = "http://localhost:%r" % _cnf.get("port", None)

	config.update(**blockchain_json.pop("networks")[config["network"]])
	config.update(**blockchain_json)

	secret = _cnf.get("forging", {}).get("secret", [None])[0]
	keys = crypto.getKeys(secret)
	config["publicKey"] = keys["publicKey"]
	
	seed = getBestSeed(*config["seeds"])
	account = requests.get(seed+"/api/delegates/get?publicKey=%s" % keys["publicKey"], verify=True, timeout=5).json().get("delegate", {})
	tbw_config["username"] = account["username"]
	tbw_config["excludes"] = [account["address"]]
	account = requests.get(seed+"/api/accounts?address=%s" % account["address"], verify=True, timeout=5).json().get("account", {})

	if account.get("secondPublicKey", False):
		seed = tbw_config.get("#2", "01")
		if not seed: seed = "01"
		secondPublicKey = crypto.getKeys(None, seed=crypto.unhexlify(seed))["publicKey"]
		while secondPublicKey != account["secondPublicKey"]:
			secret = getpass.getpass("> enter your second secret: ")
			seed = crypto.hashlib.sha256(secret.encode("utf8") if not isinstance(secret, bytes) else secret).digest()
			secondPublicKey = crypto.getKeys(None, seed=seed)["publicKey"]
			tbw_config["#2"] = crypto.hexlify(seed)
	else:
		tbw_config["#2"] = None

	dumpJson(tbw_config, os.path.join(ROOT, "tbw.json"))
	config["user"] = os.environ.get("USER", None)
	config["homedir"] = os.environ.get("HOME", None)
	dumpConfig(config)


def configure():
	config = loadConfig()
	tbw_config = loadJson(os.path.join(ROOT, "tbw.json"))
	if OPTIONS.share:
		tbw_config["share"] = min(1.0, max(0.1, OPTIONS.share))
	if OPTIONS.threshold:
		tbw_config["threshold"] = max(0.1, OPTIONS.threshold)
	if OPTIONS.funds:
		if requests.get(config["peer"]+"/api/accounts?address=%s" % OPTIONS.funds, verify=True, timeout=5).json().get("success", False):
			tbw_config["funds"] = OPTIONS.funds
		else:
			sys.stdout.write("> %s seems not to be a valid address" % OPTIONS.funds)
	if OPTIONS.vendorField:
		tbw_config["vendorField"] = OPTIONS.vendorField[0:min(64, len(OPTIONS.vendorField))]
	if OPTIONS.excludes:
		tbw_config["excludes"] = OPTIONS.excludes.split(",")
	if OPTIONS.targeting:
		tbw_config["targeting"] = not tbw_config.pop("targeting", False)
	if OPTIONS.symbol:
		tbw_config["symbol"] = OPTIONS.symbol

	dumpJson(tbw_config, os.path.join(ROOT, "tbw.json"))


def logMsg(msg, stdout=None):
	stdout = sys.stdout if not stdout else stdout
	stdout.write(">>> [%s] %s\n" % (datetime.datetime.now().strftime("%x %X"), msg))
	stdout.flush()


def getBestSeed(*seeds):
	height, url = 0, None
	for seed in seeds:
		try:
			h = requests.get(seed+"/api/blocks/getHeight", verify=True, timeout=5).json().get("height", 0)
			if h > height:
				height = h
				url = seed
		except Exception as error:
			pass #sys.stdout.write("    Error occured with %s : %s\n" % (seed, error))
	return url


def execute(*lines, **config):
	out, err = "", ""
	for line in [l%config for l in lines]:
		if not config.get("quiet", False):
			sys.stdout.write("... %s\n" % line)
		sys.stdout.flush()
		err += "... %s\n"%line
		answer = subprocess.Popen(shlex.split(line), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		code =  answer.wait()
		if code != 0:
			sys.stdout.write("    [STATUS CODE RETURNED: %r]\n" % code)
		_out, _err = answer.communicate()
		out += _out
		err += _err
	return out, err


def bash(*lines, **config):
	answer = subprocess.Popen("/bin/bash", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = answer.communicate("\n".join([l%config for l in lines]))
	return out, err
