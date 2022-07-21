# -*- coding:utf-8 -*-

import os
import math
import time
import json
import queue
import hashlib
import sqlite3
import datetime
import threading

from datetime import timezone
from collections import OrderedDict

import zen
import dposlib

from dposlib import rest
from dposlib.ark import slots
from zen import misc, biom, loadJson, dumpJson, logMsg

biom.load()


def initDb(username):
    sqlite = sqlite3.connect(os.path.join(zen.ROOT, "%s.db" % username))
    sqlite.row_factory = sqlite3.Row
    cursor = sqlite.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS transactions(filename TEXT, "
        "timestamp INTEGER, amount INTEGER, address TEXT, id TEXT);"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS tx_index ON "
        "transactions(id, address);")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS dilution(timestamp REAL, value REAL);"
    )
    sqlite.commit()
    return sqlite


def vacuumDb(username):
    sqlite = sqlite3.connect(
        os.path.join(zen.ROOT, "%s.db" % username),
        isolation_level=None
    )
    sqlite.execute(
        "DELETE FROM dilution WHERE timestamp NOT IN "
        "(SELECT MIN(timestamp) as timestamp FROM dilution GROUP BY value)"
    )
    sqlite.execute("VACUUM")
    sqlite.commit()
    sqlite.close()


def distributeRewards(rewards, uname, minvote=0, maxvote=None, excludes=[]):
    minvote *= 100000000
    if isinstance(maxvote, (int, float)):
        maxvote *= 100000000
        _max = lambda v, max=maxvote: min(max, v)
    else:
        _max = lambda v, max=maxvote: v

    voters = misc.loadPages(
        rest.GET.api.delegates.__getattr__(uname).voters
    )
    if len(voters) == 0:
        raise Exception("No voter found during distribution computation...")
    voters = dict(
        [v["address"], _max(float(v["balance"]))] for v in voters if
        v["address"] not in excludes and
        float(v["balance"]) >= minvote
    )
    total_balance = max(1, sum(voters.values()))
    # ARK Vote Dilution
    dilution_value = 100000000.0 / total_balance
    sqlite = initDb(uname)
    req = sqlite.execute(
        "SELECT * FROM dilution ORDER BY timestamp DESC LIMIT 1"
    ).fetchall()
    if len(req):
        value = req[0]["value"]
        if value != dilution_value:
            sqlite.execute(
                "INSERT INTO dilution(timestamp, value) VALUES(?,?);",
                (time.time(), dilution_value)
            )
            sqlite.commit()
    else:
        sqlite.execute(
            "INSERT INTO dilution(timestamp, value) VALUES(?,?);",
            (time.time(), dilution_value)
        )
        sqlite.commit()
    sqlite.close()
    return OrderedDict(
        sorted(
            [[a, b/total_balance*rewards] for a, b in voters.items()],
            key=lambda e: e[-1], reverse=True
        )
    )


def adjust(username, value):
    if biom.getPublicKeyFromUsername(username):
        blockreward = rest.cfg.blockreward
        folder = os.path.join(zen.DATA, username)
        forgery = loadJson("%s.forgery" % username, folder=folder)
        total = sum(forgery["contributions"].values())
        dumpJson(
            {
                "fees": forgery.get("fees", 0.),
                "blocks": int(math.ceil(value / blockreward)),
                "contributions": OrderedDict(
                    sorted(
                        [
                            [a, v/total*value]
                            for a, v in forgery["contributions"].items()
                        ],
                        key=lambda e: e[-1], reverse=True
                    )
                )
            },
            "%s.forgery" % username,
            folder=folder
        )
    else:
        logMsg("%s username does not exist" % username)


