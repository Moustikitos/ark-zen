# -*- encoding:utf-8 -*-

from zen.cmn import loadJson, dumpJson, logMsg
from zen.chk import loadConfig
from collections import OrderedDict


import os
import sys
import time
import pytz
import datetime
import requests


ROOT = os.path.abspath(os.path.dirname(__file__))
NAME = os.path.splitext(os.path.basename(__file__))[0]


def loadForge():
	return loadJson(os.path.join(ROOT, NAME+".forge"))


def dumpForge(forge):
	dumpJson(forge, os.path.join(ROOT, NAME+".forge"))


def loadTBW():
	return loadJson(os.path.join(ROOT, NAME+".weight"))


def dumpTBW(tbw):
	dumpJson(tbw, os.path.join(ROOT, NAME+".weight"))


def loadParam():
	return loadJson(os.path.join(ROOT, NAME+".json"))
	

def dumpParam(param):
	dumpJson(param, os.path.join(ROOT, NAME+".json"))


def get():
	param = loadParam()
	config = loadConfig()
	forge = loadForge()
	seed = config["peer"]

	if config.get("publicKey", False):
		resp = requests.get(seed+"/api/delegates/forging/getForgedByAccount?generatorPublicKey="+config["publicKey"]).json()
		if not len(forge):
			reward = 0
			dumpForge(resp)
		else:
			reward = (int(resp["rewards"]) - int(forge["rewards"]))/100000000.
			dumpForge(resp)

		if reward > 0.:
			voters = requests.get(seed+"/api/delegates/voters?publicKey="+config["publicKey"]).json().get("accounts", [])
			voters = dict([v["address"], float(v["balance"])] for v in voters if v["address"] not in param.get("excludes", []))
			total_balance = sum(voters.values())
			pairs = [[a,b/total_balance*reward] for a,b in voters.items() if a not in param.get("excludes", []) and b > param.get("minvote", 0)]
			return OrderedDict(sorted(pairs, key=lambda e:e[-1], reverse=True))

	return OrderedDict()


def spread():
	rewards = get()
	tbw = loadTBW()

	if len(rewards):
		all_addresses = list(rewards.keys())
		cowards = set(tbw.keys()) - set(all_addresses)
		if len(cowards):
			logMsg("down-voted by : %s" % ", ".join(cowards))
			reward_back = int(sum([tbw.get(a, 0.) for a in cowards]))*100000000
			forged = loadForge()
			forged["rewards"] = "%r" % (int(forged["rewards"])-reward_back)
			dumpForge(forged)
		newcomers = set(all_addresses) - set(tbw.keys())
		if len(newcomers):
			logMsg("up-voted by : %s" % ", ".join(newcomers))
		dumpTBW(OrderedDict(sorted([[a, tbw.get(a, 0.)+rewards[a]] for a in rewards.keys()], key=lambda e:e[-1], reverse=True)))


def extract():
	param = loadParam()
	data = OrderedDict(sorted([[a,w] for a,w in loadTBW().items()], key=lambda e:e[-1], reverse=True))
	
	threshold = param.get("threshold", 0.)
	tbw = OrderedDict([a,w] for a,w in data.items() if w >= threshold)
	amount = sum(tbw.values())
	saved = sum(w for w in data.values() if w < threshold)

	now = datetime.datetime.now(tz=pytz.UTC)
	dumpJson(
		{
			"timestamp": "%s" % now,
			"saved": saved,
			"amount": param.get("share", 1.0)*amount,
			"weight": OrderedDict(sorted([[a,w/amount] for a,w in tbw.items()], key=lambda e:e[-1], reverse=True))
		},
		os.path.join(ROOT, "%s.tbw" % now.strftime("%Y-%m-%d"))
	)
	dumpTBW(OrderedDict([a, 0. if a in tbw else w] for a,w in data.items()))


def forgery():
	logMsg("Distributed token : %.0f" % sum(loadTBW().values()))
