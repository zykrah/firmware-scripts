from serial import serialize, deserialize
from util import read_file, write_file, gen_uid, MCU_DICT
from converters import kbd_to_qmk_info, kbd_to_vial, kbd_to_keymap, layout_str_to_layout_dict, keycodes_md_to_keycode_dict, generate_keycode_conversion_dict, kbd_to_main_config, extract_matrix_pins
import json
import requests

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
name = 'Slime88'
maintainer = 'Zykrah'
manufacturer = 'MANUFACTURER'
url = ""
vid = "0xFEED"
pid = "0x0001"
ver = "0.0.1"
layers=4
mcu_choice = "RP2040" # choose from MCU_PRESETS

try: # KiCAD Netlist (for pins)
    netlist = read_file('slime88.net')
except FileNotFoundError:
    netlist = None

mcu_dict = MCU_DICT[mcu_choice]
mcu = mcu_dict['mcu']
bootloader = mcu_dict['bootloader']
board = mcu_dict['board']
if netlist:
    output_pin_pref = mcu_dict['output_pin_pref']
    schem_pin_pref = mcu_dict['schem_pin_pref']

diode_dir = "COL2ROW" # default
if mcu_choice != 'None' and netlist:
    try:
        pin_dict = extract_matrix_pins(netlist, mcu, output_pin_pref, schem_pin_pref)
    except Exception as e:
        raise Exception(f"Invalid netlist provided!, {e}")
elif mcu_choice == 'None' and netlist:
    raise Exception("You need to choose a MCU preset to utilise the netlist function!")
else:
    pin_dict = {}

qmk_info_path = 'info.json'
qmk_info_content = kbd_to_qmk_info(keyboard, name, maintainer, url, vid, pid, ver, mcu, bootloader, board, pin_dict, diode_dir, manufacturer)
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

#keyboard_h_content = kbd_to_layout_macro(keyboard)


keymap_c_path = 'keymap.c'
layout_dict = layout_str_to_layout_dict(read_file('vil.json'))
link = "https://raw.githubusercontent.com/qmk/qmk_firmware/master/docs/keycodes.md"
keycodes_dict = keycodes_md_to_keycode_dict(requests.get(link).text)
# keycodes_dict = keycodes_md_to_keycode_dict(read_file('keycodes.md')) # Local fallback
conversion_dict = generate_keycode_conversion_dict(read_file('deprecated_keycodes.txt'))

keymap_c_content = kbd_to_keymap(keyboard, layers, 1, layout_dict, keycodes_dict, conversion_dict)
write_file(keymap_c_path, keymap_c_content)

main_config_h_content = kbd_to_main_config(keyboard, layers)
write_file('config.h', main_config_h_content)
