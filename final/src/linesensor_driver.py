'''
linesensor_driver class: initializes pins, calibrates, and finds centroid for line following 
'''

import random, pyb
from utime import ticks_ms, ticks_diff

class linesensor:
    def __init__(self, pins: tuple, spacing: float):
        self._last_print = ticks_ms()
        self.pinObjects = []
        self.pinPositions = []
        self.whiteCal = []
        self.blackCal = []
        self.centroid = 0
        self.spacing = spacing
        n = -((len(pins)-1)/2)
        for pin in pins:
            currentADC = pyb.ADC(pin)
            self.pinObjects.append(currentADC)
            self.pinPositions.append(self.spacing*n)
            #print(str(self.pinPositions))
            self.whiteCal.append(0)
            self.blackCal.append(1)
            n += 1
        
    def calwhite(self):
        for i, value in enumerate(self.whiteCal):
            # Get pin output from relevant sensor pin using white paper as reference. Store values in whiteCal list as references.
            self.whiteCal[i] = self.pinObjects[i].read()
        print(self.whiteCal)
    def calblack(self):
        for i, value in enumerate(self.blackCal): 
            # Get pin output from relevant sensor pin using black paper as reference. Store values in blackCal list as references.
            self.blackCal[i] = self.pinObjects[i].read()
        print(self.blackCal)

    def findCentroid(self):
        pos_times_val = 0
        total_val = 0
        for i, pinObject in enumerate(self.pinObjects):
            # Get pin output from relevant sensor pin. Adjust based on calibration values.
            denom = self.blackCal[i] - self.whiteCal[i]
            if denom == 0:
                currentValue = 0
            else:
                currentValue = (self.whiteCal[i] - pinObject.read()) / (self.whiteCal[i] - self.blackCal[i])
            currentValue = max(0.0, min(currentValue, 1.0))
            # Multiply this calibrated value by sensor position.
            pos_times_val += self.pinPositions[i]*currentValue
            total_val += currentValue
        if not total_val == 0:
            #print(str(pos_times_val))
            #print(total_val)
            self.centroid = max(-24, min(pos_times_val/total_val, 24))
        return self.centroid, total_val
    
    def printNormalized(self, interval_ms=200):
        now = ticks_ms()
        if ticks_diff(now, self._last_print) >= interval_ms:
            self._last_print = now
            vals = []
            for i, pinObject in enumerate(self.pinObjects):
                denom = self.blackCal[i] - self.whiteCal[i]
                if denom == 0:
                    vals.append(0.0)
                else:
                    norm = (pinObject.read() - self.whiteCal[i]) / denom
                    vals.append(round(norm, 2))
            #print([pin.read() for pin in self.pinObjects])
            #print(vals)
            #print(sum(vals))



