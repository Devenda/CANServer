# pylint: disable=C0103,C0111
#!/usr/bin/env python3
import asyncio
import logging
import websockets
import CANServer


def main():
    # Setup logger
    logging.basicConfig(filename='CANDriver.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logging.info('Logger setup done, starting web server')

    cs = CANServer.CANServer()
    # start_server = websockets.serve(cs.handler, '127.0.0.1', 5678)  # For
    # windows PC
    start_server = websockets.serve(
        cs.handler, '192.168.1.123', 5678)  # For PI

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()


if __name__ == '__main__':
    main()
