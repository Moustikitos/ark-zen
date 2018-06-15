# -*- coding:utf-8 -*-
# created by Toons on 01/05/2017
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup


with open("VERSION") as f1, open("README.md") as f2:
	VERSION = f1.read().strip()
	LONG_DESCRIPTION = f2.read()

kw = {
	"version": VERSION,
	"name": "Zen",
	"keywords": ["blockchain", "ark-v2"],
	"author": "Toons",
	"author_email": "moustikitos@gmail.com",
	"maintainer": "Toons",
	"maintainer_email": "moustikitos@gmail.com",
	"url": "https://github.com/Moustikitos/zen",
	"download_url": "https://github.com/Moustikitos/zen/archive/master.zip",
	"include_package_data": True,
	"description": "Failover tool for ARK delegate",
	"long_description": LONG_DESCRIPTION,
	"packages": ["zen", "zen.app"],
	"install_requires": ["requests", "ecdsa", "pytz", "babel", "base58", "flask", "flask_bootstrap"],
	"scripts": [
		"bin/zen-cmd.py",
		"bin/tfa-tk.py"
	],
	"license": "Copyright 2016-2017 Toons, Copyright 2017 ARK, MIT licence",
	"classifiers": [
		"Development Status :: 2 - Pre-Alpha",
		"Environment :: Console",
		"Environment :: Web Environment",
		"Intended Audience :: Developers",
		"Intended Audience :: End Users/Desktop",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
		"Programming Language :: Python",
		"Programming Language :: Python :: 2",
		"Programming Language :: Python :: 3",
	],
}

setup(**kw)
