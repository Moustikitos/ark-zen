# -*- coding:utf-8 -*-
import os
import sys
import zen


def getSnapshots(snapdir):
	snapshots = sorted([name for name in os.listdir(snapdir) if os.path.isdir(os.path.join(snapdir, name)) and name.startswith("1-")])
	if not len(snapshots):
		raise Exception("no snapshots initialized yet")
	return snapshots 


def createSnapshot():
	root = zen.loadJson("root.json")
	os.system('''
cd %(workdir)s
yarn create:%(network)s''' % {
	"workdir": os.path.join(root["node_folder"], "packages", "core-snapshots-cli"),
	"network": os.path.basename(root["config"]).replace(".json", "")
})


def updateSnapshot():
	root = zen.loadJson("root.json")
	workdir = os.path.join(root["node_folder"], "packages", "core-snapshots-cli")
	network = os.path.basename(root["config"]).replace(".json", "")
	snapdir = os.path.expanduser(os.path.join("~", ".ark", "snapshots", network))

	snapshots = getSnapshots(snapdir)
	if not os.system('''
cd %(workdir)s
yarn create:%(network)s -b %(snapshot)s''' % {
	"workdir": workdir,
	"network": os.path.basename(root["config"]).replace(".json", ""),
	"snapshot": snapshots[-1]
}):
		for snapshot in snapshots:
			os.system('rm -rf "%s"' % os.path.join(snapdir, snapshot))


def rebuildFromZero():
	root = zen.loadJson("root.json")
	workdir = os.path.join(root["node_folder"], "packages", "core-snapshots-cli")
	network = os.path.basename(root["config"]).replace(".json", "")
	snapdir = os.path.expanduser(os.path.join("~", ".ark", "snapshots", network))

	snapshots = getSnapshots(snapdir)

	os.system('''
cd %(workdir)s
pm2 stop ark-core-relay
pm2 stop ark-core-forger
yarn import:%(network)s -b %(snapshot)s --truncate
pm2 start ark-core-relay
pm2 start ark-core-forger
''' % {
	"workdir": workdir,
	"network": network,
	"snapshot": snapshots[-1]
})


def rollbackAndRebuild():
	root = zen.loadJson("root.json")
	workdir = os.path.join(root["node_folder"], "packages", "core-snapshots-cli")
	network = os.path.basename(root["config"]).replace(".json", "")
	snapdir = os.path.expanduser(os.path.join("~", ".ark", "snapshots", network))

	snapshots = getSnapshots(snapdir)
	blockstop = int(snapshots[-1].split("-")[-1]) - 500

	os.system('''
cd %(workdir)s
pm2 stop ark-core-relay
pm2 stop ark-core-forger
yarn rollback:%(network)s -b %(blockstop)s
yarn import:%(network)s -b %(snapshot)s
pm2 start ark-core-relay
pm2 start ark-core-forger
''' % {
	"workdir": workdir,
	"network": network,
	"blockstop": blockstop,
	"snapshot": snapshots[-1]
})
