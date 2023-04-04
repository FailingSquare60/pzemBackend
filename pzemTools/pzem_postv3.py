import serial
import struct
import argparse
from collections import namedtuple
from time import sleep, time, localtime, strftime, perf_counter
import subprocess
import mysql.connector
import sqlite3
import time
import os
# my pzem api
from .pzem_readv3 import AC_PZEM_1
# TheHWCave api
from .TheHWCave.AC_COMBOX import AC_COMBOX as AC_PZEM_3

# READ PZEM-004T v3
# Using TheHWCave's PZEM v3 serial API
# takes port, table name and writes into pzem.db
# pollMeter -takes port, interval (s)
# postMeasurements - takes table

DEF_PORT = '/dev/ttyUSB0'
DEF_ADDR = 1
DEF_HWVERSION = 'v3'
DEF_DB = '../../pzem.db'
DEF_TABLE = 'pzem_box'


def pollMeter(port=DEF_PORT, hwversion=DEF_HWVERSION):
    if hwversion == 'v3':
        ACM = AC_PZEM_3(port)
    else:  # v1
        ACM = AC_PZEM_1(port)
    pd = ACM.Poll()
    return pd


def getAddress(port=DEF_PORT, hwversion=DEF_HWVERSION):
    addr = None  # triggers read current address
    if hwversion == 'v3':
        ACM = AC_PZEM_3(port)
        addr = ACM.SlaveAddress(None)
    return addr


def setAddress(port=DEF_PORT, addr=None, hwversion=DEF_HWVERSION):
    success = False
    if hwversion == 'v3':
        ACM = AC_PZEM_3(port)
        res = ACM.SlaveAddress(addr)
        if res == addr:
            success = True
    return success


def postMeasurements(pd, table, mysql_host, mysql_database, mysql_user, mysql_pw):
    now = perf_counter()
    s = '{:5.1f},{:4.1f},{:7.3f},{:5.1f},{:5.0f},{:3.1f},{:5.2f},{:1n}'.format(
        now, pd.Volt, pd.Current, pd.Power,	pd.Energy,	pd.Freq, pd.Pf,	pd.Alarm)
    print(s)
    oldEnergy = 0
    dEnergy = int(pd.Energy) - int(oldEnergy)
    kwh = float(dEnergy)/1000
    oldEnergy = pd.Energy
    sql = "INSERT INTO " + table + " Values('{}', {:.2f}, {:d}, {:.2f}, {:.2f}, {:d}, {:.2f})".format(
        time.strftime('%Y-%m-%d %H:%M:%S'), pd.Current, int(pd.Energy), pd.Power, pd.Volt, dEnergy, kwh)
    print(sql)
    count = 0
    if False:
        print('connecting to sqlite db: ' + mysql_database)
        print('database exists?' + str(os.path.exists(mysql_database)))
        try:
            cnx = sqlite3.connect(mysql_database, isolation_level=None)
            print("connecting to db...")
            cur = cnx.cursor()
            cur.execute(sql)
            print("cur...")
            #print('tables found: ')
            # for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';"):
            #    print(row)
            with cnx:
                # WAL mode to prevent locking database
                cnx.execute('PRAGMA journal_mode=wal')
                cnx.execute(sql)
                # cur.execute(sql)
            cur.close()
            cnx.close()
            # cur.commit()
            # cnx.execute(sql)

        except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            print('Could not complete database operation:', e)
            # cnx.close()
            time.sleep(10)
    # mysql
    print("connecting to mysql")
    try:
        cnx = mysql.connector.connect(
            user=mysql_user, password=mysql_pw, host=mysql_host, database=mysql_database)
        cur = cnx.cursor()
        cur.execute(sql)
        cnx.commit()
        cur.close()
    except (mysql.connector.Error) as e:
        print('Could not complete database operation:', e)
        # cnx.close()
        time.sleep(10)


def run(table, mysql_host, mysql_database, mysql_user, mysql_pw, port=DEF_PORT, addr=DEF_ADDR, hwversion=DEF_HWVERSION, interval=30):
    start = perf_counter()
    now = perf_counter()-start
    if hwversion == 'v1':
        currAddr = addr  # TODO make V1 address read/set
    elif hwversion == 'v3':
        currAddr = getAddress(port, hwversion)  # only for v3

    if addr == currAddr:
        print('address matches! ', currAddr)
        Continue = True  # need a hwversion catch for V1
    else:
        print('address does not match!', currAddr)
        Continue = False

    while Continue:
        try:
            now = perf_counter()-start

            print('polling meter at port ', port)
            pd = pollMeter(port, hwversion)
            if pd is not None:
                print('posting measurements to table ', mysql_database)
                postMeasurements(pd, table, mysql_host, mysql_database, mysql_user, mysql_pw)
            else:
                print("pd is None, not posting to database")

            elapsed = (perf_counter()-start) - now
            if elapsed < interval:
                sleep(interval - elapsed) #seconds
        except KeyboardInterrupt:
            print("Pzem Run interrupted")
            time.sleep(5)


if __name__ == "__main__":
    run()
