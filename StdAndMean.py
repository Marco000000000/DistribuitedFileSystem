from datetime import datetime
import json
import matplotlib.pyplot as plt
import numpy as np

# Specify the path to your input JSON file
input_file_path = 'StepLatency.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    datai = json.load(file)
data=[]
for i in datai:
    data.append(i[1])
index=0
std=[]
mean=[]
times=100
step=5
output_json_std = 'std_Latency.json'
output_json_mean = 'mean_Latency.json'




print((len(data)-times))
for i in range(len(data)-times):
    std.append([str(step*i),np.std(data[i:i+times])])
    mean.append([str(step*i),np.mean(data[i:i+times])])

# Write the sorted data to a new JSON file
with open(output_json_std, 'w') as json_file:
    json.dump(std, json_file, indent=2)
    # Write the sorted data to a new JSON file
with open(output_json_mean, 'w') as json_file:
    json.dump(mean, json_file, indent=2)
# Create a plot


plt.plot(std, marker='o')
plt.title('Latency')
plt.xlabel('Sample')
plt.ylabel('Latency (s)')
plt.show()
plt.plot(mean, marker='o')
plt.title('Latency')
plt.xlabel('Sample')
plt.ylabel('Latency (s)')
plt.show()
# Show the plot
