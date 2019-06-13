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
	"name": "zen",
	"keywords": ["tbw", "ark-v2"],
	"author": "Toons",
	"author_email": "moustikitos@gmail.com",
	"maintainer": "Toons",
	"maintainer_email": "moustikitos@gmail.com",
	"url": "https://github.com/Moustikitos/zen",
	"download_url": "https://github.com/Moustikitos/zen/archive/master.zip",
	"include_package_data": True,
	"description": "Tool for ARK delegate",
	"long_description": LONG_DESCRIPTION,
	"long_description_content_type": "text/markdown",
	"packages": ["zen", "zen.app"],
	"install_requires": ["docopt", "dposlib==0.2.1", "flask", "gunicorn", "pygal"],
	"license": "Copyright 2016-2019 Toons",
	"classifiers": [
		"Development Status :: 6 - Mature",
		"Environment :: Console",
		"Environment :: Web Environment",
		"Framework :: Flask",
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
