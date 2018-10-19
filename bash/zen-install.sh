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
if ! (git clone https://github.com/Moustikitos/zen.git) then
    cd ~/zen
    git fetch --all
    git reset --hard origin/master
else
    cd ~/zen
fi

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install -r requirements.txt -q

# initialize zen
echo
echo initializing zen
echo ================
python cfg.py initialize

# launch zen-tbw or reload it
# reload ark-core-relay if launched
echo
echo launching/reloading pm2 tasks
echo =============================
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
    pm2 start app.json
else
    pm2 reload zen-tbw
fi

if [ "$(pm2 id ark-core-relay) " != "[]" ]; then
    pm2 reload ark-core-relay
fi
