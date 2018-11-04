# install system dependencies
clear
echo installing system dependencies
echo ==============================
sudo apt-get -qq install python
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip

# download zen package
echo
echo downloading zen package
echo =======================
cd ~
if ! (git clone https://github.com/Moustikitos/ark-zen.git) then
    cd ~/ark-zen
    git fetch --all
    git reset --hard origin/master
else
    cd ~/ark-zen
fi

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install --user -r requirements.txt -q

# initialize zen
echo
echo initializing zen
echo ================
cp bash/zen ~
cd ~
chmod +x zen
if ! (./zen initialize) then
    echo
    echo setup aborted
else

    # launch zen-tbw or reload it
    # reload ark-core-relay if launched
    echo
    echo launching/restarting pm2 tasks
    echo ==============================
    if [ "$(pm2 id zen-tbw) " = "[] " ]; then
        cd ~/ark-zen
        pm2 start app.json
    else
        pm2 restart zen-tbw
    fi

    if [ "$(pm2 id ark-core-relay) " != "[] " ]; then
        pm2 restart ark-core-relay
    fi
fi
