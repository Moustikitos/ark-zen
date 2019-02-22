# install system dependencies
clear
echo installing system dependencies
echo ==============================
sudo apt-get -qq install curl
sudo apt-get -qq install python
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip

# download zen package
echo
echo downloading zen package
echo =======================
cd ~
if ! (git clone --branch master https://github.com/Moustikitos/ark-zen.git) then
    cd ~/ark-zen
else
    cd ~/ark-zen
    git reset --hard
fi
git fetch --all
git checkout master -f

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
    # launch zen-srv or reload it
    # reload ark-forger if launched
    echo
    echo launching/restarting pm2 tasks
    echo ==============================
    if [ "$(pm2 id zen-srv) " = "[] " ]; then
        cd ~/ark-zen
        pm2 start srv.json
    else
        pm2 restart zen-srv
    fi

    if [ "$(pm2 id ark-forger) " != "[] " ]; then
        pm2 restart ark-forger
    fi
fi