def extract(username):
    now = datetime.datetime.now(tz=timezone.utc)

    if biom.getPublicKeyFromUsername(username):
        param = loadJson("%s.json" % username)
        threshold = param.get("threshold", 0.2)
        share = param.get("share", 1.0)

        forgery = loadJson(
            "%s.forgery" % username, os.path.join(zen.DATA, username)
        )
        data = OrderedDict(
            sorted(
                [[a, w] for a, w in forgery.get("contributions", {}).items()],
                key=lambda e: e[-1], reverse=True
            )
        )
        tbw = OrderedDict(
            [a, w * share] for a, w in data.items() if w * share >= threshold
        )
        totalDistributed = sum(tbw.values())

        dumpJson(
            {
                "timestamp": "%s" % now,
                "delegate-share": round(
                    forgery.get("blocks", 0.) * dposlib.rest.cfg.blockreward
                    * (1.0 - share), 8
                ),
                "undistributed": round(
                    sum(w for w in data.values() if w < threshold), 8
                ),
                "distributed": round(totalDistributed, 8),
                "fees": round(forgery.get("fees", 0.), 8),
                "weight": OrderedDict(
                    sorted(
                        [[a, s/totalDistributed] for a, s in tbw.items()],
                        key=lambda e: e[-1],
                        reverse=True
                    )
                )
            },
            "%s.tbw" % now.strftime("%Y%m%d-%H%M"),
            folder=os.path.join(zen.ROOT, "app", ".tbw", username)
        )

        # reset forgery keeping unpaind voters
        forgery["contributions"] = OrderedDict(
            [a, 0. if a in tbw else w] for a, w in data.items()
        )
        forgery["blocks"] = 0
        forgery["fees"] = 0.
        dumpJson(
            forgery, "%s.forgery" % username, os.path.join(zen.DATA, username)
        )


def dumpRegistry(username, chunk_size=50):
    folder = os.path.join(zen.ROOT, "app", ".tbw", username)
    tbw_files = [n for n in os.listdir(folder) if n.endswith(".tbw")]
    if not len(tbw_files):
        return False

    KEYS01, KEYS02 = biom.getUsernameKeys(username)
    wallet = rest.GET.api.wallets(username).get("data", {})

    if KEYS01 and len(wallet):
        nonce = int(wallet.get("nonce", 0)) + 1
        config = loadJson("%s.json" % username)
        dposlib.core.Transaction.useDynamicFee(
            config.get("fee_level", None)
        )

        for name in tbw_files:
            data = loadJson(name, folder)
            amount = data["distributed"]

            totalFees = 0
            registry = OrderedDict()
            timestamp = slots.getTime()
            vendorField = config.get("vendorField", "%s reward" % username)

            weights = sorted(
                data["weight"].items(), key=lambda e: e[-1], reverse=True
            )

            if len(weights) < 3:
                for addr, wght in weights:
                    tx = dposlib.core.transfer(
                        round(amount * wght, 8), addr, vendorField
                    )
                    if "vendorFieldHex" in config:
                        tx.vendorFieldHex = config["vendorFieldHex"]
                    dict.__setitem__(tx, "senderPublicKey", wallet["publicKey"])
                    dict.__setitem__(tx, "nonce", nonce)
                    tx.senderId = wallet["address"]
                    tx.timestamp = timestamp
                    tx.fee = config.get("fee_level", None)
                    tx.feeIncluded = True
                    tx.signature = \
                        dposlib.core.crypto.getSignatureFromBytes(
                            dposlib.core.crypto.getBytes(tx),
                            KEYS01["privateKey"]
                        )
                    if KEYS02 is not None:
                        tx.signSignature = \
                            dposlib.core.crypto.getSignatureFromBytes(
                                dposlib.core.crypto.getBytes(tx),
                                KEYS02["privateKey"]
                            )
                    tx.id = \
                        dposlib.core.crypto.getIdFromBytes(
                            dposlib.core.crypto.getBytes(
                                tx, exclude_multi_sig=False
                            )
                        )
                    registry[tx["id"]] = tx
                    totalFees += tx["fee"]
                    nonce += 1

            else:
                while len(weights) % chunk_size <= 3:
                    chunk_size -= 1

                for chunk in [
                    weights[i:i+chunk_size]
                    for i in range(0, len(weights), chunk_size)
                ]:
                    transaction = dposlib.core.multiPayment(
                        *[[round(amount * wght, 8), addr] for addr, wght in chunk],
                        vendorField=vendorField
                    )
                    if "vendorFieldHex" in config:
                        transaction.vendorFieldHex = config["vendorFieldHex"]
                    dict.__setitem__(
                        transaction, "senderPublicKey", wallet["publicKey"]
                    )
                    dict.__setitem__(transaction, "nonce", nonce)
                    transaction.senderId = wallet["address"]
                    transaction.timestamp = timestamp
                    transaction.fee = config.get("fee_level", None)
                    transaction.signature = \
                        dposlib.core.crypto.getSignatureFromBytes(
                            dposlib.core.crypto.getBytes(transaction),
                            KEYS01["privateKey"]
                        )
                    if KEYS02 is not None:
                        transaction.signSignature = \
                            dposlib.core.crypto.getSignatureFromBytes(
                                dposlib.core.crypto.getBytes(transaction),
                                KEYS02["privateKey"]
                            )
                    transaction.id = \
                        dposlib.core.crypto.getIdFromBytes(
                            dposlib.core.crypto.getBytes(
                                transaction, exclude_multi_sig=False
                            )
                        )
                    registry[transaction["id"]] = transaction
                    totalFees += transaction["fee"]
                    nonce += 1

            totalFees /= 100000000.0
            if config.get("wallet", False):
                transaction0 = dposlib.core.transfer(
                    round(
                        data["delegate-share"] + data["fees"] - totalFees, 8
                    ),
                    config["wallet"], "%s share" % username,
                )
                dict.__setitem__(
                    transaction0, "senderPublicKey", wallet["publicKey"]
                )
                dict.__setitem__(transaction0, "nonce", nonce)
                transaction0.senderId = wallet["address"]
                transaction0.timestamp = timestamp
                transaction0.fee = config.get("fee_level", None)
                transaction0.feeIncluded = True
                transaction0.signature = \
                    dposlib.core.crypto.getSignatureFromBytes(
                        dposlib.core.crypto.getBytes(transaction0),
                        KEYS01["privateKey"]
                    )
                if KEYS02 is not None:
                    transaction0.signSignature = \
                        dposlib.core.crypto.getSignatureFromBytes(
                            dposlib.core.crypto.getBytes(transaction0),
                            KEYS02["privateKey"]
                        )
                transaction0.id = \
                    dposlib.core.crypto.getIdFromBytes(
                        dposlib.core.crypto.getBytes(
                            transaction0, exclude_multi_sig=False
                        )
                    )
                registry[transaction0["id"]] = transaction0

            dumpJson(
                registry,
                "%s.registry" % os.path.splitext(name)[0],
                os.path.join(zen.DATA, username)
            )
            data["covered fees"] = totalFees
            dumpJson(data, name, os.path.join(folder, "history"))
            os.remove(os.path.join(folder, name))

    return True


