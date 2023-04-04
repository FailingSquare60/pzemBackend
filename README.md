# PzemBackend 
Integrated [TheHWCave's Pzem004T v3.0 library](https://github.com/TheHWcave/Peacefair-PZEM-004T-) with my v1.0 library to poll meters every 10 seconds via and posts to a remote mySQL database. Utilizes systemctl to manage python processes for each meter connected (Ex: to Raspberry Pi).

## Requirements
# PZEM004T AC electrical meter
Works with both [Pzem004T v1.0](https://innovatorsguru.com/ac-digital-multifunction-meter-using-pzem-004t/) and [Pzem004T v3.0](https://innovatorsguru.com/pzem-004t-v3/) modules
#Raspberry Pi
- Tested on Raspberry PI 3 and 3+
- I do NOT reccomend Pi Zeros v1 or v2 as the USB issues do not resolve without manual power cycling

## Configuration
1. Connect the PZEM meter per specs and connect the serial interface to a Serial-to-USB adapter into a Raspbery Pi. 

2. Create a meter config file (Ex: meter1.py) See below.

3. Create a systemctl file to manage this process for you. See below

##If you have multiple meters 
You can use the serial addressing method of the Pzem library to be sure the USB addresses in the config are pointing to the right meter.

## Meter Config File Example
```
#meter1.py
from pzemTools.pzem_postv3 import run
import os

table = 'mysql_table'
meter_port = '/dev/ttyUSB0'
meter_addr = 1
meter_ver = 'v3'
mysql_host = 'my.host'
mysql_db = 'mysqldb'
mysql_user = 'myUser'
mysql_pw = 'myPassword'

run( table, mysql_host, mysql_db, mysql_user, mysql_pw, meter_port, meter_addr, meter_ver)

if __name__ == '__main__':
    meter1.py()
```

##Systemctl File Example
```
sudo nano /lib/systemd/system/pzemunitA.service
```
```
[Unit] 
Description=record pzem meter data to database(s)

[Service] 
ExecStart=/usr/bin/python3 /home/pi/pzemBackend/meter1.py 
Restart=always 
RestartSec=10 User=pi

[Install] 
WantedBy=multi-user.target
```
