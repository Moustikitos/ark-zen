# `zen`

`zen` package, entirely written in python, provides `True Block Weight` utilities for DPOS pool.

### Support this project
 
[![Liberapay receiving](https://img.shields.io/liberapay/goal/Toons?logo=liberapay)](https://liberapay.com/Toons/donate)

[Buy &#1126;](https://bittrex.com/Account/Register?referralCode=NW5-DQO-QMT) and:

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://dpos.arky-delegate.info/arky)

## Supported blockchain

 * [X] Ark

## Install

### Last release

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-zen/master/bash/zen-install.sh) 3.1.0
```

### Development version

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-zen/master/bash/zen-install.sh)
```

### First launch

```bash
cd ~
ark-zen/bash/activate
./zen initialize
./zen deploy-srv
```

## `zen` command

```bash
./zen --help

Usage:
    zen add-delegate <username> [-h <webhook-peer>]
    zen configure [--chunk-size <chubk-size> --fee-coverage]
    zen configure <username> [-s <share> -w <wallet> -e <excludes> -b <block-delay> -f <fee-level>]
    zen configure <username> [-m <minimum-vote> -M <maximum-vote> -t <threshold>]
    zen deploy-srv [--ip-address <ip-address> -p <port>]
    zen (reset | initialize | backup-data | remove-custom-peer)
    zen (deploy-srv | restart-srv | stop-srv | log-zen | log-bg)
    zen (launch-payroll | resume-payroll | retry-payroll | check-applied | remove-delegate) <username>
    zen adjust-forge <username> <value>
    zen set-secrets [<username>]
    zen append-custom-peer <peer-list>
    zen check-secrets

Options:
    -b --block-delay=<block-delay>    : block amount to wait beetween payroll
    -e --excludes=<excludes>          : coma-separated or file address list to exclude from payroll
    -w --wallet=<wallet>              : delegate funds wallet
    -f --fee-level=<fee-level>        : set the fee level for the delegate
    -h --webhook-peer=<webhook-peer>  : define the webhook peer to use
    -s --share=<share>                : delegate share rate (0.0<=share<=1.0)
    -t --threshold=<threshold>        : minimum amount for a payment
    -n --name-list=<name-list>        : *.tbw coma-separated name list
    -m --minimum-vote=<minimum-vote>  : set a minimum vote level
    -M --maximum-vote=<maximum-vote>  : set a maximum vote level
    -p --port=<port>                  : port to use for zen server        [default: 5000]
    --ip-address=<ip-address>         : ip address to use for zen server  [default: 127.0.0.1]
    --chunk-size=<chunk-size>         : max transaction per multitransfer [default: 30]
    --fee-coverage                    : delegate covers transaction fees (flag)

Subcommands:
    reset              : initialization starting from ark-core config folder
    initialize         : initialization starting from peer selection
    configure          : configure global or delegate-specific options
    deploy-srv         : deploy services and start the true block weight server tasks
    restart-srv        : restart the true block weight server tasks
    stop-srv           : stop the true block weight server tasks
    log-zen/bg         : log true block weight server or background tasks
    backup-data        : store delegate public data in a data-bkp.tar.bz2
    launch-payroll     : create a payroll for <username> (true block weight status reseted)
    retry-payroll      : retry a specified payroll for <username> (true block weight status unchanged)
    resume-payroll     : resume existing <username> payroll (true block weight status unchanged)
    add-delegate       : add delegate if bip39 secret protection used
    remove-delegate    : remove delegate <username>
    secrets            : reset delegate secrets
    check-secrets      : check registered private keys
    append-custom-peer : append custom peer from coma-separated-peer list or newline-separated-peer file
    remove-custom-peer : remove one or more custom peer from a selection list
```

## Notification system

4 notification types are available. Notification service is activated if a json configuration file is present in `.json` folder.

**freemobile (french only)**

Notification option must be enabled in your Free mobile account. Then, copy your parameters in `freemobile.json` file&nbsp;:
```json
{
    "user": "12345678", 
    "pass": "..."
}
```

**twilio**

Copy your parameters in `twilio.json` file&nbsp;:
```json
{
    "sid": "...",
    "auth": "...", 
    "receiver": "+1234567890", 
    "sender": "+0987654321"
}
```

**Pushover**

Copy your parameters in `pushover.json` file&nbsp;:
```json
{
    "user": "...",
    "token": "..."
}
```

**Pushbullet**

Copy your API token in `pushbullet.json` file&nbsp;:
```json
{
    "token": "..."
}
```

## `zen` front-end

![zen front-end](https://raw.githubusercontent.com/Moustikitos/zen/master/app.png)

## Releases

### Normae - 4.0.0 [current work]
  * [X] Packaging improvement
  * [X] security improvmenet
  * [X] `SIGINT` and `SIGTERM` handlers for bg tasks

### Monoceros
#### 3.1.0
  * [X] Ark core 3.0 compliancy
#### 3.0.0
  * [X] virtualenv target choice on zen installation
  * [X] `zen` and `bg` run as system services

### Lupus 
#### 2.0.1
  * [X] nonce bugfix
  * [X] `retry-payroll` updated
  * [X] `bg` module updated
#### 2.0.0
  * [x] ark-core 2.6 compliancy
  * [x] dposlib 0.3 compliancy
  * [x] use multipayment transaction

### Hydrus - 1.9.0
  * [x] dposlib 0.2.2 compliancy
  * [x] background tasks added
  * [x] block computation daemonization
  * [x] logging improvement
  * [x] better error handling

### Gemini
#### 1.8.1
  * [x] ark v2.5.1 compliancy
#### 1.8.0
  * [x] dposlib 0.2.1 compliancy
  * [x] ark v2.4.1 compliancy

### Fornax
#### 1.7.3
  * [x] persona network compliancy
#### 1.7.2
  * [x] front-end improvement
  * [x] added FAQ page
  * [x] background tasks merged
#### 1.7.1
  * [x] setup script improvement
  * [x] initialization improvement
  * [x] added relay checker
#### 1.7.0
  * [x] ark-zen now runs in virtualenv
  * [x] server auto-configuration using gunicorn and nginx 
  * [x] minor bugfixes and improvements

### Eridanus - 1.6.0
  * [x] notification system added (SMS or push)
  * [x] ark-zen runs with ark-core 2.2.x
  * [x] added node checker

### Delphinus - 1.5.0
  * [x] ark-zen runs with ark-core 2.1.x
  * [x] html front-end improvement

### Cassiopeia
#### 1.4.2
  * [x] ark-zen runs with both ark-core mainnet and devnet
#### 1.4.1
  * [x] fee coverage is now optional
  * [x] delegate targetting is now optional
#### 1.4.0
  * [x] automatic fee coverage
  * [x] transaction history rebuild
  * [x] delegate targetting

### Boötis
#### 1.3.1
  * [x] reward distribution improvement
#### 1.3.0
  * [x] enable remote delegate management
  * [x] blockchain database rebuild
  * [x] snapshot management
  * [x] custom peer management

### Andromeda - 1.2.0
  * [x] true block weight
  * [x] secured payrolls
  * [x] command line interface
  * [x] light weight HTML front-end
  * [x] multiple pool management
