# -*- coding:utf-8 -*-

from dposlib import rest
rest.use("dark")

import os
import io
import sys
import json
import time
import shutil
import datetime

# register python familly
PY3 = True if sys.version_info[0] >= 3 else False
input = raw_input if not PY3 else input

import requests

# configuration pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
DATA = os.path.abspath(os.path.join(ROOT, "app", ".data"))
JSON = os.path.abspath(os.path.join(ROOT, "app", ".json"))
LOG = os.path.abspath(os.path.join(ROOT, "app", ".log"))
# peers
WEBHOOK_PEER = None
API_PEER = None


def getPublicKeyFromUsername(username):
	req = dposlib.rest.GET.api.v2.delegates.get(kwargs["username"], peer=API_PEER)
	req.get("data", {}).get("publicKey", False)


def loadJson(name, folder=None):
	filename = os.path.join(JSON, name if not folder else os.path.join(folder, name))
	if os.path.exists(filename):
		with io.open(filename) as in_:
			return json.load(in_)
	else:
		return {}


def dumpJson(data, name, folder=None):
	filename = os.path.join(JSON, name if not folder else os.path.join(folder, name))
	try: os.makedirs(os.path.dirname(filename))
	except OSError: pass
	with io.open(filename, "w" if PY3 else "wb") as out:
		json.dump(data, out, indent=4)


def loadEnv(pathname):
	with io.open(pathname, "r") as environ:
		lines = [l.strip() for l in environ.read().split("\n")]
	result = {}
	for line in [l for l in lines if l != ""]:
		key,value = [l.strip() for l in line.split("=")]
		try:
			result[key] = int(value)
		except:
			result[key] = value
	return result


def dumpEnv(env, pathname):
	shutil.copy(pathname, pathname+".bak")
	with io.open(pathname, "w") as environ:
		for key,value in sorted([(k,v) for k,v in env.items()], key=lambda e:e[0]):
			environ.write("%s=%s\n" % (key, value))


def logMsg(msg, logname=None):
	if logname:
		logfile = os.path.join(LOG, logname)
		try:
			os.makedirs(os.path.dirname(logfile))
		except OSError:
			pass
		stdout = io.open(logfile, "a")
	else:
		stdout = sys.stdout
	stdout.write(">>> [%s] %s\n" % (datetime.datetime.now().strftime("%x %X"), msg))
	stdout.flush()
	return stdout.close() if logname else None


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
			except ValueError:
				i = -1
			except KeyboardInterrupt:
				return False
		if i == 0:
			return False
		return elem[i - 1]
	elif n == 1:
		return elem[0]
	else:
		sys.stdout.write("Nothing to choose...\n")
		return False


def init():
	global API_PEER, WEBHOOK_PEER
	root = loadJson("root.json")

	# first ask network folder
	node_folder = ""
	while not os.path.exists(node_folder):
		try: node_folder = os.path.abspath(input("> enter node folder: "))
		except KeyboardInterrupt: return
	blockchain_folder = os.path.join(node_folder, "packages", "crypto", "lib", "networks")
	try:
		blockchain = chooseItem("select blockchain:", *list(os.walk(blockchain_folder))[0][1])
	except IndexError:
		raise Exception("configuration folder not found")

	if not blockchain:
		logMsg("node configuration skipped")
		return
	
	networks_folder = os.path.join(blockchain_folder, blockchain)
	network = chooseItem("select network:", *[os.path.splitext(f)[0] for f in list(os.walk(networks_folder))[0][-1] if f.endswith(".json")])
	
	if not network:
		logMsg("node configuration skipped")
		return

	root["env"] = os.path.expanduser(os.path.join("~", ".%s"%blockchain, "config"))
	root["config"] = os.path.join(networks_folder, "%s.json"%network)
	dumpJson(root, "root.json")
	logMsg("node configuration saved in %s" % os.path.join(JSON, "root.json"))

	envfile = os.path.expanduser(os.path.join("~", ".%s"%blockchain, ".env"))
	env = loadEnv(envfile)
	env["ARK_WEBHOOKS_API_ENABLED"] = "true"
	env["ARK_WEBHOOKS_ENABLED"] = "true"
	env["ARK_WEBHOOKS_HOST"] = "0.0.0.0"
	env["ARK_WEBHOOKS_PORT"] = "4004"
	API_PEER = "http://127.0.0.1:%(ARK_API_PORT)s" % env
	WEBHOOK_PEER = "http://127.0.0.1:%(ARK_WEBHOOKS_PORT)s" % env
	dumpEnv(env, envfile)
	logMsg("environement configuration saved in %s" % envfile)

