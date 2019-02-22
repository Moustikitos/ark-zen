# -*- coding:utf-8 -*-
import os
import sys
import zen

WORKDIR = os.path.expanduser("~/.config/yarn/global/node_modules/@arkecosystem/core-snapshots-cli")

def getSnapshots(snapdir):
	snapshots = sorted([name for name in os.listdir(snapdir) if os.path.isdir(os.path.join(snapdir, name)) and name.startswith("1-")])
	if not len(snapshots):
		raise Exception("no snapshots initialized yet")
	return snapshots 


def createSnapshot():
	root = zen.loadJson("root.json")
	os.system('''
cd %(workdir)s
yarn dump:%(network)s''' % {
	"workdir": WORKDIR,
	"network": root["name"]
})


def updateSnapshot():
	root = zen.loadJson("root.json")
	network = root["name"]
	snapdir = os.path.expanduser(os.path.join("~", ".local", "share", "ark-core", network, "snapshots"))

	snapshots = getSnapshots(snapdir)
	if not os.system('''
cd %(workdir)s
yarn dump:%(network)s --blocks %(snapshot)s''' % {
	"workdir": WORKDIR,
	"network": network,
	"snapshot": snapshots[-1]
}):
		for snapshot in snapshots:
			os.system('rm -rf "%s"' % os.path.join(snapdir, snapshot))


def rebuildFromZero():
	root = zen.loadJson("root.json")
	network = root["name"]
	snapdir = os.path.expanduser(os.path.join("~", ".local", "share", "ark-core", network, "snapshots"))

	snapshots = getSnapshots(snapdir)

	os.system('''
cd %(workdir)s
pm2 stop ark-core-relay
pm2 stop ark-core-forger
yarn restore:%(network)s --blocks %(snapshot)s --truncate
pm2 start ark-core-relay
pm2 start ark-core-forger
''' % {
	"workdir": WORKDIR,
	"network": network,
	"snapshot": snapshots[-1]
})


def rollbackAndRebuild():
	root = zen.loadJson("root.json")
	network = root["name"]
	snapdir = os.path.expanduser(os.path.join("~", ".local", "share", "ark-core", network, "snapshots"))

	snapshots = getSnapshots(snapdir)
	blockstop = int(snapshots[-1].split("-")[-1]) - 500

	os.system('''
cd %(workdir)s
pm2 stop ark-core-relay
pm2 stop ark-core-forger
yarn rollback:%(network)s --blocks %(blockstop)s
yarn restore:%(network)s --blocks %(snapshot)s
pm2 start ark-core-relay
pm2 start ark-core-forger
''' % {
	"workdir": WORKDIR,
	"network": network,
	"blockstop": blockstop,
	"snapshot": snapshots[-1]
})
