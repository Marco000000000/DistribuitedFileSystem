import json

# Specify the path to your input file
input_file_path = 'throughput.txt'

# Specify the path to your output JSON file
output_json_path = 'throughput.json'

# Read the file and load its content into a Python list
with open(input_file_path, 'r') as file:
    data = json.load(file)

# Write the data to a new JSON file
with open(output_json_path, 'w') as json_file:
    json.dump(data, json_file, indent=2)  # 'indent' is optional and adds formatting for better readability
