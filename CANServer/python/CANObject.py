# pylint: disable=C0103,C0111
#!/usr/bin/env python3
import canopen
import logging


class CANObject(object):
    # todo default bij None?
    def __init__(self, node, key, mode=None, updateRate=None, toMin=None, toMax=None, fromMin=None, fromMax=None):
        self.logger = logging.getLogger(__name__)
        self.logger.info('CANObject Logger Added')

        self.node = node
        self.key = key
        self.mode = mode
        self.updateRate = updateRate

        self.toMin = toMin
        self.toMax = toMax

        self.fromMin = fromMin
        self.fromMax = fromMax

    def translate(self, value):
        # Figure out how 'wide' each range is
        fromSpan = self.fromMax - self.fromMin
        toSpan = self.toMax - self.toMin

        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - self.fromMin) / float(fromSpan)

        # Convert the 0-1 range into a value in the right range.
        return int(round(self.toMin + (valueScaled * toSpan)))

    def getData(self, canNode: canopen.Node):
        if self.mode == 'SDO':
            try:
                #use lib to get data
                coDatatype = canNode.object_dictionary[self.key].data_type
                possibleCoDatatypes = canopen.objectdictionary.Variable.STRUCT_TYPES

                rawData = canNode.sdo[self.key].data
                # unpack_from instead of unpack, to ignore extra bytes send.
                data = (possibleCoDatatypes[coDatatype].unpack_from(rawData))[0]
                scaledData = self.translate(data)

                self.logger.info("%s: Raw Data:%s Converted data: %s",
                             self.key, data, scaledData)

                return str(scaledData)
            except Exception as e:
                self.logger.exception("An error occured while requesting data from the CAN slave")
            
                return str(0)
            
        else:
            self.logger.error(
                "getData called on non SDO object, mode:%s", self.mode)
