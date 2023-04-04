from time import sleep
import serial
import threading
#RASP
import time
import mysql.connector
import datetime
import binascii

#rename to pzem_read()
ARR_ADDRESS = [0xC0,0xA8,0x01,0x01,0x00] #all caps for const put at top of pzem_read.py as global
CMD_ADDRESS = [0xB4] + ARR_ADDRESS
CMD_ENERGY = [0xB3] + ARR_ADDRESS
CMD_VOLTAGE = [0xB0] + ARR_ADDRESS
CMD_CURRENT = [0xB1] + ARR_ADDRESS
CMD_POWER = [0xB2] + ARR_ADDRESS

def sendCmd(ser, cmdArr1):
    #print("sending cmd: ", cmdArr1)
    rcvArr = [0x00,0x00,0x00,0x00,0x00,0x00,0x00]
    sum = 0
    for elem in cmdArr1:
            sum += elem
            #print(type(elem))
    sumByte = (sum << 0) & 0xFF
    #print("sum: " + hex(sumByte))
    #cmdArr1.append(sumByte)
    #cmdArr1 += [sumByte]
    ser.write(serial.to_bytes(cmdArr1 + [sumByte])) 
    byte = 0x00
    i = 0
    while i < 7:
        #print("resp: i= ", i)
        byte = ser.read()
        #print("resp: byte= ", byte)
        if byte != '\n':	
                rcvArr[i] = byte
        i += 1
    return rcvArr;

def respValid(rcvArr):
    sum = 0
    i = 0
    try:
        while i < 6:
            #print(type(rcvArr[i][0]))
            sum += int(rcvArr[i][0])
            i += 1
        sumByte = (sum << 0) & 0xFF
        if sumByte == rcvArr[6][0]:
            #print("success! " + str(sumByte))
            tf = True
        else:
            #print("fail sumByte: " + str(sumByte) + " recArr[6]: " + str(rcvArr[6])[0])
            tf = False
    except:
        print("respValid failed!")
        tf=False
    return tf;

def bytes2int(str):
    return int(str.encode('hex'), 16)

def readVoltage(rcvArr):
    #D1D2 represents integer bits
    voltage = float(rcvArr[2][0]) + float(rcvArr[3][0])/10
    #print("voltage: " + str(voltage))
    return voltage;

def readCurrent(rcvArr):
    #D2 represents integer, D3 rep decimal
    current = float(rcvArr[2][0]) + float(rcvArr[3][0])/10
    #print("Current: " + str(current))
    return current;

def readEnergy(rcvArr):
    #for elem in rcv:
    #	print(hex(elem))
    #D1D2D3 represents integer
    energy = float(rcvArr[1][0]<<16) + float(rcvArr[2][0]<<8) + float(rcvArr[3][0])
    #print("energy: " + str(energy))
    return energy;

def readPower(rcvArr):
    #D1D2 represents integer
    power = float(rcvArr[1][0]<<8) + float(rcvArr[2][0])
    #print("power: " + str(power))
    return power;

def pzem_read(serialportname = "/dev/ttyUSB0"):
    ser = serial.Serial(serialportname, baudrate=9600, timeout=1)
    print(serialportname)
    
    rcvArr = [0x00,0x00,0x00,0x00,0x00,0x00,0x00]  #NOT CONSTANT

    ser.flushInput()

    rcvArr = sendCmd(ser, CMD_ADDRESS)
    #for elem in rcv:
    #	print elem
    respValid(rcvArr)
    while True:
        rcvArr = sendCmd(ser, CMD_VOLTAGE)
        voltage = readVoltage(rcvArr)
        print("voltage: " + str(voltage))
        rcvArr = sendCmd(ser, CMD_CURRENT)
        current = readCurrent(rcvArr)
        print("Current: " + str(current))
        rcvArr = sendCmd(ser, CMD_ENERGY)
        energy = readEnergy(rcvArr)
        print("energy: " + str(energy))
        rcvArr = sendCmd(ser, CMD_POWER)
        power = readPower(rcvArr)
        print("power: " + str(power))
        print(" ")

if __name__ == '__main__':
    pzem_read()




	
	
