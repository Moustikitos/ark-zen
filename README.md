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

## Available commands

```bash
cd ~
./zen-run
Usage:
    zen-run reset
    zen-run initialize
    zen-run configure <username> [-s <share> -f <fund> -t <threshold> -e <excludes>]
    zen-run configure [-c <currency> -b <block-delay>]
    zen-run start-tbw
    zen-run stop-tbw
    zen-run launch-payroll <username>
    zen-run resume-payroll <username>
```
