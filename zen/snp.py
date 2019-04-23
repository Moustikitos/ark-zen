# -*- coding:utf-8 -*-
import os
import sys
import zen
import zen.misc


def getSnapshots(snapdir):
	snapshots = sorted([name for name in os.listdir(snapdir) if os.path.isdir(os.path.join(snapdir, name)) and name.startswith("1-")])
	if not len(snapshots):
		raise Exception("no snapshots initialized yet")
	return snapshots 


def createSnapshot():
	if not os.system('ark snapshot:dump'):
		zen.misc.notify("Blockchain snapped !")


def updateSnapshot():
	root = zen.loadJson("root.json")
	network = root["name"]
	appname = os.path.basename(root["config_folder"])
	snapdir = os.path.expanduser(os.path.join("~", ".local", "share", appname, network, "snapshots"))
	snapshots = getSnapshots(snapdir)

	if not os.system('ark snapshot:dump --blocks %(snapshot)s' % {"snapshot": snapshots[-1]}):
		for snapshot in snapshots:
			os.system('rm -rf "%s"' % os.path.join(snapdir, snapshot))
		zen.misc.notify("Blockchain snapped !")
	os.system('cd ~ && tar cf ~/last-snapshot.tar .local/share/ark-core/%(network)s/snapshots/1-*' % {"network": network})


def rebuildFromZero():
	root = zen.loadJson("root.json")
	appname = os.path.basename(root["config_folder"])
	snapdir = os.path.expanduser(os.path.join("~", ".local", "share", appname, root["name"], "snapshots"))
	snapshots = getSnapshots(snapdir)

	zen.misc.stop_pm2_app("ark-core")
	zen.misc.stop_pm2_app("ark-forger")
	zen.misc.stop_pm2_app("ark-relay")
	os.system('ark snapshot:restore --blocks %(snapshot)s --truncate' % {"snapshot": snapshots[-1]})
	zen.misc.start_pm2_app("ark-relay")
	zen.misc.start_pm2_app("ark-forger")


def rollbackAndRebuild():
	root = zen.loadJson("root.json")
	appname = os.path.basename(root["config_folder"])
	snapdir = os.path.expanduser(os.path.join("~", ".local", "share", appname, root["name"], "snapshots"))
	snapshots = getSnapshots(snapdir)
	blockstop = int(snapshots[-1].split("-")[-1]) - 500

	zen.misc.stop_pm2_app("ark-core")
	zen.misc.stop_pm2_app("ark-forger")
	zen.misc.stop_pm2_app("ark-relay")
	os.system('''
ark snapshot:rollback --height %(blockstop)s
ark snapshot:restore --blocks %(snapshot)s
''' % {
	"blockstop": blockstop,
	"snapshot": snapshots[-1]
})
	zen.misc.start_pm2_app("ark-relay")
	zen.misc.start_pm2_app("ark-forger")
