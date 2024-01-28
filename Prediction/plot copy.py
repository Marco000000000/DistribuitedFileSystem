import json
import matplotlib.pyplot as plt

# Specify the path to your input JSON file
input_file_path = 'throughput_sorted.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    data = json.load(file)

fourth_elements = []

for inner_list in data:
    if inner_list[2] != 10000000000000 and inner_list[2] != 0:
        fourth_elements.append(inner_list[2]/1000000)

# Create a plot
plt.plot(fourth_elements, marker='o')
plt.title('Throughput')
plt.xlabel('Sample')
plt.ylabel('Throughput (Mbps)')

# Show the plot
plt.show()
