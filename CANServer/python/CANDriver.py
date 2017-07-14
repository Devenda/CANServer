# pylint: disable=C0103,C0111
#!/usr/bin/env python3
import asyncio
import logging
import websockets
import CANServer


def main():
    # Setup logger
    logging.basicConfig(filename='/home/pi/CAN/CANServer/CANServer/python/CANDriver.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logging.info('Logger setup done, starting web server')

    try:
        cs = CANServer.CANServer()
        # start_server = websockets.serve(cs.handler, '127.0.0.1', 5678)  # For windows PC
        start_server = websockets.serve(cs.handler, '172.24.1.1', 5678)  # For PI
    except Exception as e:
        logging.exception("Error starting websocket")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        self.logger.exception("Unforseen error")
        raise