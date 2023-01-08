from serial import serialize, deserialize
from util import read_file, write_file, gen_uid
from converters import kbd_to_qmk_info, kbd_to_vial
import json

from json_encoders import * # from qmk_firmware/lib/python/qmk/json_encoders.py, for generating info.json

# Input an exported json of a KLE that follows the guide (See README.md)
input_kle_json_path = 'test-json.json'
read_content = read_file(input_kle_json_path)

# Deserialize json
deserialized_path = 'deserialized.json'
keyboard = deserialize(json.loads(read_content))

# To test de/serialization. Should generate same kle json as provided
serialized_path = 'serialized.json'
srlzd = serialize(keyboard)
write_file(serialized_path, json.dumps(srlzd, ensure_ascii=False, indent=2, cls=KLEJSONEncoder))

# Test parity:
print(f"Deserialized and Serialized JSONs are identical: {read_file(input_kle_json_path) == read_file(serialized_path)}")

# Generate a QMK info.json file used for QMK Configurator
qmk_info_path = 'info.json'
qmk_info_content = kbd_to_qmk_info(keyboard)
write_file(qmk_info_path, json.dumps(qmk_info_content, indent=4, separators=(', ', ': '), sort_keys=False, cls=InfoJSONEncoder))


# Generate a VIAL json file used to identify a keyboard in VIAL. Same as via but with encoders and no required product/vendor ID
# Also generate a config.h file with a randomly generated UID and unlocking combo (if included)
vial_vendor_id = '0x7A79'
vial_product_id = '0x0000'
vial_uid = gen_uid()
vial_json_path = 'vial.json'
vial_config_h_path = 'config.h'
vial_json_content, vial_config_h = kbd_to_vial(keyboard, vial_uid, vial_vendor_id, vial_product_id)
write_file(vial_json_path, json.dumps(vial_json_content, ensure_ascii=False, indent=2, cls=KLEJSONEncoder))
write_file(vial_config_h_path, vial_config_h)
