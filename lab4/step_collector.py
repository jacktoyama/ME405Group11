import serial
import time

# run commands like in putty
# when g is run, data should be saved to a csv and automaticlally turned into a plot

import serial
import time

ser = serial.Serial(
    port="COM4",
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=0.1
)

time.sleep(2)  # give STM32 time to reset if needed

print("Connected. Type commands (Ctrl+C to exit).")

try:
    while True:
        # --- user input ---
        cmd = input(">> ")
        ser.write((cmd + "\n").encode())

        # --- read STM32 response ---
        time.sleep(0.05)
        while ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            print(line)

except KeyboardInterrupt:
    print("\nExiting...")
    ser.close()