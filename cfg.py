# -*- encoding:utf-8 -*-
import os
import sys
import optparse

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import zen
import zen.tbw


# def rebuild(url, dbname, snapshot="~/snapshot"):
# 	os.system(
# """
# pm2 stop all
# pm2 delete all
# sudo -u postgres dropdb --if-exists %(dbname)s
# createdb %(dbname)s
# wget %(url)s %(snapshot)s
# pg_restore -O -j 8 -d %(dbname)s %(snapshot)s
# """ % {"dbname":dbname, url":url, "snapshot":snapshot}
# )


def start():
	# os.chdir(os.path.abspath(os.path.dirname(__file__)))
	os.system("""
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
	cd %(abspath)s
    pm2 start app.json
else
    pm2 restart zen-tbw
fi
""" % {"abspath": os.path.abspath(os.path.dirname(__file__))})


def stop():
	os.chdir(os.path.abspath(os.path.dirname(__file__)))
	os.system("""
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
    pm2 stop zen-tbw
fi
""")


def initialize():
	zen.init()
	zen.tbw.init()


def pay(username):
	zen.tbw.extract(username)
	zen.tbw.dumpRegistry(username)
	zen.tbw.broadcast(username)


if __name__ == "__main__":
	tbw = zen.loadJson("tbw.json")

	# catch command line
	parser = optparse.OptionParser()
	# -f --funds
	# -s --symbol
	# -d --delay
	# -e --excludes
	# -u --username
	(options, args) = parser.parse_args()

	if len(args):
		func = getattr(sys.modules[__name__], args[0])
		if callable(func):
			func()
