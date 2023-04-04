from time import sleep
import serial
import threading
# RASP
import time
import datetime
import binascii
import argparse
from collections import namedtuple

# pzem_read.py api for reading PZEM-004T v1
# pzem_poll: given const addresses, send command, get resp in recvArr, check resp is valid and build dataobj

parser = argparse.ArgumentParser()
DEF_PORT = '/dev/ttyUSB0'

parser.add_argument('--port', '-p', help='port (default = /dev/ttyUSB0',
                    dest='port_dev', action='store', type=str, default=DEF_PORT)

parser.add_argument('--time', '-t', help='interval time in seconds between measurements (def=1.0)',
                    dest='int_time', action='store', type=float, default=1.0)


class AC_PZEM_1:
    # all caps for const put at top of pzem_read.py as global
    __ARR_ADDRESS = [0xC0, 0xA8, 0x01, 0x01, 0x00]
    __CMD_ADDRESS = [0xB4] + __ARR_ADDRESS
    __CMD_ENERGY = [0xB3] + __ARR_ADDRESS
    __CMD_VOLTAGE = [0xB0] + __ARR_ADDRESS
    __CMD_CURRENT = [0xB1] + __ARR_ADDRESS
    __CMD_POWER = [0xB2] + __ARR_ADDRESS

    #
    # 	The class keeps copies of the actual values in the AC module here
    #
    __volt = 0.0  # in V
    __current = 0.0  # in A
    __power = 0.0  # in W
    __energy = 0.0  # in Wh
    __freq = 0.0  # in Hz
    __pf = 0.0
    __alarm = 0
    __thresh = 0.0  # in W
    __addr = 0

    PollData = namedtuple('PollData', ['Volt', 'Current', 'Power',
                                       'Energy', 'Freq', 'Pf', 'Alarm'])

    def sendCmd(self, ser, cmdArr1):
        #print("sending cmd: ", cmdArr1)
        rcvArr = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        sum = 0
        for elem in cmdArr1:
            sum += elem
            # print(type(elem))
        sumByte = (sum << 0) & 0xFF
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
        return rcvArr

    def respValid(self, rcvArr):
        sum = 0
        i = 0
        try:
            while i < 6:
                # print(type(rcvArr[i][0]))
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
            tf = False
        return tf

    def bytes2int(str):
        return int(str.encode('hex'), 16)

    def readVoltage(self, rcvArr):
        # D1D2 represents integer bits
        voltage = float(rcvArr[2][0]) + float(rcvArr[3][0])/10
        #print("voltage: " + str(voltage))
        return voltage

    def readCurrent(self, rcvArr):
        # D2 represents integer, D3 rep decimal
        current = float(rcvArr[2][0]) + float(rcvArr[3][0])/10
        #print("Current: " + str(current))
        return current

    def readEnergy(self, rcvArr):
        # for elem in rcv:
        #	print(hex(elem))
        # D1D2D3 represents integer
        energy = float(rcvArr[1][0] << 16) + \
            float(rcvArr[2][0] << 8) + float(rcvArr[3][0])
        #print("energy: " + str(energy))
        return energy

    def readPower(self, rcvArr):
        # D1D2 represents integer
        power = float(rcvArr[1][0] << 8) + float(rcvArr[2][0])
        #print("power: " + str(power))
        return power

    def __read_responses(self):
        rcvArr = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # NOT CONSTANT
        res = False
        ser = self.__ACM
        rcvArr = self.sendCmd(ser, self.__CMD_ADDRESS)
        valid = self.respValid(rcvArr)
        if valid:
            rcvArr = self.sendCmd(ser, self.__CMD_VOLTAGE)
            if self.respValid(rcvArr) and valid:
                self.__volt = self.readVoltage(rcvArr)
            rcvArr = self.sendCmd(ser, self.__CMD_CURRENT)
            if self.respValid(rcvArr) and valid:
                __current = self.readCurrent(rcvArr)
            rcvArr = self.sendCmd(ser, self.__CMD_ENERGY)
            if self.respValid(rcvArr) and valid:
                __energy = self.readEnergy(rcvArr)
            rcvArr = self.sendCmd(ser, self.__CMD_POWER)
            if self.respValid(rcvArr) and valid:
                __power = self.readPower(rcvArr)

        return valid

    def Poll(self):
        """
                read data from the module and return it as a tuple
                if data valid
        """
        pd = None
        if self.__read_responses():
            pd = self.PollData(
                Volt=self.__volt,
                Current=self.__current,
                Power=self.__power,
                Energy=self.__energy,
                Freq=self.__freq,
                Pf=self.__pf,
                Alarm=self.__alarm)
        return pd

    def __init__(self, port=DEF_PORT):
        self.__ACM = serial.Serial(port=port, baudrate=9600, timeout=1)


if __name__ == '__main__':
    ACM = AC_PZEM_1(arg.port_dev)

    start = perf_counter()
    now = perf_counter()-start
    try:
        while True:
            now = perf_counter()-start
            pd = ACM.Poll()
            s = '{:5.1f},{:4.1f},{:7.3f},{:5.1f},{:5.0f},{:3.1f},{:5.2f},{:1n}'.format(
                now,
                pd.Volt,
                pd.Current,
                pd.Power,
                pd.Energy,
                pd.Freq,
                pd.Pf,
                pd.Alarm)
            print(s)
            elapsed = (perf_counter()-start) - now
            if elapsed < arg.int_time:
                sleep(arg.int_time - elapsed)
    except KeyboardInterrupt:
        print("ACM interrupted")
