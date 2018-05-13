# -*- encoding:utf-8 -*-

from zen.cmn import loadJson, dumpJson, loadConfig, dumpConfig, logMsg, getBestSeed, execute, bash
from collections import OrderedDict

import zen.cmn as cmn
import io
import os
import sys
import time
import math
import pprint
import requests

ROOT = os.path.abspath(os.path.dirname(__file__))
NAME = os.path.splitext(os.path.basename(__file__))[0]


def float2minsec(value):
	ent = math.floor(value)
	return "%dmin %02dsec" % (int(ent), (value-ent)*60)


def loadStatus():
	return loadJson(os.path.join(ROOT, NAME+".status"))


def dumpStatus(data):
	dumpJson(data, os.path.join(ROOT, NAME+".status"))


def getBestSnapshot():
	config = loadConfig()
	size, snapshot= 0, None
	for snapshot in config.get("snapshots", []):
		try:
			req = requests.get(snapshot, stream=True)
			content_length = int(req.headers["Content-length"])
			if content_length > size:
				size = content_length
				best = snapshot
		except Exception as error:
			sys.stdout.write("    Error occured with %s : %s\n" % (snapshot, error))
	return size, snapshot


def getNextForgeRound(seed, **kw):
	forging_queue = requests.get(seed+"/api/delegates/getNextForgers?limit=%(delegates)d" % kw).json().get("delegates", [])
	try:
		delay_before_forge = float2minsec(forging_queue.index(kw["publicKey"]) * kw["blocktime"] / 60.)
	except (KeyError, ValueError):
		delay_before_forge = "Nan"
	return delay_before_forge


def getNetHeight(seed):
	return requests.get(seed+"/api/blocks/getHeight", verify=True).json().get("height", 0)


def getNodeHeight():
	config = loadConfig()
	config["quiet"] = True
	return int(execute(*config["cmd"]["nodeheight"], **config)[0].strip())


def restart():
	logMsg("Restarting node...")
	config = loadConfig()
	status = loadStatus()
	status["restarted"] = True
	dumpStatus(status)
	try:
		out, err = execute(*config["cmd"]["restart"], **config)
		with io.open("restart.log", "wb") as log:
			log.write(err if isinstance(err, bytes) else err.encode("utf-8"))
	except Exception as error:
		sys.stdout.write("    Error occured : %s\n" % error)
		status["restarted"] = False
	else:
		status.pop("block speed issue round", False)
	dumpStatus(status)


def rebuild():
	logMsg("Rebuilding node...")
	config = loadConfig()
	status = loadStatus()

	status["rebuilding"] = True
	dumpStatus(status)

	snapshot_folder = "%(homedir)s/snapshots"  %config
	snapshots = [os.stat(os.path.join(snapshot_folder, f)) for f in os.listdir(snapshot_folder)]
	if len(snapshots):
		snapshot_size = max(snp.st_size for snp in snapshots)
	else:
		snapshot_size = 0
	size, url = getBestSnapshot()
	sys.stdout.write("    Checking for best snapshots\n")
	sys.stdout.write("    > size:%so - url:%s (previous snapshot size %so)\n" % (size, url, snapshot_size))

	if size > snapshot_size:
		execute("wget -nv %(best_snapshot)s -O %(homedir)s/snapshots/%(database)s",
			best_snapshot=url,
			homedir=config["homedir"],
			database=config["database"]
		)
			
	try:
		out, err = execute(*config["cmd"]["rebuild"], **config)
		with io.open("rebuild.log", "wb") as log:
			log.write(err if isinstance(err, bytes) else err.encode("utf-8"))
	except Exception as error:
		sys.stdout.write("    Error occured : %s\n" % error)
		status["rebuilding"] = False
	else:
		status.pop("rebuilding", False)
	dumpStatus(status)

	# restart()


def check():
	# load app configuration, last known status and best seed
	config = loadConfig()
	status = loadStatus()

	# exit if node is rebuilding
	if status.get("rebuilding", False):
		logMsg("Node is rebuilding...")
		dumpStatus(status)
		return

	# load best seed
	seed = getBestSeed(*config.get("seeds", []))
	# get values to check node health
	if not seed:
		# better use peer if no seeds available
		logMsg("No seed available...")
		seed = config["peer"]
		net_height = getNetHeight(seed)
	else:
		try:
			net_height = max(getNetHeight(seed), getNetHeight(config["peer"]))
		except requests.exceptions.ConnectionError:
			restart()
			return 

	# estimate time remaining for next block forge
	status["next forge round"] = getNextForgeRound(seed, **config)

	node_height = getNodeHeight()
	timestamp = time.time()
	height_diff = net_height - node_height
	block_speed = 60*(node_height - status.get("node height", 0))/ \
	                 (timestamp - status.get("timestamp", 0))

	# update computed values
	status.update(**{
		"net height": net_height,
		"node height": node_height,
		"height diff": height_diff,
		"timestamp": timestamp,
		"block speed": block_speed
	})

	# if node block speed under 80% of theorical blockchain speed
	if block_speed < 0.8*60.0/config["blocktime"]: # 60/blocktime => blockchain speed in block per minute
		status["block speed issue round"] = status.get("block speed issue round", 0)+1
		logMsg("Block speed issue : %.2f blk/min instead of %.2f (round %d)" % \
		                           (block_speed, 60.0/config["blocktime"], status["block speed issue round"]))
	else:
		status.pop("block speed issue round", False)

	# if node height is far from half day produced block
	if height_diff > 60./config["blocktime"]*60*12: 
		logMsg("Node too far away from height, better rebuild ! (%d blocks)" % (height_diff))
		rebuild()
		restart()
	# node height is same as net height
	elif -1 <= height_diff <= 0:
		status["synch"] = True
		if status.pop("restarted", False):
			logMsg("Node is synch !")
		dumpStatus(status)
	else:
		status["synch"] = False
		dumpStatus(status)
		# node is not stuck and is too far from net height
		if height_diff > config["blocktime"]/0.8:
			logMsg("Height difference is too high ! (%d blocks)" % (height_diff))
			# node already restarted and we gave it sufficient time to reach net height
			if status.get("restarted", False) and \
			   status.get("block speed issue round", 0) >= 0.5*config["delegates"]*config["blocktime"]//60:
				rebuild()
				restart()
			# node is not restarted since last synch
			elif not status.get("restarted", False):
				restart()
		# node is going solo --> fork !
		elif height_diff < -config["blocktime"]/0.8:
			logMsg("Node is going solo with %d blocks forward ! It is forking..." % (-height_diff))
		pprint.pprint(status, indent=4)

	if status.get("block speed issue round", 0) > 0.8*config["delegates"]*config["blocktime"]//60:
		restart()
