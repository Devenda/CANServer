# pylint: disable=C0103,C0111
#!/usr/bin/env python3

import json
import asyncio
import logging
import threading
import queue
import random
import canopen
import CANObject


class CANServer(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info('Logger Added')

        self.CAN_Objects = []
        self.CAN_Data = {}

        self.updateRate = 1.0  # float()

        self.network = canopen.Network()
        self.nodeNo = 0
        self.node =  self.network.add_node(38, 'os123xes.eds')

        self.networkStarted = False

        self.q = queue.Queue(maxsize=0)
        
        # Starting CAN worker thread
        cw = threading.Thread(target=self.can_worker)
        cw.daemon = True
        cw.start()

    def initNetwork(self):
        pdoClear = False
        # Disconnect from network when new init is done.
        if self.networkStarted:
            # Empty queue
            self.q.queue.clear()

            #Disconnect from network last to make sure queue is empty
            self.network.disconnect()
            self.networkStarted = False
        
        self.network.connect(channel='can0', bustype='socketcan', bitrate=125000)
        self.networkStarted = True

        # setup CAN objects
        for co in self.CAN_Objects:
            # Add key to data dict with initial value
            self.CAN_Data[co.key] = 0

            # Setup PDO
            if co.mode == "PDO":
                if not pdoClear:
                    self.node.pdo.tx[1].clear()
                    pdoClear = True
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
                print("Error, mode", co.mode, "not known")

    # Callback for when PDO data is available
    def pdo_Callback(self, message):
        print("PDO callback called")
        # Add data to Data dict
        for co in self.CAN_Objects:
            if co.mode == "pdo":
                self.CAN_Data[co.key] = message[co.key].raw

        # ToDo send data each time PDO data received

    # Gets all CAN Objects from the queue and gets there actual data
    def can_worker(self):
        while True:
            co = self.q.get()
            #print("Set update for:", co.key)
            self.CAN_Data[co.key] = co.getData(self.node)
            self.q.task_done()

    # Gets called after a time defined by the update rate of the SDO object
    def sdo_update(self, co: CANObject.CANObject):
        # push co on CAN worker queue
        self.q.put(co)

        # Restart SDO timer
        #print("restarting timer with update rate:", float(co.updateRate))
        if co in self.CAN_Objects:
            threading.Timer(float(co.updateRate),
                            self.sdo_update, args=(co, )).start()

    # Decode JSON config file and make CAN objects
    async def consumer(self, message):
        canObjectList = json.loads(message)
        print('Config received:', canObjectList)
        # Get each CANObject from webpage
        # ToDo move to init?
        for co in canObjectList:
            # Warn when multiple nodes are used
            if self.nodeNo != co["node"] and self.nodeNo != 0:
                print('Warning: New node detected:', self.node)
                self.nodeNo = co["node"]
            # Assign node for first config
            if self.nodeNo != co["node"] and self.nodeNo == 0:
                print('Node:', self.nodeNo)
                self.nodeNo = co["node"]
            # node = None, because node not yet initialized

            # save can objects
            self.CAN_Objects.append(CANObject.CANObject(co["node"], co["key"], co["mode"],
                                                        co["updateRate"], co["toMin"], co["toMax"],
                                                        co["fromMin"], co["fromMax"]))
            # Init CAN Data dict with all keys and data = 0
            self.CAN_Data[co["key"]] = "0"

            # set update rate to fastest rate of all co
            newRate = float(co["updateRate"])
            if newRate < self.updateRate:
                self.updateRate = newRate
        # Init network, start driver
        self.initNetwork()

    # Sends data on the fastest rate of all CAN Objects
    async def producer(self):
        await asyncio.sleep(self.updateRate)
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
