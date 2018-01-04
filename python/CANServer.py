# pylint: disable=C0103,C0111,C0301
#!/usr/bin/env python3
import configparser
import csv
import json
import asyncio
import logging
import threading
import queue
import datetime
from collections import OrderedDict
import time
import can
import canopen
import CANObject

class CANServer(object):
    def __init__(self):
          # Get config
        self.config = configparser.ConfigParser()
        self.config.read('/home/pi/CAN/CANServer/python/CANSERVER.INI')

        self.logger = logging.getLogger(__name__)
        self.logger.info('CANServer Logger Added')

        self.CAN_Objects = []
        self.CAN_Data = OrderedDict()
        self.CAN_DataToLog = OrderedDict()

        self.network = canopen.Network()
        self.nodeNo = 0

        self.firstStart = True

        self.filename = ""
        self.logData = bool(self.config['CANSERVER']['logData'])
        self.csvwriter = None
        self.initialized = False

        edsfile = self.config['CANSERVER']['edsFilePath']
        self.node = self.network.add_node(int(self.config['CANSERVER']['canNode']), edsfile)

        self.q = queue.Queue(maxsize=0)

        # Starting CAN worker thread
        cw = threading.Thread(target=self.can_worker)
        cw.daemon = True
        cw.start()

        try:
            # try:
            #     bus = can.bus.BusABC(channel=self.config['CANSERVER']['canChannel'], bustype='socketcan', bitrate=125000)
            #     bus.send(can.Message())
            # except Exception:
            #     self.logger.exception("unable to send msg")

            self.network.connect(channel=self.config['CANSERVER']['canChannel'], bustype='socketcan', bitrate=125000)        

            # while True:
            #     time.sleep(1)
            #     try:
            #         self.network.scanner.search()
            #     except can.CanError:
            #         self.logger.exception("Could not send can message")
            #     # We may need to wait a short while here to allow all nodes to respond
            #     time.sleep(0.1)
            #     if self.node in self.network.scanner.nodes:
            #         break
            #     else:
            #         self.logger.warning("configured node not found, retrying in 1sec")
        except Exception:
            self.logger.exception("Could not connect to CAN network")

    # Gets called after a time defined by the update rate of the SDO object
    def sdo_update(self, co: CANObject.CANObject):
        # push co on CAN worker queue
        #self.logger.info("Added co to SDO watch %s", co)
        self.q.put(co)

        # Restart SDO timer
        self.logger.info("restarting timer with update rate:%s", float(co.updateRate))
        if co in self.CAN_Objects:
            threading.Timer(float(co.updateRate), self.sdo_update, args=(co, )).start()

    # Gets all CAN Objects from the queue and gets there actual data
    def can_worker(self):
        while True:
            co = self.q.get()
            self.logger.info("can worker: set update for:%s", co.key)
            # Only add value if key is present, otherwise do nothing (assigning to nonexisting key ads key)
            if co.key in self.CAN_Data:
                data = co.getData(self.node)
                self.CAN_Data[co.key] = data
                if co.key in self.CAN_DataToLog:
                    self.CAN_DataToLog[co.key] = data
            self.q.task_done()

    # Decode JSON config file and make CAN objects
    async def consumer(self, message):
        try:
            canObjectList = json.loads(message)
            self.logger.info('Config received: %s', canObjectList)

            # Empty existing list
            self.CAN_Objects[:] = []
            self.CAN_Data.clear()
            self.CAN_DataToLog.clear()

            for co in canObjectList:
                # Init CAN objects
                self.CAN_Objects.append(CANObject.CANObject(co["key"], co["log"], co["updateRate"],
                                                            co["toMin"], co["toMax"],
                                                            co["fromMin"], co["fromMax"]))
                # Init CAN Data dict with all keys and data = 0
                self.CAN_Data[co["key"]] = "0"

                if co["log"]:
                    self.CAN_DataToLog[co["key"]] = "0"

            if self.logData:
                self.filename = '/home/pi/CAN/CANServer/python/eKartlog_' + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + '.csv'
                with open(self.filename, "w") as logfile:  # = write (new?)
                    self.csvwriter = csv.writer(logfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    self.logger.info(list(self.CAN_Data.keys()))

                    header = ['Time'] + list(self.CAN_DataToLog.keys())

                    self.csvwriter.writerow(header)
                    self.initialized = True
            # Init objects
            self.initCanObjects()

        except ValueError:
            self.logger.exception("The received string is not JSON!")

    def initCanObjects(self):
        # setup CAN objects
        for co in self.CAN_Objects:
            self.sdo_update(co)

    # Sends data on the sendRate
    async def producer(self):
        await asyncio.sleep(float(self.config['CANSERVER']['sendRate']))

        if self.logData and self.initialized:
            with open(self.filename, "a") as logfile:  # a = append
                self.csvwriter = csv.writer(logfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                data = [datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]] + list(self.CAN_DataToLog.values())
                self.csvwriter.writerow(data)
        return json.dumps(self.CAN_Data)

    async def consumer_handler(self, websocket):
        while True:
            message = await websocket.recv()
            await self.consumer(message)

    async def producer_handler(self, websocket):
        while True:
            message = await self.producer()
            await websocket.send(message)

    async def handler(self, websocket, path):
        consumer_task = asyncio.ensure_future(self.consumer_handler(websocket))
        producer_task = asyncio.ensure_future(self.producer_handler(websocket))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
