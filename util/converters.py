from collections import OrderedDict
from copy import deepcopy
import json
from json import JSONDecodeError
from typing import Any, List, Dict, Tuple, Literal

from util.common_keys import COMMON_KEYS, COMMON_MODS
from util.serial import Keyboard, KeyboardMetadata, serialize, deserialize
from util.util import gen_uid, max_x_y, min_x_y, write_file, replace_chars, extract_matrix_pins
from util.layouts import convert_key_list_to_layout, extract_row_col, get_layout_all, extract_ml_val_ndx, get_alternate_layouts

# GENERATE INFO.JSON
# TO-DO:
# - make a way of converting the other way around (INFO.JSON -> KEYBOARD)
# DONE detect bounds of default layout and offset every key by a certain amount
# DONE automatically generate a layout_all based on multilayout with maximum amount of keys
# DONE create functions to easily set certain multilayouts
# DONE make more generic converter
# - be able to manually set the layout_all
# DONE create multiple layouts based on a list of multilayout options

def kbd_to_qmk_info(kbd: Keyboard,
                    name: str = None,
                    maintainer: str = None,
                    url: str = None,
                    vid: str = None,
                    pid: str = None,
                    ver: str = None,
                    mcu: str = None,
                    bootloader: str = None,
                    board: str = None,
                    pin_dict: dict = None,
                    diode_dir: Literal['COL2ROW', 'ROW2COL'] = "COL2ROW",
                    manufacturer: str = None,
                    alt_layouts: Dict[str, List[int]] = None
                    ) -> Dict[str, Any]: # Change to a TypedDict for qmk info dict
    """Converts a Keyboard into a QMK info.json (dict)"""
    # Check for encoder keys (Both VIA and VIAL)
    encoders_num = 0
    for key in kbd.keys:
        # Toggle encoders if a key with encoders detected
        if key.labels[4].startswith('e'):
            if key.labels[4] == 'e': # VIAL
                enc_val = int(key.labels[9])

            if len(key.labels[4]) > 1 and key.labels[4][1].isnumeric(): # VIA
                enc_val = int(key.labels[4][1])
            encoders_num = max(encoders_num, enc_val+1)

    # Before we figure out the all layout, generate the alternate layouts
    if alt_layouts:
        _alt_layouts = {}
        for alt_name in alt_layouts.keys():
            # Format nicely
            _alt_layouts['_'.join(alt_name.lower().split())] = alt_layouts[alt_name]
            
        alternate_layout_key_map = get_alternate_layouts(kbd, _alt_layouts)
    else:
        alternate_layout_key_map = None

    rows = 0
    cols = 0

    for key in kbd.keys:
        row, col = extract_row_col(key)

        rows = max(rows, row + 1)
        cols = max(cols, col + 1)

    # Removes all multilayout options except max layouts.
    kbd = get_layout_all(kbd)

    # The final list that will actually be used in the info.json
    qmk_layout_all = convert_key_list_to_layout(kbd.keys)

    if not name:
        if kbd.meta.name:
            name = kbd.meta.name
        else:
            name = 'Keyboard'

    if not maintainer:
        maintainer = 'qmk'

    if not manufacturer:
        manufacturer = 'MANUFACTURER'

    if not url:
        url = ''

    usb = OrderedDict()
    if pid and vid and ver:
        usb["vid"] = vid
        usb["pid"] = pid
        usb["device_version"] = ver

    keyboard = {
        'keyboard_name': name,
        #'url': url,
        'maintainer': maintainer,
        #'usb': usb,
        'manufacturer': manufacturer,
    }

    if not alt_layouts or (len(alternate_layout_key_map.keys()) == 1 and 'all' in alternate_layout_key_map.keys()):
        keyboard['layouts'] = {
            'LAYOUT': {
                'layout': qmk_layout_all
            }
        }
    else:
        keyboard['layouts'] = {
            'LAYOUT_all': {
                'layout': qmk_layout_all
            }
        }
        for layout_name, layout_keys in alternate_layout_key_map.items():
            keyboard['layouts'][f"LAYOUT_{layout_name}"] = {
                'layout': convert_key_list_to_layout(layout_keys)
            }


    if mcu and bootloader:
        keyboard["processor"] = mcu
        keyboard["bootloader"] = bootloader
        keyboard["features"] = {
            'bootmagic': True,
            'command': False,
            'console': False,
            'extrakey': True,
            'mousekey': True,
            'nkro': True
        }
        if board:
            keyboard["board"] = board

    if url:
        keyboard["url"] = url

    if usb:
        keyboard["usb"] = usb

    keyboard["diode_direction"] = diode_dir
    if pin_dict:
        if len(pin_dict["cols"]) != cols or len(pin_dict["rows"]) != rows:
            raise Exception("Number of columns/rows in netlist does not match the KLE!")
        keyboard["matrix_pins"] = pin_dict
    else:
        keyboard["matrix_pins"] = {'cols': ['X', ] * cols, 'rows': ['X', ] * rows}

    if encoders_num:
        if not keyboard.get('features'):
            keyboard["features"] = {}
        keyboard["features"]["encoder"] = True
        keyboard["encoder"] = {'rotary': []}
        for i in range(encoders_num):
            keyboard["encoder"]['rotary'].append({"pin_a": "X", "pin_b": "X"})

    return keyboard


