#!/usr/bin/env python3.6

# import canopen
# network = canopen.Network()
# node = network.add_node(1, 'os123xes.eds')
# print(node.pdo.tx[1].clear())
# print(node.pdo.tx[1].add_variable('Motor Speed'))


# pylint: disable=C0103
import canopen
import time
import struct

# setup
# Start with creating a network representing one CAN bus
network = canopen.Network()
# Add some nodes with corresponding Object Dictionaries
# original file had a '%' should be '%%'
node = network.add_node(38, 'os123xes.eds')
#node = network.add_node(38, '/home/pi/CAN/CAN Driver/os123xes.eds')
network.connect(channel='can0', bustype='socketcan', bitrate=125000)


# # scan for all nodes:
# # This will attempt to read an SDO from nodes 1 - 127
# network.scanner.search()
# # We may need to wait a short while here to allow all nodes to respond
# time.sleep(30)
# for node_id in network.scanner.nodes:
#     print("Found node %d!" % node_id)
# ==> worked, found 38

# # try reading device config
# # Open the Store EDS variable as a file like object
# infile = node.sdo[0x1021].open('r', encoding='ascii')
# # Open a file for writing to
# outfile = open('out.eds', 'w', encoding='ascii')
# # Iteratively read lines from node and write to file
# outfile.writelines(infile)
# # Clean-up
# infile.close()
# outfile.close()
# ==> did not work, 0x1021 does not exist


# # Read a variable using SDO
print(node.sdo[0x3464].raw) #==> device name
# while True:
#     # # product id
#     # print(node.sdo[0x3464].raw, "Bits", node.sdo[0x3464].bits)
#     # data = node.sdo.upload(0x3464, 0)
#     # print("", data)

#     # motor RPM
#     # data = node.sdo.upload(0x3207, 0)
#     # print("", data)
#     print("Raw",node.sdo['Motor Speed'].raw, "Phys", node.sdo['Motor Speed'].phys)
#     print("Raw",node.sdo[0x3215].raw, "Phys", node.sdo[0x3215].phys)

#     time.sleep(0.1)
# Read values, but most of the time we get type error


#Try PDO config
node.pdo.tx[1].clear()
# node.pdo.tx[1].add_variable(0x1018, 1)  # Vendor Id
node.pdo.tx[1].add_variable('Motor Speed')  # get RPM
# node.pdo.tx[1].trans_type = 1
# node.pdo.tx[1].enabled = True
# node.pdo.read()

# # Using a callback to asynchronously receive values
# def print_speed(message):
#     print(message[0x1018, 1].phys)


# node.pdo.tx[4].add_callback(print_speed)
# time.sleep(5)

# # Save new configuration (node must be in pre-operational)
# node.nmt.state = 'PRE-OPERATIONAL'
# node.pdo.save()
# # Read current PDO configuration
# node.pdo.read()

# # Start SYNC message with a period of 100 ms
# network.sync.start(0.1)

# # Start PDO
# node.nmt.state = 'OPERATIONAL'


# # Write a variable using SDO
# node.sdo['Producer heartbeat time'].raw = 1000

# # Read PDO configuration from node
# node.pdo.read()
# # Transmit SYNC every 100 ms
# network.sync.start(0.1)

# # Change state to operational (NMT start)
# node.nmt.state = 'OPERATIONAL'

# # Read a value from Tx PDO 1
#node.pdo.tx['Record Number 0x1400'].wait_for_reception()
# speed = node.pdo.tx[1]['ApplicationStatus.ActualSpeed'].phys

# Disconnect from CAN bus
# network.sync.stop()
# network.disconnect()

