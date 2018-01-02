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

        self.updateRate = 1.0  # float()

        self.network = canopen.Network()
        self.nodeNo = 0

        self.firstStart = True

        self.filename = ""
        self.logData = bool(self.config['CANSERVER']['logData'])
        self.csvwriter = None
        self.initialized = False

        try:
            edsfile = self.config['CANSERVER']['edsFilePath']
            self.node = self.network.add_node(int(self.config['CANSERVER']['canNode']), edsfile)
        except Exception:
            self.logger.exception("could not find eds file:%s", edsfile)

        self.q = queue.Queue(maxsize=0)

        # Starting CAN worker thread
        cw = threading.Thread(target=self.can_worker)
        cw.daemon = True
        cw.start()

        try:
            self.network.connect(
                channel=self.config['CANSERVER']['canChannel'], bustype='socketcan', bitrate=125000)
        except Exception:
            self.logger.exception("Could not connect to CAN network")

    # Callback for when PDO data is available
    def pdo_Callback(self, message):
        # Add data to Data dict
        for co in self.CAN_Objects:
            if co.mode == "pdo":
                self.CAN_Data[co.key] = message[co.key].raw

        # ToDo send data each time PDO data received

    # Gets called after a time defined by the update rate of the SDO object
    def sdo_update(self, co: CANObject.CANObject):
        # push co on CAN worker queue
        #self.logger.info("Added co to SDO watch %s", co)
        self.q.put(co)

        # Restart SDO timer
        self.logger.info("restarting timer with update rate:%s",
                         float(co.updateRate))
        if co in self.CAN_Objects:
            threading.Timer(float(co.updateRate),
                            self.sdo_update, args=(co, )).start()

    # Gets all CAN Objects from the queue and gets there actual data
    def can_worker(self):
        while True:
            co = self.q.get()
            self.logger.info("can worker: set update for:%s", co.key)
            # Only add value if key is present, otherwise do nothing (assigning
            # to nonexisting key ads key)
            if co.key in self.CAN_Data:
                self.CAN_Data[co.key] = co.getData(self.node)
            self.q.task_done()

    # Decode JSON config file and make CAN objects
    async def consumer(self, message):
        try:
            canObjectList = json.loads(message)
            self.logger.info('Config received: %s', canObjectList)

            # Empty existing list
            self.CAN_Objects[:] = []
            self.CAN_Data.clear()

            for co in canObjectList:
                # Init CAN objects
                self.CAN_Objects.append(CANObject.CANObject(co["key"], co["mode"], co["updateRate"],
                                                            co["toMin"], co["toMax"],
                                                            co["fromMin"], co["fromMax"]))
                # Init CAN Data dict with all keys and data = 0
                self.CAN_Data[co["key"]] = "0"

                # set update rate to fastest rate of all co with a minimum of 0.5
                newRate = float(co["updateRate"])
                if newRate < self.updateRate and newRate >= float(self.config['CANSERVER']['minUpdateRate']):
                    self.updateRate = newRate
                elif self.logData:
                    self.updateRate = 0.1
                else:
                    self.updateRate = float(self.config['CANSERVER']['minUpdateRate'])

            if self.logData:
                self.filename = '/home/pi/CAN/CANServer/python/eKartlog_' + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + '.csv'
                with open(self.filename, "w") as logfile: #  = write (new?)
                    self.csvwriter = csv.writer(logfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    #self.logger.warn(list(self.CAN_Data.keys()))
                    self.csvwriter.writerow(list(self.CAN_Data.keys()))
                    self.initialized = True
            # Init objects
            self.initCanObjects()

        except ValueError:
            self.logger.exception("The received string is not JSON!")
    def initCanObjects(self):
        # setup CAN objects
        for co in self.CAN_Objects:
            # Setup PDO
            if co.mode == "PDO":
                self.node.pdo.tx[1].clear()
                self.node.pdo.tx[1].add_variable(co.key)
                self.node.pdo.tx[1].add_callback(self.pdo_Callback)
                self.node.pdo.tx[1].trans_type = 1
                self.node.pdo.tx[1].enabled = True

                # Save config
                self.node.nmt.state = 'PRE-OPERATIONAL'
                self.node.pdo.save()

                # Set sync
                self.network.sync.start(0.01)

                # Run
                self.node.nmt.state = 'OPERATIONAL'
            # Setup SDO
            elif co.mode == "SDO":
                self.sdo_update(co)
            else:
                self.logger.error("Mode:%s not known!", co.mode)

    # Sends data on the fastest rate of all CAN Objects
    async def producer(self):
        await asyncio.sleep(self.updateRate)

        if self.logData and self.initialized:
            with open(self.filename, "a") as logfile: # a = append
                self.csvwriter = csv.writer(logfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                self.csvwriter.writerow(list(self.CAN_Data.values()))
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
