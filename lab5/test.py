import csv
import matplotlib.pyplot as plt

time_ms = []
centroid = []

with open("lab5p2.csv", "r") as file:
    reader = csv.reader(file)
    next(reader)  # Skip header row
    for row in reader:
        centroid.append(float(row[0]))
        time_ms.append(float(row[1]))

plt.plot(time_ms, centroid)
plt.xlabel("Time (ms)")
plt.ylabel("Centroid")
plt.title("Centroid vs Time")
plt.grid(True)
plt.show()