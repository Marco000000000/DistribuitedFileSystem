import json
import matplotlib.pyplot as plt
import numpy as np

# Specify the path to your input JSON file
input_file_path = 'std_Throughput.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    data = json.load(file)

fourth_elements = []
fourth_elements_view = []
i = 0

for inner_list in data:
    
        fourth_elements.append([i, inner_list[1]])
        fourth_elements_view.append(inner_list[1])
        i += 1

# Create a plot
plt.plot(fourth_elements_view, marker='o')
plt.title('Latency')
plt.xlabel('Sample')
plt.ylabel('Latency (s)')



# Show the plot
plt.show()