# TODO: fix it
def waitForDelegate(publicKey):
    slot = zen.biom.getRoundOrder().index(publicKey) + 1
    if slot > 0:
        blocktime = rest.cfg.blocktime
        activeDelegates = rest.cfg.activeDelegates
        activeDelegatesMilestone = getattr(
            rest.cfg, "activeDelegatesMilestone", 1
        )
        height = rest.GET.api.blockchain(
            returnKey="data"
        ).get("block", {}).get("height", False)

        if not height:
            return

        current_slot = (height - activeDelegatesMilestone) % activeDelegates
        wait_delay = ((slot - current_slot) % activeDelegates) * blocktime
        delay = wait_delay + blocktime - time.time() % blocktime
        zen.logMsg("waiting %.2f seconds for %s slot..." % (delay, publicKey))

        try:
            threading.Event().wait(
                wait_delay + blocktime - time.time() % blocktime
            )
        except KeyboardInterrupt:
            pass


def broadcast(username, chunk_size=30):
    # initialize options
    config = loadJson("root.json")
    chunk_size = max(5, config.get("chunk_size", chunk_size))
    folder = os.path.join(zen.DATA, username)

    # proceed all registry file found in username folder
    for name in [n for n in os.listdir(folder) if n.endswith(".registry")]:
        registry = loadJson(name, folder=folder)
        transactions = sorted(
            list(registry.values()), key=lambda t: t.get("nonce", 0)
        )
        for chunk in (
            transactions[x:x+chunk_size]
            for x in range(0, len(transactions), chunk_size)
        ):
            response = rest.POST.api.transactions(
                transactions=chunk, peer=zen.API_PEER
            )
            logMsg(
                "chunk of transactions broadcasted to %s...\n%s" % (
                    zen.API_PEER, json.dumps(response, indent=2)
                )
            )
        misc.notify(
            "New payroll started : %d transactions sent to delegate node..." %
            len(transactions)
        )


