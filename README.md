# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities
for DPOS pool management.

## Supported blockchain

 * [X] Ark-v2

## Install

### Dependencies

```bash
sudo apt-get install python
sudo apt-get install python-setuptools
sudo apt-get install python-pip
```

### Zen

```bash
cd ~
git clone https://github.com/Moustikitos/zen.git
```

Install dependencies

```bash
cd zen
pip install -r requirement.txt
```

## Start

```bash
cd zen
python cfg.py initialize
pm2 start app.json
```
