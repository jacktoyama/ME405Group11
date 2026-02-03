import csv
from pathlib import Path
import matplotlib.pyplot as plt


def read_csv(filepath):
    # Initialize line number and output list
    cur_line = 1
    rows = []
    # Open file
    with open(filepath, "r") as f:
        # Grab header
        header = f.readline()
        header = header.strip(" \n")
        header = header.split(",")
        if len(header) < 2:
            print("header has less than 2 values")
            return None
        # For each line 
        for line in f:
            # Increment line number
            cur_line += 1
            # Strip newline and comments, then split into list
            raw_row = line.strip(" \n")

            raw_row = raw_row.split("#", 1)[0]
            raw_row = raw_row.split(",")
            # Skip if less than 2 values or a value cannot be converted to a float
            if len(raw_row) < 2:
                print(f"line: {cur_line} skipped for having < 2 readable values. Line content: {line}")
                continue
            try:
                raw_row = [float(val) for val in raw_row]
            except ValueError:
                print(f"line: {cur_line} skipped for having invalid value")
                continue
            rows.append(raw_row)
    return header, rows

# Set Path
csv_path = "data.csv"
# Run csv function
header, rows = read_csv(csv_path)
x, y = zip(*rows)

# Create plot
plt.scatter(x, y)
plt.xlabel(header[0])
plt.ylabel(header[1])
plt.grid(True)
plt.show()