def updateRegistryNonces(username):
    folder = os.path.join(zen.DATA, username)
    registries = [n for n in os.listdir(folder) if n.endswith(".registry")]
    if not len(registries):
        return False

    KEYS01, KEYS02 = biom.getUsernameKeys(username)
    wallet = rest.GET.api.wallets(username).get("data", {})
    nonce = int(wallet["nonce"]) + 1

    if KEYS01 and len(wallet):
        for name in registries:
            full_registry = loadJson(name, folder=folder)
            registry = loadJson(name+".milestone", folder=folder)
            if len(registry):
                logMsg(
                    "updating transaction nonces in %s..." %
                    (name+".milestone")
                )
                for tx in list(registry.values()):
                    old_id = tx["id"]
                    new_tx = dposlib.core.Transaction(tx)
                    new_tx.nonce = nonce
                    nonce += 1
                    new_tx.signWithKeys(
                        KEYS01["publicKey"], KEYS01["privateKey"]
                    )
                    if KEYS02 is not None:
                        new_tx.signSignWithKey(KEYS02["privateKey"])
                    new_tx.identify()
                    registry.pop(old_id)
                    full_registry.pop(old_id)
                    registry[new_tx["id"]] = new_tx
                    full_registry[new_tx["id"]] = new_tx
            dumpJson(registry, name+".milestone", folder=folder)
            dumpJson(full_registry, name, folder=folder)

    return True


def regenerateUnapplied(username, filename):
    registry = zen.loadJson(
        "%s.registry" % filename, os.path.join(zen.DATA, username)
    )
    tbw = zen.loadJson(
        "%s.tbw" % filename, os.path.join(zen.TBW, username, "history")
    )

    for tx in registry.values():
        if not biom.transactionApplied(tx["id"]):
            zen.logMsg(
                'tx %(id)s [%(amount)s --> %(recipientId)s] unapplied' % tx
            )
        else:
            tbw["weight"].pop(tx["recipientId"], False)

    zen.dumpJson(
        tbw, '%s-unapplied.tbw' % filename, os.path.join(zen.TBW, username)
    )


def checkApplied(username):
    folder = os.path.join(zen.DATA, username)
    sqlite = initDb(username)
    cursor = sqlite.cursor()

    for name in [n for n in os.listdir(folder) if n.endswith(".registry")]:
        full_registry = loadJson(name, folder=folder)
        # try to lad a milestone first, if no one exists
        registry = loadJson(name+".milestone", folder=folder)
        # if void dict returned by loadJson, then load registry file
        if not len(registry):
            registry = dict(full_registry)
            logMsg("starting transaction check from %s..." % name)
        else:
            logMsg(
                "resuming transaction check from %s..." % (name+".milestone")
            )

        start = time.time()
        transactions = list(registry.values())
        for tx in transactions:
            if biom.transactionApplied(tx["id"]):
                logMsg(
                    "transaction %(id)s <type %(type)s> applied" %
                    registry.pop(tx["id"])
                )
                if "payments" in tx.get("asset", {}):
                    for record in tx["asset"]["payments"]:
                        cursor.execute(
                            "INSERT OR REPLACE INTO transactions("
                            "filename, timestamp, amount, address, id"
                            ") VALUES(?,?,?,?,?);", (
                                os.path.splitext(name)[0],
                                tx["timestamp"],
                                int(record["amount"])/100000000.,
                                record["recipientId"],
                                tx["id"]
                            )
                        )
                else:
                    cursor.execute(
                        "INSERT OR REPLACE INTO transactions("
                        "filename, timestamp, amount, address, id"
                        ") VALUES(?,?,?,?,?);", (
                            os.path.splitext(name)[0],
                            tx["timestamp"],
                            int(tx["amount"])/100000000.,
                            tx["recipientId"],
                            tx["id"]
                        )
                    )
            # set a milestone every 5 seconds
            if (time.time() - start) > 5.:
                sqlite.commit()
                dumpJson(registry, name+".milestone", folder=folder)
                logMsg(
                    "milestone set (%d transaction left to check)" %
                    len(registry)
                )
                start = time.time()
        dumpJson(registry, name+".milestone", folder=folder)
        sqlite.commit()

        if len(registry) == 0:
            dumpJson(
                full_registry, name, folder=os.path.join(folder, "backup")
            )
            try:
                os.remove(os.path.join(folder, name))
                os.remove(os.path.join(folder, name+".milestone"))
            except Exception:
                pass
            checked_tx = full_registry.values()
            misc.notify(
                "Payroll successfully broadcasted !\n"
                "%.8f token sent trough %d transactions" % (
                    sum(
                        [
                            sum([
                                int(rec["amount"])
                                for rec in tx["asset"].get("payments", [])
                            ]) for tx in checked_tx
                        ]
                    )/100000000.,
                    len(checked_tx)
                )
            )
        else:
            misc.notify(
                "Transactions are still to be checked (%d)..." % len(registry)
            )


