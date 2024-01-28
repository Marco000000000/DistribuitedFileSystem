import json
import matplotlib.pyplot as plt

# Specify the path to your input JSON file
input_file_path = 'latency_sorted.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    data = json.load(file)

# Extract the fourth element of each inner list
fourth_elements = [inner_list[2] for inner_list in data]

# Create a plot
plt.plot(fourth_elements, marker='o')
plt.title('Latency')
plt.xlabel('Sample')
plt.ylabel('Latency (s)')

# Show the plot
plt.show()
