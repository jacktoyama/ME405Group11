import random, pyb

class linesensor:
    def __init__(self, pins: tuple, spacing: float):
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
            currentValue = (pinObject.read()-self.whiteCal[i])/(self.blackCal[i]-self.whiteCal[i])
            # Multiply this calibrated value by sensor position.
            pos_times_val += self.pinPositions[i]*currentValue
            total_val += currentValue
        if not total_val == 0:
            #print(str(pos_times_val))
            #print(str(total_val))
            self.centroid = max(-24, min(pos_times_val/total_val, 24))
        return self.centroid

