# pylint: disable=C0103,C0111
#!/usr/bin/env python3


class CANObject(object):
    def __init__(self, node, key, mode=None, toMin=None, toMax=None, fromMin=None, fromMax=None):
        self.node = node
        self.key = key
        self.mode = mode

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
        return self.toMin + (valueScaled * toSpan)

    async def getData(self, canNode):
        print('mode', self.mode)
        if self.mode == 'sdo':
            data = str(canNode.sdo[self.key].raw)
            return data
