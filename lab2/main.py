# -*- coding: utf-8 -*-
"""
Created on Tue Jan 27 13:03:45 2026

@author: Jameson Stengel
"""

from encoderdriver_winter import Encoder
from motordriver_winter import Motor
from pyb import Pin, Timer
from time import ticks_us, ticks_diff, ticks_add

interval = 333333 # interval in microseconds
start = ticks_us()
loops = 0

encoder_L = Encoder(1, 0xFFFF, 0, Pin.cpu.A9, Pin.cpu.A8)
encoder_R = Encoder(2, 0xFFFF, 0, Pin.cpu.A1, Pin.cpu.A0)
# def __init__(self, PWM, DIR, nSLP):
motor_L = Motor(3, 20000, 1, Pin.cpu.B4, Pin.cpu.B5, Pin.cpu.B3)
motor_R = Motor(4, 20000, 1, Pin.cpu.B6, Pin.cpu.A7, Pin.cpu.A6)

motor_L.set_effort(20)
motor_R.set_effort(20)
motor_L.enable()
motor_R.enable()

deadline = ticks_add(start, interval)

while True:
    now = ticks_us()
    if ticks_diff(deadline, now) <= 0:
        if loops == 15:
            motor_L.disable()
            motor_R.disable()
        if loops == 30:
            motor_L.set_effort(-30)
            motor_R.set_effort(-30)
            motor_L.enable()
            motor_R.enable()
        if loops == 45:
            motor_L.set_effort(30)
            motor_R.disable()
        if loops == 60:
            motor_L.disable()
            motor_R.set_effort(30)
            motor_R.enable()
        if loops == 75:
            motor_L.set_effort(50)
            motor_L.enable()
            motor_R.set_effort(50)
            motor_R.enable()
        if loops == 150:
            break
        encoder_L.update()
        encoder_R.update()
        print("LEFT ENCODER: Position = " + str(encoder_L.get_position()) + 
              ", Velocity = " + str(encoder_L.get_velocity()))
        print("RIGHT ENCODER: Position = " + str(encoder_R.get_position()) + 
              ", Velocity = " + str(encoder_R.get_velocity()))
        deadline = ticks_add(deadline, interval)
        loops += 1
print("Driver testing complete.")
motor_L.disable()
motor_R.disable()