def computeDelegateBlock(username, block):
    # get reward and fee fome the given block
    rewards = float(block["reward"])/100000000.
    fees = (float(block["totalFee"]) - float(block.get("burnedFee", 0)))/100000000.
    blocks = 1
    logMsg(
        "getting rewards and fees from forged block %s: %r|%r"
        % (block["id"], rewards, fees)
    )

    # Compare the ids of last forged blocks
    # to compute rewards and fees...
    publicKey = block["generatorPublicKey"]
    filename = "%s.last.block" % username
    folder = os.path.join(zen.DATA, username)
    last_block = loadJson(filename, folder=folder)
    # if there is a <username>.last.block
    if last_block.get("id", False):
        logMsg("last known forged: %s" % last_block["id"])
        # get all blocks till the last forged
        req, last_blocks, page = {}, [], 1
        last_height = last_block["height"]
        while req.get("data", [{}])[-1].get(
            "height", last_height + 1
        ) > last_height:
            req = rest.GET.api.delegates(publicKey, "blocks", page=page)
            last_blocks.extend(req.get("data", []))
            page += 1
        # raise Exceptions if issues with API call
        if not len(last_blocks):
            raise Exception("No block found in peer response")
        elif req.get("error", False) is not False:
            raise Exception("Api error : %r" % req.get("error", "?"))
        # compute fees, blocs and rewards from the last saved block
        for blk in last_blocks:
            _id = blk["id"]
            if _id == block["id"]:
                pass
            # stop the loop when last forged block is reach in the last blocks
            # list
            elif _id == last_block["id"]:
                logMsg("    nothing more since block %s" % _id)
                break
            # if bc is not synch and response is too bad, also check timestamp
            else:
                if blk["timestamp"]["epoch"] > last_block["timestamp"]:
                    reward = float(blk["forged"]["reward"])/100000000.
                    fee = (
                        float(blk["forged"]["fee"]) -
                        float(blk["forged"].get("burnedFee", 0))
                    )/100000000.
                    logMsg(
                        "    getting rewards and fees from block %s: %r|%r"
                        % (_id, reward, fee)
                    )
                    rewards += reward
                    fees += fee
                    blocks += 1
                else:
                    logMsg("    ignoring block %s (previously forged)" % _id)
    # else initiate <username>.last.block
    else:
        dumpJson(block, filename, folder=folder)
        raise Exception("First iteration for %s" % username)

    # find forger information using username and compute the reward
    # distribution excluding delegate
    forger = loadJson("%s.json" % username)
    forgery = loadJson("%s.forgery" % username, folder=folder)
    address = dposlib.core.crypto.getAddress(publicKey)
    excludes = forger.get("excludes", [address])
    if address not in excludes:
        excludes.append(address)
    contributions = distributeRewards(
        rewards, username,
        minvote=forger.get("minimum_vote", 0),
        maxvote=forger.get("maximum_vote", None),
        excludes=excludes
    )
    # dump true block weight data
    _ctrb = forgery.get("contributions", {})
    dumpJson(
        {
            "fees": forgery.get("fees", 0.) + fees,
            "blocks": forgery.get("blocks", 0) + blocks,
            "contributions": OrderedDict(
                sorted(
                    [
                        [a, _ctrb.get(a, 0.) + contributions[a]]
                        for a in contributions
                    ],
                    key=lambda e: e[-1],
                    reverse=True
                )
            )
        },
        "%s.forgery" % username,
        folder=folder
    )
    # dump current forged block as <username>.last.block
    dumpJson(block, filename, folder=folder)

    # notify vote movements
    msg = "\n".join(
        [
            "%s removed from %s list [%.8f Arks]" %
            (misc.shorten(wallet), username, _ctrb[wallet])
            for wallet in [w for w in _ctrb if w not in contributions]
        ] + [
            "%s added to %s list" % (misc.shorten(wallet), username)
            for wallet in [w for w in contributions if w not in _ctrb]
        ]
    )
    registry = execute_payroll(
        username, *[
            [wallet, _ctrb[wallet]]
            for wallet in [w for w in _ctrb if w not in contributions]
        ],
        vendorField=f"{username} residual share"
    )
    dumpJson(registry, f"{block['height']}.downvote.milestone", folder=folder)
    logMsg(
        "checking vote changes..." +
        (" nothing hapened !" if msg == "" else ("\n%s" % msg))
    )
    if msg != "":
        misc.notify(msg)


