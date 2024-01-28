from datetime import datetime
import json
import matplotlib.pyplot as plt
import numpy as np

# Specify the path to your input JSON file
input_file_path = 'latency_sorted.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    datai = json.load(file)

fourth_elements = []
fourth_elements_view = []
i = 0
data=[]
for inner_list in datai:
    if inner_list[2] < 15:
        fourth_elements.append([i, inner_list[2]])
        fourth_elements_view.append(inner_list[2])
        data.append(inner_list)
        i += 1
print(data[-1])
finalData=datetime.strptime(data[-1][3], '%Y-%m-%d %H:%M:%S')
firstData=datetime.strptime(data[1][3], '%Y-%m-%d %H:%M:%S')

finalSeconds= finalData.hour*3600+finalData.minute*60+finalData.second
firstSeconds= firstData.hour*3600+firstData.minute*60+firstData.second
#tsr.json
samples=int((finalSeconds-firstSeconds)/5)
step=5 #secondi
index=0
lastValue=0
data1=[]
print(samples,finalSeconds,firstSeconds)
for value in range(0, samples*5, 5):
    tempData=datetime.strptime(data[index][3], '%Y-%m-%d %H:%M:%S')
    tempSeconds= tempData.hour*3600+tempData.minute*60+tempData.second
    data1.append([str(value),data[index][2]])
    if(tempSeconds-firstSeconds<=value):
        index+=1
output_json_path = 'StepLatency.json'

# Write the sorted data to a new JSON file
with open(output_json_path, 'w') as json_file:
    json.dump(data1, json_file, indent=2)
# Create a plot
plt.plot(fourth_elements_view, marker='o')
plt.title('Latency')
plt.xlabel('Sample')
plt.ylabel('Latency (s)')



# Show the plot
plt.show()