# CONVERT SIMPLIZED KLE TO VIA JSON
# TO-DO
# - detect if keyboard can be converted first
# DONE make a way of converting the other way around (VIA KLE/JSON -> SIMPLIFIED KLE)
# - add way to input the index for which label indices to use for rows/cols/multilayout etc
# - change this function to have a more similar structure to the qmk info converter (for multilayouts)

def kbd_to_vial(kbd: Keyboard,
                vial_uid: str = None,
                vendor_id: str = None,
                product_id: str = None,
                lighting: str = None,
                name: str = None
                ) -> Tuple[Dict[str, Any], str]: # Change to a TypedDict for via/l json dict
    """Converts a Keyboard into a VIA/L JSON file and VIAL config.h"""
    if not lighting:
        lighting = 'none'
    if not name:
        name = kbd.meta.name
    if not vial_uid:
        vial_uid = gen_uid()

    rows = 0
    cols = 0
    ml_keys = [] # list of multilayout keys
    ml_dict = {}
    ml_count = 0 # amount of multilayouts

    vial_kbd = deepcopy(kbd)

    vial_unlock_rows = []
    vial_unlock_cols = []
    
    for key in vial_kbd.keys:
        og_key = deepcopy(key)
        # key colour whitelist
        if not og_key.color in ["#cccccc", "#aaaaaa", "#777777"]:
            key.color = "#cccccc"
        key.color = og_key.color
        key.labels = [None] * 12 # Empty labels
        key.textSize = [None] * 12 # Reset text size

        if og_key.labels[4] == "e": # encoder; VIAL ONLY
            key.labels[4] = og_key.labels[4]

        elif og_key.labels[4].startswith("e"): # encoder; VIA (I know this is included in the VIAL converter, will have to change later)
            key.labels[4] = og_key.labels[4]

        # Matrix coords
        row, col = extract_row_col(og_key)

        # Add if unlock key
        if og_key.labels[2] == "u": 
            vial_unlock_rows.append(row)
            vial_unlock_cols.append(col)

        # Update total rows and columns
        rows = max(rows, row + 1)
        cols = max(cols, col + 1)
            
        key.labels[0] = f"{row},{col}"

        if (not og_key.labels[3] or not og_key.labels[5]):
            continue # Skip non multilayout keys

        # Multi-layout
        ml_ndx, ml_val = extract_ml_val_ndx(og_key)

        ml_count = max(ml_count, ml_ndx + 1) # sets ml_count to highest ml index

        key.labels[7] = og_key.labels[7] # Name of multilayout (Primary multilayout name)
        key.labels[6] = og_key.labels[6] # Name of multi-multilayout (Secondary multilayout name)
        key.labels[8] = f"{ml_ndx},{ml_val}"

        if not ml_ndx in ml_dict.keys():
            ml_dict[ml_ndx] = {}
        ml_dict[ml_ndx][ml_val] = True
        ml_keys.append(key)

    vial_ml = [None] * ml_count # final list used in via json file
    for key in ml_keys:
        ml_ndx, ml_val = map(int, key.labels[8].split(','))
        ml_name = key.labels[7]
        key.labels[7] = '' # Remove primary multilayout

        # Update multilayouts
        if len(ml_dict[ml_ndx]) == 2 and ml_name and not vial_ml[ml_ndx]:
            vial_ml[ml_ndx] = ml_name
        if len(ml_dict[ml_ndx]) > 2 and (ml_name or key.labels[6]): # More than 2 multilayouts
            if not vial_ml[ml_ndx]:
                vial_ml[ml_ndx] = [""] * (len(ml_dict[ml_ndx]) + 1)
            if not vial_ml[ml_ndx][0]: # multilayout name
                vial_ml[ml_ndx][0] = ml_name
            vial_ml[ml_ndx][ml_val+1] = key.labels[6]
    
        key.labels[6] = '' # Remove secondary multilayout

    # Error messages
    for ml_ndx in range(len(vial_ml)):
        if type(vial_ml[ml_ndx]) == list:
            for ml_val in range(len(vial_ml[ml_ndx])):
                if not vial_ml[ml_ndx][ml_val]:
                    if ml_val == 0:
                        raise Exception(f"Multilayout index ({ml_ndx}) is missing a primary multilayout name.")
                    else:
                        raise Exception(f"Multilayout index ({ml_ndx}), value ({ml_val}) is missing a secondary multilayout name.")
        else:
            if not vial_ml[ml_ndx]:
                raise Exception(f"Multilayout index ({ml_ndx}) is missing a multilayout name.")

    # Remove metadata
    vial_kbd.meta = KeyboardMetadata()

    keymap_all = serialize(vial_kbd)
    
    # DEBUG
    # write_file("test-vial.json", json.dumps(keymap_all, ensure_ascii=False, indent=2))

    vial_dict = {
        "name": name,
        "vendorId": vendor_id,
        "productId": product_id,
        "lighting": lighting,
        "matrix": {
            "rows": rows,
            "cols": cols
        },
        "layouts": {
            "labels": vial_ml,
            "keymap": keymap_all
        }
    }

    if not name:
        del vial_dict["name"]
    if not vendor_id:
        del vial_dict["vendorId"]
    if not product_id:
        del vial_dict["productId"]
    if not vial_ml:
        del vial_dict["layouts"]["labels"]

    # Generation of config.h file
    config_h = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#pragma once"
    if vial_uid:
        config_h += f"\n\n{vial_uid}"
    if vial_unlock_rows and vial_unlock_cols:
        u_rows = ', '.join([str(r) for r in vial_unlock_rows])
        u_cols = ', '.join([str(c) for c in vial_unlock_cols])
        config_h += f"\n\n#define VIAL_UNLOCK_COMBO_ROWS {{{u_rows}}}\n#define VIAL_UNLOCK_COMBO_COLS {{{u_cols}}}"
    else:
        config_h += "\n\n/* CONSIDER ADDING AN UNLOCK COMBO. SEE DOCUMENTATION. */\n#define VIAL_INSECURE"
    config_h += "\n"

    return vial_dict, config_h


