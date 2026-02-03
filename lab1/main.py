"""
Created on Tue Jan 6 12:32:37 2026
@authors: Jameson Stengel, Jack Toyama
"""
from pyb import Pin, Timer, ADC
from time import sleep_ms
from array import array

# Set the enable and reverse pins for both motors.
enable_left = Pin(Pin.cpu.B3, mode = Pin.OUT_PP)
enable_right = Pin(Pin.cpu.A6, mode = Pin.OUT_PP)
reverse_left = Pin(Pin.cpu.B5, mode = Pin.OUT_PP)
reverse_right = Pin(Pin.cpu.A7, mode = Pin.OUT_PP)
# Set the timers and channels for both motors.
tim3 = Timer(3, freq=20000)
t3ch1 = tim3.channel(1, pin=Pin.cpu.B4, mode=Timer.PWM, pulse_width_percent=50)
tim4 = Timer(4, freq=20000)
t4ch1 = tim4.channel(1, pin=Pin.cpu.B6, mode=Timer.PWM, pulse_width_percent=50)
# Set up timer objects and channels for both encoders.
tim1 = Timer(1, period = 0xFFFF, prescaler = 0)
t1ch1 = tim1.channel(1, pin=Pin.cpu.A8, mode=Timer.ENC_AB)
t1ch2 = tim1.channel(2, pin=Pin.cpu.A9, mode=Timer.ENC_AB)
tim2 = Timer(2, period = 0xFFFF, prescaler = 0)
t2ch1 = tim2.channel(1, pin=Pin.cpu.A0, mode=Timer.ENC_AB)
t2ch2 = tim2.channel(2, pin=Pin.cpu.A1, mode=Timer.ENC_AB)
# Initialize both motors by disabling them.
enable_left.low()
enable_right.low()
reverse_left.low()
reverse_right.low()
# Run test sequence (both off, left on 1s, off 1s, right on 1s, off 1s, both on 70%, both on 10%, both reversed 10%)
sleep_ms(1000)
enable_left.high()
sleep_ms(1000)
enable_left.low()
sleep_ms(1000)
enable_right.high()
sleep_ms(1000)
enable_right.low()
sleep_ms(1000)
t3ch1.pulse_width_percent(70)
t4ch1.pulse_width_percent(70)
enable_left.high()
enable_right.high()
sleep_ms(500)
t3ch1.pulse_width_percent(10)
t4ch1.pulse_width_percent(10)
sleep_ms(1000)
reverse_left.high()
reverse_right.high()
sleep_ms(1000)
#enable_left.low()
#enable_right.low()

while True:
    print(tim1.counter())
    print(tim2.counter())
    sleep_ms(333)