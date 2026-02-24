import serial
import time

def read_until_idle(ser, idle_timeout=0.3):
    """
    Read lines from serial until no new data arrives for idle_timeout seconds.
    Returns a list of decoded line strings.
    """
    lines = []
    ser.timeout = 0.05  # Short read timeout so readline() doesn't block long
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            print(line)
            lines.append(line)
        else:
            # readline() returned empty — check if device has gone quiet
            if not ser.in_waiting:
                break
    return lines

ser = serial.Serial(
    port="COM4",
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=0.1
)

time.sleep(2)

try:
    while True:
        cmd = input(">> ")
        ser.write((cmd + "\n").encode())
        if cmd.lower() == "g":
            time.sleep(1.1)  # Wait for full data dump to buffer
            lines = []
            while ser.in_waiting:
                line = ser.readline().decode(errors="ignore").strip()
                print(line)
                lines.append(line)
        else:
            lines = read_until_idle(ser)

except KeyboardInterrupt:
    print("shutting down")
    ser.close()