# CONVERT VIA KLE JSON TO SIMPLIZED KLE

def via_to_kbd(via_json: str) -> Keyboard:
    obj = json.loads(via_json)
    text = json.dumps(obj['layouts']['keymap'])
    if 'labels' in obj['layouts'].keys():
        via_ml = obj['layouts']['labels']
    else:
        via_ml = []

    kbd = deserialize(json.loads(text))
    output_kbd = deepcopy(kbd)
    ml_dict = {}
    ml_length_dict = {}

    # complete ml_dict: keeps track of if ml label has been assigned to a key yet
    for _, obj in enumerate(via_ml):
        if isinstance(obj, list): # list multilayout
            ml_dict[_] = [True] * len(obj)
        if isinstance(obj, str): # boolean multilayout
            ml_dict[_] = True

    # complete ml_length_dict: gets length of all keys in a given multilayout
    for key in output_kbd.keys:
        ml = key.labels[8]
        split_ml = ml.split(",")

        if len(split_ml) == 2:
            ndx = int(split_ml[0]) # need to catch errors here
            val = int(split_ml[1])

            if ml_length_dict.get(ndx):
                ml_length_dict[ndx].append(key.width)
            else:
                ml_length_dict[ndx] = [key.width]

    for key in output_kbd.keys:
        row_col = key.labels[0]
        split_row_col = row_col.split(",")
        
        ml = key.labels[8]
        split_ml = ml.split(",")
        
        # reset labels
        key.labels = [""] * 12

        if len(split_row_col) == 2:
            row = split_row_col[0] # need to catch errors here
            col = split_row_col[1]
            key.labels[9] = row
            key.labels[11] = col
        
        if len(split_ml) == 2:
            ndx = int(split_ml[0]) # need to catch errors here
            val = int(split_ml[1])
            key.labels[3] = str(ndx)
            key.labels[5] = str(val)

            if isinstance(via_ml[ndx], list): # list multilayout
                if ml_dict[ndx][0] and key.width == max(ml_length_dict[ndx]): # primary label
                    key.labels[7] = via_ml[ndx][0] 
                    ml_dict[ndx][0] = False
                if ml_dict[ndx][val+1]: # secondary label
                    key.labels[6] = via_ml[ndx][val+1]
                    ml_dict[ndx][val+1] = False
            else: # boolean multilayout
                if ml_dict[ndx] and key.width == max(ml_length_dict[ndx]):
                    key.labels[7] = via_ml[ndx]
                    ml_dict[ndx] = False
    
    return output_kbd


