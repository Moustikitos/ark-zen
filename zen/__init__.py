# -*- coding:utf-8 -*-

import dposlib
from dposlib import rest

import os
import io
import sys
import json
import time
import shutil
import socket
import datetime

# https://docs.ark.io/guidebook/core/events.html#available-events

# register python familly
PY3 = True if sys.version_info[0] >= 3 else False
input = raw_input if not PY3 else input

import requests

# configuration pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
JSON = os.path.abspath(os.path.join(ROOT, ".json"))
DATA = os.path.abspath(os.path.join(ROOT, "app", ".data"))
LOG = os.path.abspath(os.path.join(ROOT, "app", ".log"))
ENV = None

# peers
API_PEER = None
WEBHOOK_PEER = None
#
PUBLIC_IP = None


def getIp():
	"""Store the public ip of server in PUBLIC_IP global var"""
	global PUBLIC_IP
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# doesn't even have to be reachable
		s.connect(('10.255.255.255', 1))
		PUBLIC_IP = s.getsockname()[0]
	except:
		PUBLIC_IP = '127.0.0.1'
	finally:
		s.close()
	return PUBLIC_IP


def getPublicKeyFromUsername(username):
	req = dposlib.rest.GET.api.v2.delegates(username)
	return req.get("data", {}).get("publicKey", False)


def getUsernameFromPublicKey(publicKey):
	req = dposlib.rest.GET.api.v2.delegates(publicKey)
	return req.get("data", {}).get("username", False)


def loadJson(name, folder=None):
	filename = os.path.join(JSON if not folder else folder, name)
	if os.path.exists(filename):
		with io.open(filename) as in_:
			return json.load(in_)
	else:
		return {}


def dumpJson(data, name, folder=None):
	filename = os.path.join(JSON if not folder else folder, name)
	try: os.makedirs(os.path.dirname(filename))
	except OSError: pass
	with io.open(filename, "w" if PY3 else "wb") as out:
		json.dump(data, out, indent=4)


def dropJson(name, folder=None):
	filename = os.path.join(JSON if not folder else folder, name)
	if os.path.exists(filename):
		os.remove(filename)
	

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
	with io.open(pathname, "wb") as environ:
		for key,value in sorted([(k,v) for k,v in env.items()], key=lambda e:e[0]):
			environ.write(b"%s=%s\n" % (key, value))


def logMsg(msg, logname=None, dated=False):
	if logname:
		logfile = os.path.join(LOG, logname)
		try:
			os.makedirs(os.path.dirname(logfile))
		except OSError:
			pass
		stdout = io.open(logfile, "a")
	else:
		stdout = sys.stdout

	stdout.write(
		">>> " + \
		("[%s] " % datetime.datetime.now().strftime("%x %X") if dated else "") + \
		"%s\n" % msg
	)
	stdout.flush()

	if logname:
		return stdout.close()


def initPeers():
	global WEBHOOK_PEER, API_PEER
	root = loadJson("root.json")
	try: env = loadEnv(os.path.join(root["env"]))
	except: pass
	try: WEBHOOK_PEER = "http://127.0.0.1:%(ARK_WEBHOOKS_PORT)s" % env
	except: pass
	try: API_PEER = "http://127.0.0.1:%(ARK_API_PORT)s" % env
	except: pass


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
				sys.stdout.write("\n")
				sys.stdout.flush()
				return False
		if i == 0:
			return None
		return elem[i - 1]
	elif n == 1:
		return elem[0]
	else:
		sys.stdout.write("Nothing to choose...\n")
		return False


