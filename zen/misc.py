# -*- coding:utf-8 -*-

from zen import tbw


def transactionApplied(id):
	return tbw.rest.GET.api.v2.transactions(id).get("data",{}).get("confirmations", 0) >= 1


def regenerateUnapplied(username, filename):
	registry = zen.loadJson("%s.registry" % filename, os.path.join(zen.DATA, username))
	tbw = zen.loadJson("%s.tbw" % filename, os.path.join(zen.TBW, username))

	for tx in registry.values():
		if not transactionApplied(tx["id"]):
			zen.logMsg('tx %(id)s [%(amount)s --> %(recipientId)s] unapplied' % tx)
		else:
			tbw["weight"].pop(tx["recipientId"], False)
	
	zen.dumpJson(tbw,'%s-unapplied.tbw' % filename, os.path.join(zen.TBW, username))		 
