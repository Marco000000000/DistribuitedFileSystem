import json
from datetime import datetime

# Specify the path to your input JSON file
input_file_path = 'latency.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    data = json.load(file)

# Define a custom sorting key function to extract the date-time and convert it to a datetime object
def sorting_key(inner_list):
    return datetime.strptime(inner_list[3], '%Y-%m-%d %H:%M:%S')

for temp in data:
    print(datetime.strptime(temp[3], '%Y-%m-%d %H:%M:%S'))

# Sort the outer list based on the date-time strings
sorted_data = sorted(data, key=sorting_key)

# Specify the path to your output JSON file
output_json_path = 'latency_sorted.json'

# Write the sorted data to a new JSON file
with open(output_json_path, 'w') as json_file:
    json.dump(sorted_data, json_file, indent=2)  # 'indent' is optional and adds formatting for better readability
