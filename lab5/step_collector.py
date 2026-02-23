import serial
import time
import csv
import re
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt


def read_csv(filepath):
    cur_line = 1
    rows = []
    with open(filepath, "r") as f:
        header = f.readline().strip(" \n").split(",")
        if len(header) < 4:
            print("header has less than 4 values")
            return None
        for line in f:
            cur_line += 1
            raw_row = line.strip(" \n")
            raw_row = raw_row.split("#", 1)[0]
            raw_row = raw_row.split(",")
            if len(raw_row) < 4:
                print(f"line: {cur_line} skipped for having < 4 readable values. Line content: {line}")
                continue
            try:
                raw_row = [float(val) for val in raw_row[:4]]
            except ValueError:
                print(f"line: {cur_line} skipped for having invalid value")
                continue
            rows.append(raw_row)
    return header, rows

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


log_dir = Path("collectionLog")
log_dir.mkdir(exist_ok=True)

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
        lines = read_until_idle(ser)

except KeyboardInterrupt:
    print("shutting down")
    ser.close()