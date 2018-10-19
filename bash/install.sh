# install system dependencies
echo installing system dependencies
sudo apt-get install python
sudo apt-get install python-setuptools
sudo apt-get install python-pip

clear

# download zen package
echo downloading zen package
cd ~
git clone https://github.com/Moustikitos/zen.git

# install python dependencies
echo installing python dependencies
cd ~/zen
pip install -r requirement.txt

clear

# initialize zen
echo initializing zen
python cfg.py initialize

# launch zen-tbw or reload it
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
    pm2 start app.json
else
    pm2 reload zen-tbw
fi

# reload ark-core-relay if launched
if [ "$(pm2 id ark-core-relay) " != "[]" ]; then
    pm2 reload ark-core-relay
fi
