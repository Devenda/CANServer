# pylint: disable=C0103,C0111
#!/usr/bin/env python3

import json
import asyncio
import random
import websockets
import canopen
import CANObject


class CANServer(object):
    def __init__(self):
        self.CAN_SDO_Objects = []
        self.CAN_PDO_Objects = []
        self.pdoReady = False
        self.pdoDataDict = dict()
        self.nodeNo = 0
        self.node = None

    def initNetwork(self):
        pdoClear = False
        network = canopen.Network()

        self.node = network.add_node(
            38, '/home/pi/CAN/CANServer/os123xes.eds')
        network.connect(channel='can0', bustype='socketcan', bitrate=125000)

        # Setup PDO, SDO not needed
        for co in self.CAN_PDO_Objects:
            if not pdoClear:
                self.node.pdo.tx[1].clear()
                pdoClear = True
            self.node.pdo.tx[1].add_variable(co.key)
            self.node.pdo.tx[1].add_callback(self.pdo_Callback)
            self.node.pdo.tx[1].trans_type = 1
            self.node.pdo.tx[1].enabled = True
        pdoClear = False  # New config will be saved
        # Save config
        self.node.nmt.state = 'PRE-OPERATIONAL'
        self.node.pdo.save()

        # Set sync
        network.sync.start(0.01)

        # Run
        self.node.nmt.state = 'OPERATIONAL'

    # Decode JSON config file and make CAN objects
    async def consumer(self, message):
        canObjectList = json.loads(message)
        print('Config received:', canObjectList)
        # Get each CANObject from webpage
        for cod in canObjectList:
            # Warn when multiple nodes are used
            if self.nodeNo != cod["node"] and self.nodeNo != 0:
                print('Warning: New node detected:', self.node)
                self.nodeNo = cod["node"]
            # Assign node for first config
            if self.nodeNo != cod["node"] and self.nodeNo == 0:
                print('Node:', self.nodeNo)
                self.nodeNo = cod["node"]
            # node = None, because node not yet initialized
            print(cod)

            # save can objects to correct list (filter on mode, sdo, pdo)
            if cod["mode"] == 'SDO':
                self.CAN_SDO_Objects.append(CANObject.CANObject(cod["node"], cod["key"], cod["mode"],
                                                                cod["toMin"], cod["toMax"],
                                                                cod["fromMin"], cod["fromMax"]))
            elif cod["mode"] == 'PDO':
                self.CAN_PDO_Objects.append(CANObject.CANObject(cod["node"], cod["key"], cod["mode"],
                                                                cod["toMin"], cod["toMax"],
                                                                cod["fromMin"], cod["fromMax"]))
            else:
                print('Error, mode: ', cod["mode"], ' unknown!')
        # Init network, start driver
        self.initNetwork()

    def pdo_Callback(self, message):
        coDict = dict()
        for co in self.CAN_PDO_Objects:
            print(message[co.key].raw)
            coDict[co.key] = message[co.key].raw
        self.pdoDataDict = coDict
        self.pdoReady = True

    async def producer(self):
        coDict = dict()

        if self.pdoReady:
            coDict.update(self.pdoDataDict)
        # for co in self.CAN_SDO_Objects:
        #     print('co key found:')
        #     print(co.key)
        #     print('co value:')
        #     print(await co.getData(self.node))
        #     coDict[co.key] = await co.getData(self.node)
        # await asyncio.sleep(0.5)
        # print(json.dumps(coDict))
        # return json.dumps(coDict)
        coDict = {'One': 1, 'Two': 2, 'Three': 3}
        await asyncio.sleep(0.5)
        return json.dumps(coDict)

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


cs = CANServer()
start_server = websockets.serve(
    cs.handler, '127.0.0.1', 5678)  # For windows PC
# start_server = websockets.serve(cs.handler, '192.168.1.123', 5678) # For PI

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