def execute_payroll(username, *pairs, **kwargs):
    KEYS01, KEYS02 = biom.getUsernameKeys(username)
    wallet = rest.GET.api.wallets(username).get("data", {})
    vendorField = kwargs.get("vendorField", f"{username} share")
    vendorFieldHex = kwargs.get("vendorFieldHex", None)
    nonce = int(wallet["nonce"]) + 1
    dlgt_puk = wallet["publicKey"]
    dlgt_addr = wallet["address"]
    registry = {}
    assert KEYS01["publicKey"] == dlgt_puk

    if len(pairs) < 3:
        for addr, amount in pairs:
            tx = dposlib.core.transfer(round(amount, 8), addr, vendorField)
            dict.__setitem__(tx, "senderPublicKey", dlgt_puk)
            dict.__setitem__(tx, "nonce", nonce)
            if vendorFieldHex is not None:
                tx.vendorFieldHex = vendorFieldHex
            tx.senderId = dlgt_addr
            tx.fee = "minFee"
            tx.feeIncluded = True
            tx.signature = dposlib.core.crypto.getSignatureFromBytes(
                dposlib.core.crypto.getBytes(tx),
                KEYS01["privateKey"]
            )
            if KEYS02 is not None:
                tx.signSignature = dposlib.core.crypto.getSignatureFromBytes(
                    dposlib.core.crypto.getBytes(tx),
                    KEYS02["privateKey"]
                )
            tx.id = dposlib.core.crypto.getIdFromBytes(
                dposlib.core.crypto.getBytes(
                    tx, exclude_multi_sig=False
                )
            )
            registry[tx["id"]] = tx
            nonce += 1

    else:
        chunk_size = 50
        while len(pairs) % chunk_size <= 3:
            chunk_size -= 1

        for chunk in [
            pairs[i:i+chunk_size]
            for i in range(0, len(pairs), chunk_size)
        ]:
            tx = dposlib.core.multiPayment(
                *[[round(amount, 8), addr] for addr, amount in chunk],
                vendorField=vendorField
            )
            dict.__setitem__(tx, "senderPublicKey", wallet["publicKey"])
            dict.__setitem__(tx, "nonce", nonce)
            if vendorFieldHex is not None:
                tx.vendorFieldHex = vendorFieldHex
            tx.senderId = wallet["address"]
            tx.fee = "minFee"
            tx.signature = dposlib.core.crypto.getSignatureFromBytes(
                dposlib.core.crypto.getBytes(tx),
                KEYS01["privateKey"]
            )
            if KEYS02 is not None:
                tx.signSignature = dposlib.core.crypto.getSignatureFromBytes(
                    dposlib.core.crypto.getBytes(tx),
                    KEYS02["privateKey"]
                )
            tx.id = dposlib.core.crypto.getIdFromBytes(
                dposlib.core.crypto.getBytes(
                    tx, exclude_multi_sig=False
                )
            )
            registry[tx["id"]] = tx
            nonce += 1

    return registry


class TaskExecutioner(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()

    @staticmethod
    def killall():
        TaskExecutioner.STOP.set()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        zen.logMsg("TaskExecutioner instance set: %r" % self)

    def run(self):
        # controled infinite loop
        while not TaskExecutioner.STOP.is_set():
            try:
                auth, block = TaskExecutioner.JOB.get()
                if not block:
                    raise Exception("Error: can not read data")
                else:
                    publicKey = block["generatorPublicKey"]
                username = zen.biom.getUsernameFromPublicKey(publicKey)
                if not username:
                    raise Exception("Error: can not reach username")
                # check autorization and exit if bad one
                webhook = zen.loadJson("%s-webhook.json" % username)
                if webhook.get("hash", "") != hashlib.sha256(
                    (auth + webhook["token"]).encode("utf-8")
                ).hexdigest():
                    raise Exception("Not autorized here")
                computeDelegateBlock(username, block)
            except Exception as error:
                logMsg("%r" % error)
