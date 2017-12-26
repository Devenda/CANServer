# pylint: disable=C0103,C0111
#!/usr/bin/env python3
import configparser
import asyncio
import logging
import websockets
import CANServer
import os

def main():
    # Get config
    config = configparser.ConfigParser()
    config.read('/home/pi/CAN/CANServer/python/CANSERVER.INI')    

    # Setup logger
    logging.basicConfig(filename=config['CANDRIVER']['LogFilePath'],
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logging.info('Logger setup done, starting web server')
    logging.info('does path exist?:')
    logging.info(os.path.exists('/home/pi/CAN/CANServer/python/CANSERVER.INI'))
    try:
        cs = CANServer.CANServer()
        # start_server = websockets.serve(cs.handler, '127.0.0.1', 5678)  # For windows PC
        start_server = websockets.serve(cs.handler, config['CANDRIVER']['WebSocketIp'], config['CANDRIVER']['WebSocketPort'])  # For PI
    except Exception:
        logging.exception("Error starting websocket")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception("Unforseen error")
        raise