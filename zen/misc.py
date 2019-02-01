# -*- coding:utf-8 -*-

import zen
# from zen import tbw


def transactionApplied(id):
	return zen.tbw.rest.GET.api.v2.transactions(id).get("data",{}).get("confirmations", 0) >= 1


def regenerateUnapplied(username, filename):
	registry = zen.loadJson("%s.registry" % filename, os.path.join(zen.DATA, username))
	tbw = zen.loadJson("%s.tbw" % filename, os.path.join(zen.TBW, username, "history"))

	for tx in registry.values():
		if not transactionApplied(tx["id"]):
			zen.logMsg('tx %(id)s [%(amount)s --> %(recipientId)s] unapplied' % tx)
		else:
			tbw["weight"].pop(tx["recipientId"], False)
	
	zen.dumpJson(tbw,'%s-unapplied.tbw' % filename, os.path.join(zen.TBW, username))


def loadPages(endpoint, pages=None, quiet=True, nb_tries=10):
	if not isinstance(endpoint, zen.rest.EndPoint):
		raise Exception("Invalid endpoint class")
	count, pageCount, data = 0, 1, []
	while count < pageCount:
		req = endpoint.__call__(page=count+1)
		if req.get("error", False):
			nb_tries -= 1
			if not quiet:
				zen.logMsg("Api error occured... [%d tries left]" % nb_tries)
			if nb_tries <= 0:
				raise Exception("Api error occured: %r" % req)
		else:
			pageCount = req["meta"]["pageCount"]
			if isinstance(pages, int):
				pageCount = min(pages, pageCount)
			if not quiet:
				zen.logMsg("reading page %s over %s" % (count+1, pageCount))
			data.extend(req.get("data", []))
			count += 1
	return data


def loadCryptoCompareYearData(year, reference, interest):
	req = zen.rest.GET.data.histoday(
		peer="https://min-api.cryptocompare.com",
		fsym=reference,
		tsym=interest,
		limit=365,
		toTs=int(datetime.datetime(year, 12, 31, 23, 59).timestamp())
		)
	if req["Response"] == "Success":
		return req["Data"]
	else:
		raise Exception("can not reach data")
