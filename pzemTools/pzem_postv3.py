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
DEF_RETRY_INTERVAL = 5  # seconds
DEF_MAX_RETRIES = 5

def get_usb_device_id(port):
    """
    Find the USB device ID (e.g., '1-1.3') associated with a given port (e.g., '/dev/ttyUSB0').

    Args:
        port (str): The device port (e.g., '/dev/ttyUSB0').

    Returns:
        str: The USB device ID (e.g., '1-1.3') or None if not found.
    """
    try:
        result = subprocess.run(
            ["udevadm", "info", "--name", port, "--query", "path"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"[ERROR] udevadm error: {result.stderr.strip()}")
            return None

        device_path = result.stdout.strip()
        # Extract the USB device ID from the path
        parts = device_path.split("/")
        for part in parts:
            if part.startswith("1-") and len(part.split(".")) > 1:  # Look for IDs like '1-1.3'
                return part

        print("[ERROR] USB device ID not found.")
        return None
    except Exception as e:
        print(f"[ERROR] Exception in get_usb_device_id: {e}")
        return None

def reset_usb_port(device_id):
    """
    Reset a USB port by unbinding and rebinding the device driver.

    Args:
        device_id (str): The USB device ID (e.g., "1-1.3").
    """
    device_path = f"/sys/bus/usb/devices/{device_id}/driver"
    
    # Check if the device path exists
    if not os.path.exists(device_path):
        print(f"[ERROR] Device {device_id} not found. Check the device ID.")
        return

    try:
        # Unbind the device
        with open(f"{device_path}/unbind", "w") as unbind_file:
            unbind_file.write(device_id)
        print(f"[INFO] Device {device_id} unbound successfully.")

        time.sleep(2)  # Wait for 2 seconds before rebinding

        # Rebind the device
        with open(f"{device_path}/bind", "w") as bind_file:
            bind_file.write(device_id)
        print(f"[INFO] Device {device_id} rebound successfully.")

    except PermissionError:
        print("[ERROR] Permission denied. Try running the script with sudo.")


def pollMeter(port=DEF_PORT, hwversion=DEF_HWVERSION):
    """
    Poll the meter for readings. Retry if USB connection fails.
    """
    retry_count = 0
    while retry_count < DEF_MAX_RETRIES:
        try:
            if not os.path.exists(port):
                raise serial.SerialException(f"Device not found at {port}")
            if hwversion == 'v3':
                acm = AC_PZEM_3(port)
            else:
                acm = AC_PZEM_1(port)
            pd = acm.Poll()
            return pd
        except serial.SerialException as e:
            retry_count += 1
            print(f"USB connection error: {e}. Retrying in {DEF_RETRY_INTERVAL} seconds... ({retry_count}/{DEF_MAX_RETRIES})")
            sleep(DEF_RETRY_INTERVAL)

            # Attempt to reset the device
            device_id = get_usb_device_id(port)
            if device_id:
                print(f"Resetting device id: {device_id}")
                reset_usb_port(device_id)
            else:
                print(f"Could not find USB device ID for port {port}.")
    print("Failed to reconnect to the USB device after multiple attempts.")
    return None



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
    print(pd)
    sql = "INSERT INTO " + table + " Values('{}', {:.2f}, {:d}, {:.2f}, {:.2f}, {:d}, {:.2f})".format(
        time.strftime('%Y-%m-%d %H:%M:%S'), pd.Power, int(pd.Energy), pd.Current, pd.Volt, dEnergy, kwh)
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


def run(table, mysql_host, mysql_database, mysql_user, mysql_pw, port=DEF_PORT, addr=DEF_ADDR, hwversion=DEF_HWVERSION, interval=15):
    start = perf_counter()
    now = perf_counter() - start

    # Get usb_device_id
    usb_device_id = get_usb_device_id(port)
    if usb_device_id:
        print(f"USB device ID for port {port}: {usb_device_id}")
    else:
        print(f"Could not find USB device ID for port {port}.")

    # Reset USB if needed
    try:
        if hwversion == 'v1':
            currAddr = addr  # TODO: Make V1 address read/set
        elif hwversion == 'v3':
            currAddr = getAddress(port, hwversion)  # Only for v3

        if addr == currAddr:
            print('Address matches! ', currAddr)
            Continue = True
        else:
            print('Address does not match!', currAddr)
            Continue = False

    except OSError as e:
        if e.errno == 5:  # Errno 5: Input/output error
            print(f"[ERROR] Input/output error on port {port}: {e}.")
            usb_device_id = get_usb_device_id(port)
            if usb_device_id:
                print(f"[INFO] Attempting to reset USB device {usb_device_id}.")
                reset_usb_port(port)
                time.sleep(5)  # Allow the device to reinitialize
            else:
                print(f"[ERROR] Could not find USB device ID for port {port}. Reset failed.")
            return  # Exit if USB reset fails
        else:
            print(f"[ERROR] Unexpected OSError: {e}")
            return

    while Continue:
        try:
            now = perf_counter() - start
            print('Polling meter at port ', port)
            pd = pollMeter(port, hwversion)
            if pd is not None:
                print('Posting measurements to table ', mysql_database)
                postMeasurements(pd, table, mysql_host, mysql_database, mysql_user, mysql_pw)
            else:
                print("[WARNING] Polling returned None. Skipping database posting.")

            elapsed = (perf_counter() - start) - now
            if elapsed < interval:
                sleep(interval - elapsed)  # Sleep for remaining interval
        except OSError as e:
            if e.errno == 5:  # Handle USB I/O error during polling
                print(f"[ERROR] Input/output error on port {port}: {e}. Attempting to reset.")
                if usb_device_id:
                    reset_usb_port(port)
                    time.sleep(5)  # Allow the device to reinitialize
                else:
                    print("[ERROR] USB device ID not found. Exiting.")
                    break
        except KeyboardInterrupt:
            print("[INFO] Pzem Run interrupted by user.")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(5)



if __name__ == "__main__":
    run()
