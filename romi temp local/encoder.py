''' This file implements a "dummy" class to use in place of encoder objects
'''

from random import random
from time import ticks_us, ticks_diff   # Use to get dt value in update()
from pyb import Timer
import math

class encoder:

    def __init__(self, timnum, PERIOD, PRESCALE, chA_pin, chB_pin):
        '''Initializes an Encoder object'''
        # Initialize the individual timer used by this encoder
        self.timer = Timer(timnum, period = PERIOD, prescaler = PRESCALE)
        # Set both timer channels in order (will always be in 1-2 order)
        self.tim_ch1 = self.timer.channel(1, pin=chA_pin, mode=Timer.ENC_AB)
        self.tim_ch2 = self.timer.channel(2, pin=chB_pin, mode=Timer.ENC_AB)
        
        self.position   = 0     # Total accumulated position of the encoder
        self.prev_count = 0     # Counter value from the most recent update
        self.delta      = 0     # Change in count between last two updates
        self.ticks_prev = 0     # Previous time value on update.
        self.dt         = 0     # Amount of time between last two updates
    
    def update(self):
        '''Runs one update step on the encoder's timer counter to keep
           track of the change in count and check for counter reload'''
        self.delta = self.timer.counter()-self.prev_count
        if self.delta < -(0xFFFF + 1)/2:
            self.delta += 0xFFFF + 1
        if self.delta > (0xFFFF + 1)/2:
            self.delta -= 0xFFFF + 1
        self.delta = ((self.delta/12)/119.76)*35*2*math.pi
        self.position += self.delta
        self.prev_count = self.timer.counter()
        self.dt = ticks_diff(ticks_us(), self.ticks_prev)
        self.ticks_prev = ticks_us()
            
    def get_position(self):
        '''Returns the most recently updated value of position as determined
           within the update() method'''
        return self.position
            
    def get_velocity(self):
        '''Returns a measure of velocity using the the most recently updated
           value of delta as determined within the update() method'''
        return self.delta/(self.dt/1000000)
    
    def zero(self):
        '''Sets the present encoder position to zero and causes future updates
           to measure with respect to the new zero position'''
        self.position = 0
        self.prev_count = 0
        self.timer.counter(0)