from serial import deserialize
from util import read_file
from layouts import get_specific_layout
import json

# Input an exported json of a KLE that follows the guide (See README.md)
input_kle_json_path = 'test-json.json'
read_content = read_file(input_kle_json_path)

# Deserialize json
deserialized_path = 'deserialized.json'
keyboard = deserialize(json.loads(read_content))

get_specific_layout(keyboard, [])
