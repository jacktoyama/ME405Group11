''' This file implements a "dummy" class to use in place of motor driver objects
'''

from pyb import Pin, Timer


class motor_driver:
    
    def __init__(self, TIMERNUM, FREQ_HZ, TIM_CH, PWMPIN, DIR, nSLP):
        '''Initializes a Motor object'''
        # Initialize the timer used by the motor
        self.timer        = Timer(TIMERNUM, freq=FREQ_HZ)
        # Initialize the timer channel, including pins, for the motor and
        # set initial effort to zero
        self.tim_channel  = self.timer.channel(TIM_CH, pin=PWMPIN, 
                                              mode=Timer.PWM, 
                                              pulse_width_percent=0)
        # Define the direction pin
        self.DIR_pin      = Pin(DIR, mode=Pin.OUT_PP, value=0)
        # Define the nSLP pin
        self.nSLP_pin     = Pin(nSLP, mode=Pin.OUT_PP, value=0)
        # Set internal variable for effort to zero (used later in set_effort)
        self.motor_effort = 0
    
    def set_effort(self, effort):
        '''Sets the present effort requested from the motor based on an input value
           between -100 and 100'''
        # Take in user input for effort, pass to PWM as an absolute value
        # (negative PWM cannot be accepted by this method)
        # Also clamps value if out of range
        if abs(effort) > 100:
            self.tim_channel.pulse_width_percent(100)
        else:
            self.tim_channel.pulse_width_percent(abs(effort))
        # Determine if desired effort is negative, and if so, set DIR pin high,
        # else set pin low to ensure correct movement direction
        if effort < 0:
            self.DIR_pin.high()
        else:
            self.DIR_pin.low()
            
    def enable(self):
        '''Enables the motor driver by taking it out of sleep mode into brake mode'''
        # Sets nSLP pin high, enabling motor operations
        self.nSLP_pin.high()
            
    def disable(self):
        '''Disables the motor driver by taking it into sleep mode'''
        # Sets nSLP pin low, disabling motor operations
        self.nSLP_pin.low()