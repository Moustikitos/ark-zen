# -*- coding:utf8 -*-

from zen import crypto

import sys
import time
import json
import socket
import hashlib
import datetime
import socketserver

__PY3__ = True if sys.version_info[0] >= 3 else False

remaining = lambda: 60 - time.time()%60
elapsed = lambda: time.time()%60/60


class TCPHandler(socketserver.BaseRequestHandler):

	publicKey = None
	check = False

	def handle(self):
		signature = crypto.hexlify(self.request.recv(1024).strip())
		
		if TCPHandler.publicKey:
			try:
				TCPHandler.check = check(TCPHandler.publicKey, signature)
			except:
				pass
		else:
			TCPHandler.check = False
		if TCPHandler.check:
			self.request.sendall(b'{"granted":true}')
		else:
			self.request.sendall(b'{"granted":false}')
			

def seed():
	utc_data = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M Z")
	h = hashlib.sha256(utc_data if isinstance(utc_data, bytes) else utc_data.encode()).hexdigest()
	return h.encode("utf-8") if not isinstance(h, bytes) else h


def get(privateKey):
	return crypto.getSignatureFromBytes(seed(), privateKey)


def check(publicKey, signature):
	return crypto.verifySignatureFromBytes(seed(), publicKey, signature)


def post(privateKey, url):
	pass


def send(privateKey, host="localhost", port=9999):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((host, port))
	try:
		sign = get(privateKey)
	except:
		sign = crypto.hexlify(b"none")
	sock.sendall(crypto.unhexlify(sign))
	result = sock.recv(1024)
	sock.close()
	return json.loads(result.decode() if __PY3__ else result)["granted"]


def wait(publicKey, host="localhost", port=9999):
	# initialize values on TCPHandler class
	TCPHandler.publicKey = publicKey
	TCPHandler.check = False
	# create server waiting for signature
	server = socketserver.TCPServer((host, port), TCPHandler, bind_and_activate=False)
	# those lines below allow to reuse the port immediately after server close
	server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server.allow_reuse_addr = True
	server.server_bind()
	server.server_activate()
	# handle only one response and then close the server
	server.handle_request()
	server.socket.close()
	# return the result
	return TCPHandler.check
