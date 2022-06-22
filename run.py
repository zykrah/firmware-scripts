from deserialize import deserialize
from serialize import serialize
from util import read_file, write_file, gen_uid
from converters import kbd_to_qmk_info, kbd_to_via, kbd_to_vial
import json

from json_encoders import * # from qmk_firmware/lib/python/qmk/json_encoders.py, for generating info.json

### GUIDE ###

# Label indices:
#  0  1  2
#  3  4  5
#  6  7  8
#  9 10 11

# Label index to function:
# 0:  (QMK info.json only) If there is text here, it is included as the "label" in the info.json
# 2:  (VIAL only) If there is a 'u' here, the key is included as a key for the unlock combo 
# 3:  Multilayout index
# 4:  (VIAL only) If there is an 'e' here, the key is an encoder
# 5:  Multilayout value
# 6:  Secondary Multilayout name (if there is a list of multilayout options e.g. more than 2 bottom row layouts.)
# 7:  Primary Multilayout name/label (needs to be in at least one of the keys for any given multilayout option.
#     If there is a list of multilayout options, at least one key of each value should have a secondary label in position 6.)
# 9:  Row
# 11: Col

############

# Input an exported json of a KLE that follows the above guide
input_kle_json_path = 'slime88.json'
read_content = read_file(input_kle_json_path)

# Deserialize json
deserialized_path = 'deserialized.json'
keyboard = deserialize(json.loads(read_content))

# To test de/serialization. Should generate same kle json as provided
serialized_path = 'serialized.json'
srlzd = serialize(keyboard)
write_file(serialized_path, json.dumps(srlzd, ensure_ascii=False, indent=2, cls=KLEJSONEncoder))


# Generate a QMK info.json file used for QMK Configurator
qmk_info_path = 'info.json'
qmk_info_content = kbd_to_qmk_info(keyboard)
write_file(qmk_info_path, json.dumps(qmk_info_content, indent=4, separators=(', ', ': '), sort_keys=False, cls=InfoJSONEncoder))


# Generate a VIA json file used to identify a keyboard in VIA
via_vendor_id = '0x7A79'
via_product_id = '0x0000'
via_json_path = 'via.json'
via_json_content = kbd_to_via(keyboard, via_vendor_id, via_product_id)
write_file(via_json_path, json.dumps(via_json_content, ensure_ascii=False, indent=2, cls=KLEJSONEncoder))


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