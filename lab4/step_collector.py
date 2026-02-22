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

        time.sleep(1.1)

        lines = []
        while ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            print(line)
            lines.append(line)

        capturing = False
        csv_rows = []
        for line in lines:
            if re.match(r'^[\w\s_]+(\s*\(.*?\))?\s*,', line):
                capturing = True
            if capturing:
                if line.startswith('-') or line.startswith('+') or line == '':
                    capturing = False
                    continue
                csv_rows.append(line.rstrip(','))

        if csv_rows:
            timestamp = datetime.now().strftime("%m_%d_%H_%M_%S")
            csv_file = log_dir / f"{timestamp}.csv"
            png_file = log_dir / f"{timestamp}.png"

            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                for row in csv_rows:
                    writer.writerow(row.split(','))
            print(f"[Saved {len(csv_rows) - 1} data rows to {csv_file}]")

            header, rows = read_csv(csv_file)
            time_l, vel_l, time_r, vel_r = zip(*rows)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

            ax1.plot(time_l, vel_l)
            ax1.set_xlabel(header[0])
            ax1.set_ylabel(header[1])
            ax1.set_title("Left Wheel")
            ax1.grid(True)

            ax2.plot(time_r, vel_r)
            ax2.set_xlabel(header[2])
            ax2.set_ylabel(header[3])
            ax2.set_title("Right Wheel")
            ax2.grid(True)

            plt.tight_layout()
            plt.savefig(png_file)
            plt.close()
            print(f"[Saved plot to {png_file}]")

except KeyboardInterrupt:
    print("shutting down")
    ser.close()