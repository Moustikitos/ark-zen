# `zen`

`zen` package, entirely writen in python, provides failover routines for DPOS
nodes and `True Block Weight` utilities for pool management.

## Supported blockchain

 * [X] Ark-v2

## Install

### Dependencies

  - OS related
    * [X] `daemon` : `sudo apt-get install daemon`
    * [X] `python` : `sudo apt-get install python`
    * [X] `setuptools` : `sudo apt-get install python-setuptools`
    * [X] `pip` : `sudo apt-get install python-pip`

  - Python related (automatically managed by `pip`)
    * [X] `pytz`
    * [X] `ecdsa`
    * [X] `base58`
    * [X] `requests`
    * [X] `flask`
    * [X] `flask_bootstrap`

### using `pip`

`pip install https://github.com/Moustikitos/zen/archive/master.zip`

### using zip archive or `git`

Download and extract https://github.com/Moustikitos/zen/archive/master.zip 

or 

`git clone https://github.com/Moustikitos/zen.git`

then install dependencies

```bash
cd zen
pip install -r requirement.txt
```
