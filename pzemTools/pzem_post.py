import os
import re
import subprocess
from time import sleep
import serial
import threading
#RASP
import time
import mysql.connector
import datetime
#my pzem library
from . import pzem_read

#def USBreset(driver = 'driver', device = '004')
#need to define dualCT/240V configuration per device.
#v0.2

def pzem_post(serialportname = '/dev/ttyUSB0', user='pi', tablename='pzem_box',host='10.0.0.33',database='schema1'):
    print("pzem_post v 0.2")
    print(serialportname,user,tablename)
    count = 0
    #print(ser.in_waiting)
    Continue = False
    print("connecting to mysql")
    cnx = mysql.connector.connect(user=user, password='Repair1', host=host, database=database)
    cursor = cnx.cursor()
    
    oldEnergy = 0
    #query = '''SELECT datetime, Energy FROM PzemCoop WHERE datetime in (Select max(datetime) from PZEM) '''
    #cursor.execute(query)
    #for (datetime, Energy) in cursor:
    #    print("Current: {} on {}".format(Energy, datetime))
    #    oldEnergy = int(Energy)
    #cnx.close()

    ser = serial.Serial(serialportname, 9600,timeout=1)
    #print("serial is open? ", ser.is_open)

    arrAddress = pzem_read.ARR_ADDRESS #[0xC0,0xA8,0x01,0x01,0x00]
    rcvArr = [0x00,0x00,0x00,0x00,0x00,0x00,0x00]
    cmdAddress = pzem_read.CMD_ADDRESS #[0xB4] + arrAddress
    cmdEnergy = pzem_read.CMD_ENERGY #[0xB3] + arrAddress
    cmdVoltage = pzem_read.CMD_VOLTAGE #[0xB0] + arrAddress
    cmdCurrent = pzem_read.CMD_CURRENT #[0xB1] + arrAddress #CMD_CURRENT const
    cmdPower = pzem_read.CMD_POWER #[0xB2] + arrAddress

    rcvArr = pzem_read.sendCmd(ser, cmdAddress)
    if pzem_read.respValid(rcvArr):
        print("success! resp valid")
    else:
        print("failed" + str(rcvArr[0]))

    rcvArr = pzem_read.sendCmd(ser, cmdVoltage)
    if pzem_read.respValid(rcvArr):
        voltage = pzem_read.readVoltage(rcvArr)
        print("voltage: " + str(voltage))
        Continue = True

    #rcvArr = pzem_read.sendCmd(ser, cmdCurrent)
    current = pzem_read.readCurrent(pzem_read.sendCmd(ser, cmdCurrent))
    print("Current: " + str(current))
    #rcvAr"r = pzem_read.sendCmd(ser, cmdEnergy)
    
    energy = pzem_read.readEnergy(pzem_read.sendCmd(ser, cmdEnergy))
    print("energy: " + str(energy))
    #rcvArr = pzem_read.sendCmd(ser, cmdPower)
    power = pzem_read.readPower(pzem_read.sendCmd(ser, cmdPower))
    print("power: " + str(power))
    print(" ")

    while True:
        Continue = False
        try: 
            ser.flushInput()
            print("sending voltage cmd...")
            rcvArr = pzem_read.sendCmd(ser, cmdAddress)
            if pzem_read.respValid(pzem_read.sendCmd(ser, cmdAddress)):
                print("resp valid!")
                #voltage = pzem_read.readVoltage(pzem_read.sendCmd(ser, cmdVoltage))
                Continue = True
            else:
                print("response invalid...")
                Continue = False
                sleep(1)

            #if ser.inWaiting() > 0:
            if Continue:
                print("Continuing...")
                #ser.flushInput()
                count = count + 1
                print("count: ",count)
                
                #Read voltage
                rcvArr = pzem_read.sendCmd(ser, cmdVoltage)
                Continue = Continue and pzem_read.respValid(rcvArr)
                if Continue:
                    voltage = pzem_read.readVoltage(pzem_read.sendCmd(ser, cmdVoltage))
                #Read Current
                rcvArr = pzem_read.sendCmd(ser, cmdCurrent)
                Continue = Continue and pzem_read.respValid(rcvArr)
                if Continue:
                    current = pzem_read.readCurrent(rcvArr)
                #Read Energy
                rcvArr = pzem_read.sendCmd(ser, cmdEnergy)
                Continue = Continue and pzem_read.respValid(rcvArr)
                if Continue:
                    energy = pzem_read.readEnergy(rcvArr)               
                #Read Power
                rcvArr = pzem_read.sendCmd(ser, cmdPower)
                Continue = Continue and pzem_read.respValid(rcvArr)
                if Continue:
                    power = pzem_read.readPower(rcvArr)
                
                if Continue:
                    voltageStr = str(voltage)
                    currentStr = str(current)
                    powerStr = str(power)
                    energyStr = str(energy)
                    dEnergy = int(energy) - int(oldEnergy)
                    kwh = float(dEnergy)/1000
                    oldEnergy = energy
                    #print("test:" + voltageStr + "," + currentStr + "," + powerStr + "," + energyStr)

                    try:               
                        #cnx = mysql.connector.connect(user=user, password='Repair1', host=host, database=database, connection_timeout=3600) #move to const connection
                        cursor = cnx.cursor()
                        #sql = "INSERT INTO PZEM Values(" + str(time.asctime()) + "," + currentStr + "," + energyStr + "," + powerStr + "," + voltageStr + ")"
                        sql = "INSERT INTO " + tablename + " Values('{}', {:.2f}, {:d}, {:.2f}, {:.2f}, {:d}, {:.2f})".format(time.strftime('%Y-%m-%d %H:%M:%S'),float(currentStr),int(energy),float(powerStr),voltage,dEnergy,kwh)
                        print(sql)
                        sleep(1)
                        number_of_rows = cursor.execute(sql)
                        cnx.commit()
                        cursor.close()                        
                        
                    except mysql.connector.Error as err:
                        print("Something went wrong: {}".format(err))
                        cnx.close()
                        time.sleep(10)
                        cnx = mysql.connector.connect(user=user, password='Repair1', host=host, database=database, connection_timeout=3600) #move to const connection
                        cursor = cnx.cursor()
                else:
                    print("failed to read serial...closing/opening")
                    sleep(1)
                    ser.close()
                    sleep(30)
                    ser.open()
                    sleep(1)
            else:
                print("failed to read serial...closing/opening")
                sleep(1)
                ser.close()
                sleep(1)
                ser.open()
                sleep(1)
        except:
            print("exception: failed to read serial...closing/opening")
            try:
                ser.close()
                sleep(10)
                ser.open()
            except:
                #sudo find /sys/bus/usb/devices/*/authorized -exec sh -c 'echo 0 > ${0}; echo 1 > ${0}' {} \;
                response = subprocess.Popen("sudo find /sys/bus/usb/devices/*/authorized -exec sh -c \'echo 0 > ${0}; echo 1 > ${0}\' {} \\;", shell=True, stdout=subprocess.PIPE).stdout.read()
                sleep(10)
            sleep(10)
            #ser.close()
            sleep(1)
            #ser.open()
            sleep(1)
        print("waiting...")
        sleep(5)
        #end While

if __name__ == '__main__':
    pzem_post()








