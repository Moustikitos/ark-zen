# -*- encoding:utf-8 -*-

from zen.cmn import loadJson, dumpJson, logMsg, getBestSeed
from zen.chk import loadConfig
from collections import OrderedDict

import io
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

def readARKWalletAmount(walletAddress):
	config=loadConfig()
	response = requests.get(getBestSeed(*config['seeds'])+"/api/accounts/getBalance?address=%s" % walletAddress)
	balance = response.json().get("balance", {})
	if balance:	
		return float(response.json()["balance"])
	else: return 0.0

def readARKdelegateVote(delegateName):
	config=loadConfig()
	delegateInfo=requests.get(getBestSeed(*config['seeds'])+"/api/delegates/search?q=%s" % delegateName).json().get("delegates", {})
	if delegateInfo:
		return float(delegateInfo.pop()['vote'])
	else: return 1.0


def rewardCalculation(walletAddress, delegateName, period=7):
	"""get the reward calculation for period (in days)
		return a dict info
		info['walletAddress'] = walletAddress
		info['walletAmount'] = token amount for wallet address
		info['walletAddressRatio'] = ratio for the wallet among voters
		info['reward'] = reward calculation for the walletAddress for the period
		info['period'] = period in days
	"""
	info = {}
	config=loadConfig()
	tbw = loadParam()
	reward = requests.get(getBestSeed(*config['seeds'])+'/api/blocks/getReward').json().get("reward", {})
			
	arkForged = (period * 3600 * 24) / (config['blocktime'] * config['delegates']) * reward
	info['walletAddress'] = walletAddress
	info['walletAmount'] = readARKWalletAmount(walletAddress)
	info['walletAddressRatio'] = info['walletAmount']/(readARKdelegateVote(delegateName)+info['walletAmount'])
	info['reward'] = (arkForged * info['walletAddressRatio'] * tbw['share'])/100000000
	info['walletAmount'] /=100000000
	info['period'] = period
	return info

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
		out = io.open(os.path.join(ROOT, NAME+".log"), "a")
		all_addresses = list(rewards.keys())
		cowards = set(tbw.keys()) - set(all_addresses)
		if len(cowards):
			logMsg("down-voted by : %s" % ", ".join(cowards), stdout=out)
			reward_back = int(sum([tbw.get(a, 0.) for a in cowards]))*100000000
			forged = loadForge()
			forged["rewards"] = "%r" % (int(forged["rewards"])-reward_back)
			dumpForge(forged)
		newcomers = set(all_addresses) - set(tbw.keys())
		if len(newcomers):
			logMsg("up-voted by : %s" % ", ".join(newcomers), stdout=out)
		dumpTBW(OrderedDict(sorted([[a, tbw.get(a, 0.)+rewards[a]] for a in rewards.keys()], key=lambda e:e[-1], reverse=True)))
		out.close()


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
