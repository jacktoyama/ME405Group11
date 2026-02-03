import csv
from pathlib import Path
import matplotlib.pyplot as plt


def read_csv(filepath):
    # Initialize line number and output list
    cur_line = 1
    rows = []
    # Open file
    with open(filepath, newline='', encoding='utf-8') as f:
        # Set as csv type
        reader = csv.reader(f)
        # Grab the header line
        header = next(reader, None)
        # For each row, increment 
        for raw_row in reader:
            cur_line += 1
            if len(raw_row) < 2:
                print(f"line: {cur_line} skipped for having < 2 readable values")
                continue
            else:
                row = check_line(raw_row)
                if row != None:
                    rows.append(row)
                else:
                    print(f"line: {cur_line} skipped for having < 2 readable values")
    return header, rows

def check_line(raw_row):
    val1_init = raw_row[0]
    val2_init = raw_row[1]
    
    # Remove comments (everything after #)
    if '#' in val1_init:
        val1_init = val1_init.split('#')[0]
    if '#' in val2_init:
        val2_init = val2_init.split('#')[0]
    
    # Try to convert to float, return None if Error
    try:
        val1 = float(val1_init)
        try: 
            val2 = float(val2_init)
            row = [val1, val2]
            return row
        except ValueError:
            return None
    except ValueError:
        return None


csv_path = "data.csv"
header, rows = read_csv(csv_path)
x, y = zip(*rows)

plt.scatter(x, y, marker='o')
plt.xlabel(header[0])
plt.ylabel(header[1])
plt.grid(True)
plt.show()