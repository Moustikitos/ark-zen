# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities for DPOS pool.

## Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://dpos.arky-delegate.info/arky)

## Supported blockchain

 * [X] Ark

## Install

### last release

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-zen/master/bash/zen-install.sh) 2.0.1
```

### developpement version

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-zen/master/bash/zen-install.sh)
```

## Configure

```bash
cd ~
$HOME/ark-zen/bash/activate
./zen initialize
```
This command restarts `relay`.

## `zen` command

```bash
cd ~
$HOME/ark-zen/bash/activate
./zen --help
```
```
Usage:
    zen (reset | initialize | snap-blockchain | rebuild | remove-custom-peer)
    zen (start-srv | stop-srv | log-zen | log-bg)
    zen configure <username> [-s <share> -w <wallet> -t <threshold> -e <excludes> -b <block-delay> -f <fee-level>]
    zen add-delegate <username> [-h <webhook-peer>]
    zen configure [--max-per-sender <max-per-sender> --fee-coverage --chunk-size <chubk-size>]
    zen (launch-payroll | resume-payroll | retry-payroll | check-applied) <username>
    zen adjust-forge <username> <value>
    zen remove-delegate [<username>]
    zen append-custom-peer <peer-list>

Options:
    -b --block-delay=<block-delay>    : block amount to wait beetween payroll
    -e --excludes=<excludes>          : coma-separated or file address list to exclude from payroll
    -w --wallet=<wallet>              : delegate funds wallet
    -f --fee-level=<fee-level>        : set the fee level for the delegate
    -h --webhook-peer=<webhook-peer>  : define the webhook peer to use
    -s --share=<share>                : delegate share rate (0.0<=share<=1.0)
    -t --threshold=<threshold>        : minimum amount for a payment
    -n --name-list=<name-list>        : *.tbw coma-separated name list
    --max-per-sender=<max-per-sender> : max transaction not considered as spam attack [default:300]
    --chunk-size=<chunk-size>         : max transaction per request [default:30]
    --fee-coverage                    : delegate covers transaction fees (flag)

Subcommands:
    reset              : initialization starting from ark-core config folder
    initialize         : initialization starting from delegates configuration
    rebuild            : rebuild database from snapshots
    configure          : configure options for a given <username>
    start-srv          : start the true block weight server tasks
    stop-srv           : stop the true block weight server tasks
    log-zen/bg         : log true block weight server or background tasks
    launch-payroll     : create a payroll for <username> (true block weight status reseted)
    retry-payroll      : retry a specified payroll for <username> (true block weight status unchanged)
    resume-payroll     : resume existing <username> payroll (true block weight status unchanged)
    add-delegate       : add <username> without relay initialization (use if bip39 secret protection)
    remove-delegate    : remove delegate from list or specified by <username>
    snap-blockchain    : update snapshot or create it if no snapshot initialized yet
    append-custom-peer : append custom peer from coma-separated-peer or newline-separated-peer file
    remove-custom-peer : remove one or more custom peer from a selection list
```

## Specific tweak

You should tweak the ``env.CORE_TRANSACTION_POOL_MAX_PER_SENDER`` value to fit the number of voter. If not, part of payroll will be considered as spam.

For example, if your delegate is upvoted by 100 wallets, set the value to 110 (100+10%) :
```bash
$HOME/ark-zen/bash/activate
./zen configure --max-per-sender 110
```

Notice that `relay` have to be restarted then.

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

### Andromeda (v1.2.0)
 - [x] true block weight
 - [x] secured payrolls
 - [x] command line interface
 - [x] light weight HTML front-end
 - [x] multiple pool management

### Boötis (v1.3.0)
 - [x] enable remote delegate management
 - [x] blockchain database rebuild
 - [x] snapshot management
 - [x] custom peer management

### Boötis - minor tweaks (v1.3.1)
 - [x] reward distribution improvement

### Cassiopeia (v1.4.0)
 - [x] automatic fee coverage
 - [x] transaction history rebuild
 - [x] delegate targetting

### Cassiopeia - minor tweaks (v1.4.1)
 - [x] fee coverage is now optional
 - [x] delegate targetting is now optional

### Cassiopeia - minor tweaks (v1.4.2)
 - [x] ark-zen runs with both ark-core mainnet and devnet

### Delphinus (v1.5.0)
 - [x] ark-zen runs with ark-core 2.1.x
 - [x] html front-end improvement

### Eridanus (v1.6.0)
 - [x] notification system added (SMS or push)
 - [x] ark-zen runs with ark-core 2.2.x
 - [x] added node checker

### Fornax (v1.7.0)
 - [x] ark-zen now runs in virtualenv
 - [x] server auto-configuration using gunicorn and nginx 
 - [x] minor bugfixes and improvements

### Fornax (v1.7.1)
 - [x] setup script improvement
 - [x] initialization improvement
 - [x] added relay checker

### Fornax (v1.7.2)
 - [x] front-end improvement
 - [x] added FAQ page
 - [x] background tasks merged

### Fornax (v1.7.3)
 - [x] persona network compliancy

### Gemini (v1.8.0)
 - [x] dposlib 0.2.1 compliancy
 - [x] ark v2.4.1 compliancy

### Gemini (v1.8.1)
 - [x] ark v2.5.1 compliancy

### Hydrus (v1.9.0)
 - [x] dposlib 0.2.2 compliancy
 - [x] background tasks added
 - [x] block computation daemonization
 - [x] logging improvement
 - [x] better error handling

### Lupus (v2.0.0)
 - [x] ark-core 2.6 compliancy
 - [x] dposlib 0.3 compliancy
 - [x] use multipayment transaction

### Lupus (v2.0.1)
 - [X] nonce bugfix
 - [X] `retry-payroll` updated
 - [X] `bg` module updated