# GENERATE KEYBOARD.H (LAYOUT MACRO)
# TO-DO:
# - DONE start this
# - DONE extend to generate keymap.c
# - DONE need to clean up these functions by creating new util functions

COL_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijilmnopqrstuvwxyz'
ROW_LETTERS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop'

def kbd_to_layout_macro(kbd: Keyboard) -> str:
    """Generates a LAYOUT macro (for use in a kb.h file).
    Works as per QMK's info.json -> kb.h code."""
    # Removes all multilayout options except max layouts.
    # For parity with info.json.
    kbd = get_layout_all(kbd)

    rows = 0
    cols = 0

    # Calculates total rows and cols
    for key in kbd.keys:
        row, col = extract_row_col(key)

        rows = max(rows, row + 1)
        cols = max(cols, col + 1)

    # This following code is based off qmk's generation.
    layouts_h_lines = []

    layout_name = "LAYOUT"
    col_num = cols
    row_num = rows

    layout_keys = []
    layout_matrix = [['XXX' for i in range(col_num)] for i in range(row_num)]

    for i, key in enumerate(kbd.keys):
        row, col = extract_row_col(key)
        identifier = 'k%s%s' % (ROW_LETTERS[row], COL_LETTERS[col])

        try:
            layout_matrix[row][col] = identifier
            layout_keys.append(identifier)
        except IndexError:
            key_name = key.get('label', identifier)
            raise Exception('Matrix data out of bounds for layout %s at index %s (%s): %s, %s', layout_name, i, key_name, row, col)
            # return False

    layouts_h_lines.append('')
    layouts_h_lines.append('#define %s( \\\n\t%s \\\n) { \\\n' % (layout_name, ', '.join(layout_keys)))

    rows = ', \\\n'.join(['\t{' + ', '.join(row) + '}' for row in layout_matrix])
    rows += ' \\'
    layouts_h_lines.append(rows)
    layouts_h_lines.append('\n}\n')

    layout_h_all = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#pragma once\n\n#include \"quantum.h\"\n\n#define XXX KC_NO\n\n"
    for line in layouts_h_lines:
        layout_h_all += line

    return layout_h_all


# GENERATE KEYMAP

def generate_keycode_conversion_dict(string: str) -> Dict[str, str]:
    """For updating deprecated keycodes that .vil files still uses"""
    conversion_dict = {}
    for line in string.split("\n"):
        split_line = line.split()
        if not split_line:
            continue
        conversion_dict[split_line[0]] = split_line[1]
    return conversion_dict