def chooseMultipleItem(msg, *elem):
	"""
	Convenience function to allow the user to select multiple items from a list.
	"""
	n = len(elem)
	if n > 0:
		sys.stdout.write(msg + "\n")
		for i in range(n):
			sys.stdout.write("    %d - %s\n" % (i + 1, elem[i]))
		sys.stdout.write("    0 - quit\n")
		indexes = []
		while len(indexes) == 0:
			try:
				indexes = input("Choose items: [1-%d or all]> " % n)
				if indexes == "all":
					indexes = [i + 1 for i in range(n)]
				elif indexes == "0":
					indexes = []
					break
				else:
					indexes = [int(s) for s in indexes.strip().replace(" ", ",").split(",") if s != ""]
					indexes = [r for r in indexes if 0 < r <= n]
			except:
				indexes = []
		return [elem[i-1] for i in indexes]
	
	sys.stdout.write("Nothing to choose...\n")
	return []


def init():
	global ENV

	# try to load root.json configuration file
	root = loadJson("root.json")
	# ask node folder if not found in root.json or if root.json dos not exist
	node_folder = root.get("node_folder", "")
	while not os.path.exists(node_folder):
		try:
			node_folder = os.path.abspath(input("> enter node folder: "))
		except KeyboardInterrupt:
			raise Exception("configuration aborted...")
	
	# ark core v2.0.x
	blockchain_folder = os.path.join(node_folder, "packages", "crypto", "lib", "networks")
	if not os.path.exists(blockchain_folder):
		# ark core v2.1.x
		blockchain_folder = os.path.join(node_folder, "packages", "crypto", "src", "networks")

	try:
		blockchain = chooseItem("select blockchain:", *list(os.walk(blockchain_folder))[0][1])
	except IndexError:
		raise Exception("configuration folder not found")
		sys.exit(1)
	if not blockchain:
		logMsg("node configuration skipped (%s)" % blockchain)
		sys.exit(1)
	
	# write root.json file
	networks_folder = os.path.join(blockchain_folder, blockchain)
	if os.path.exists(os.path.join(networks_folder, "network.json")):
		# ark core v2.1.x
		root["config"] = os.path.join(networks_folder, "network.json")
		ENV = os.path.expanduser(os.path.join("~", ".config", "ark-core", blockchain, ".env"))
	else:
		# ark core v2.0.x
		try:
			network = chooseItem("select network:", *[os.path.splitext(f)[0] for f in list(os.walk(networks_folder))[0][-1] if f.endswith(".json")])
		except IndexError:
			raise Exception("network folder not found")
			sys.exit(1)
		if not network:
			logMsg("node configuration skipped (%s)" % network)
			sys.exit(1)
		root["config"] = os.path.join(networks_folder, "%s.json" % network)
		ENV = os.path.expanduser(os.path.join("~", ".%s"%blockchain, ".env"))

	p,n = os.path.split(root["config"])
	root["name"] = loadJson(n,p)["name"]
	root["env"] = ENV
	root["node_folder"] = node_folder
	dumpJson(root, "root.json")
	logMsg("node configuration saved in %s" % os.path.join(JSON, "root.json"))

	# edit .env file to enable webhooks
	env = loadEnv(ENV)
	# ark core v2.0.x
	env["ARK_WEBHOOKS_API_ENABLED"] = "true"
	env["ARK_WEBHOOKS_ENABLED"] = "true"
	env["ARK_WEBHOOKS_HOST"] = "0.0.0.0"
	env["ARK_WEBHOOKS_PORT"] = "4004"
	# ark core v2.1.x
	env["CORE_WEBHOOKS_API_ENABLED"] = "true"
	env["CORE_WEBHOOKS_ENABLED"] = "true"
	env["CORE_WEBHOOKS_HOST"] = "0.0.0.0"
	env["CORE_WEBHOOKS_PORT"] = "4004"
	dumpEnv(env, ENV)
	logMsg("environement configuration saved in %s" % ENV)


# initialize zen
getIp()
initPeers()
# initialize blockchain network
root = loadJson("root.json")
rest.use("ark" if root.get("name", False) == "mainnet" else "dark")
dposlib.core.stop()
# customize blockchain network if needed
custom_peers = loadJson("tbw.json").get("custom_peers", [])
if len(custom_peers) > 0:
	dposlib.rest.cfg.peers = custom_peers
dposlib.rest.cfg.timeout = 10
