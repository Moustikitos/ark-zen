# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities
for DPOS pool management.

## Supported blockchain

 * [X] Ark-v2

## Install

```bash
wget https://raw.githubusercontent.com/Moustikitos/zen/master/bash/zen-install.sh
bash zen-install.sh
```

## Initialize blockchain/delegates

```bash
./zen-run initialize
```

## Start/stop True Block Weight

```bash
./zen-run start-tbw
./zen-run stop-tbw
```

## Configure options

```bash
./zen-run configure [-u username] [-o value] [--options=values]
```

## Launch a payroll

```bash
./zen-run launch-payroll -u username
```