def keycodes_md_to_keycode_dict(k_md: str) -> Dict[str, str]:
    kc_dict = {}

    lines = k_md.split('\n')
    for line in lines:
        split_line = line.split('|')

        if len(split_line) <= 3:
            continue

        key = split_line[1].strip()
        aliases = split_line[2].strip()

        if not (key.startswith('`') and key.endswith('`')):
            continue

        if not (aliases.startswith('`') and aliases.endswith('`')):
            continue

        key = key.strip('`')

        aliases_split = aliases.split(', ')
        #if aliases_split > 1:
        alias = aliases_split[0].strip('`')

        #print(key, alias)

        kc_dict[key] = alias

    return kc_dict

def layout_str_to_layout_dict(string: str) -> Dict[Any, Any]: # Change to a TypedDict for layout dict
    try:
        obj = json.loads(string)
    except JSONDecodeError as e:
        raise Exception(f'Invalid VIAL/VIA layout file input, {e}')
    return obj


def kbd_to_keymap(kbd: Keyboard,
                  layers: int = 4,
                  lbl_ndx: int = 1,
                  layout_dict: dict = None,
                  keycode_dict: dict = None,
                  conversion_dict: dict = None
                  ) -> str:
    """Generates a keymap.c file"""
    # Check for encoder keys (Both VIA and VIAL)
    encoders_num = 0
    for key in kbd.keys:
        # Toggle encoders if a key with encoders detected
        if key.labels[4].startswith('e'):
            if key.labels[4] == 'e': # VIAL
                enc_val = int(key.labels[9])

            if len(key.labels[4]) > 1 and key.labels[4][1].isnumeric(): # VIA
                enc_val = int(key.labels[4][1])
            encoders_num = max(encoders_num, enc_val+1)

    # Removes all multilayout options except max layouts.
    # For parity with info.json and keymap.c
    kbd = get_layout_all(kbd)

    # Which key label index to read keycodes off
    keycode_label_no = lbl_ndx

    # This following code is based off qmk's generation.
    keymap_lines = []

    layout_name = "LAYOUT"
    max_kc_len = 9

    keymap_keys = [[] for i in range(layers)]
    
    # Calculates total rows and cols
    rows = 0
    cols = 0
    for key in kbd.keys:
        row, col = extract_row_col(key)

        rows = max(rows, row + 1)
        cols = max(cols, col + 1)

    for i, layer_keys in enumerate(keymap_keys):

        # Used to indicate when to newline
        current_y = 0

        for _, key in enumerate(kbd.keys):
            
            if layout_dict: # Check for layout_dict
                if "layout" in layout_dict.keys():  # VIAL layout file
                    vial_layout_dict = layout_dict["layout"]
                    if i+1 > len(vial_layout_dict):
                        kc = 'KC_TRNS'
                    else:
                        try:
                            row, col = extract_row_col(key)
                            kc = vial_layout_dict[i][row][col]
                        except IndexError:
                            raise Exception('Invalid .vil file/layout dictionary provided')

                elif "layers" in layout_dict.keys():  # VIA layout file
                    via_layout_dict = layout_dict["layers"]
                    if i+1 > len(via_layout_dict):
                        kc = 'KC_TRNS'
                    else:
                        try:
                            row, col = extract_row_col(key)
                            kc = via_layout_dict[i][col + row*cols]
                        except IndexError:
                            raise Exception('Invalid VIA layout file provided')

            else: # Default to label
                kc = key.labels[keycode_label_no] # Keycode
                
                if i > 0:
                    kc = 'KC_TRNS'

                elif not kc:
                    def get_key_by_value(dict, search):
                        for key, value in dict.items():
                            if value == search:
                                return key
                        return None
                    
                    lbls = deepcopy(key.labels)
                    lbls[3] = ""
                    lbls[5] = ""
                    lbls[7] = ""
                    lbls[9] = ""
                    lbls[11] = ""

                    kc = get_key_by_value(COMMON_KEYS, lbls)

                    if not kc or i > 0:
                        kc = 'KC_TRNS'

            # Convert (VIALs) deprecated keycodes into updated ones if required
            if conversion_dict:
                if kc in conversion_dict.keys():
                    kc = conversion_dict[kc]

            # Convert lengthened keycodes into shortened aliases if required
            if keycode_dict:
                if kc in keycode_dict.keys():
                    kc = keycode_dict[kc]

            # Newline if the y value changes, just to make things neater
            if key.y != current_y:
                current_y = key.y
                layer_keys.append('\n\t\t')
            layer_keys.append(f'{kc},'.ljust(max_kc_len))

        layer_keys[-1] = layer_keys[-1].strip().rstrip(',')
        #keymap_lines.append(f'#define ')
        #keymap_lines.append(f'\t[{i}] = {layout_name}(\n\t\t{"".join(layer_keys)}\n\t),\n\n')
        keymap_lines.append('\t[{}] = {}(\n\t\t{}\n\t),\n\n'.format(i, layout_name, ''.join(layer_keys)))

    keymap_lines.append('};\n')

    keymap_all = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#include QMK_KEYBOARD_H\n\nconst uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n\n"
    for line in keymap_lines:
        keymap_all += line

    if encoders_num:
        encoder_kc = {}

        if layout_dict:
            if "encoder_layout" in layout_dict.keys():  # VIAL layout file
                for i in range(encoders_num):
                    enc = []
                    for n in range(layers):
                        _enc = layout_dict["encoder_layout"][n][i]
                        for n, kc in enumerate(_enc):
                            # Convert (VIALs) deprecated keycodes into updated ones if required
                            if conversion_dict:
                                if kc in conversion_dict.keys():
                                    _enc[n] = conversion_dict[kc]

                            # Convert lengthened keycodes into shortened aliases if required
                            if keycode_dict:
                                if kc in keycode_dict.keys():
                                    _enc[n] = keycode_dict[kc]
                        enc.append(_enc)
                    encoder_kc[i] = enc

            elif "encoders" in layout_dict.keys():  # VIA layout file
                for i in range(encoders_num):
                    #encoder_kc[i] = layout_dict["encoders"][i]

                    kcs = layout_dict["encoders"][i]
                    for _ in range(len(kcs)):
                        for n, kc in enumerate(kcs[_]):
                            # Convert lengthened keycodes into shortened aliases if required
                            if keycode_dict:
                                if kc in keycode_dict.keys():
                                    kcs[_][n] = keycode_dict[kc]
                    
                    encoder_kc[i] = kcs
                    

        else:
            for i in range(encoders_num):
                encoder_kc[i] = []
                for x in range(layers):
                    encoder_kc[i].append(["KC_TRNS", "KC_TRNS"])

        keymap_all += "\n\n/* `ENCODER_MAP_ENABLE = yes` must be added to the rules.mk at the KEYMAP level. See QMK docs. */\n"
        keymap_all += "/* Remove the following code if you do not enable it in your keymap (e.g. default keymap). */\n"
        keymap_all += "#if defined(ENCODER_MAP_ENABLE)\nconst uint16_t PROGMEM encoder_map[][NUM_ENCODERS][2] = {\n"
        for i in range(layers):
            enc_line = []
            for n in range(encoders_num):
                enc_line.append(f"ENCODER_CCW_CW({encoder_kc[n][i][0]}, {encoder_kc[n][i][1]})")
            cont = ', '.join(enc_line)
            keymap_all += f"\t[{i}] = {{ {cont} }}\n"
        keymap_all += "};\n#endif\n"

    return "\n".join([x.rstrip() for x in keymap_all.split("\n")])


# GENERATE MAIN CONFIG.H

def kbd_to_main_config(kbd: Keyboard, layers: int = 4) -> str:
    config_lines = []

    if layers != 4 and layers > 0 and layers <= 32:
        #config_lines.append('\n')
        config_lines.append(f'#define DYNAMIC_KEYMAP_LAYER_COUNT {layers}')
        config_lines.append('\n')
    else:
        #config_lines.append('\n')
        config_lines.append(f'/* This file is empty and unrequired */')
        config_lines.append('\n')


    config_all = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#pragma once\n\n#include \"config_common.h\"\n\n"
    for line in config_lines:
        config_all += line

    return config_all
