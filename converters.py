from copy import deepcopy
from serial import Keyboard, KeyboardMetadata, serialize, deserialize, sort_keys
from collections import OrderedDict

from util import gen_uid, max_x_y, min_x_y, write_file, replace_chars, extract_matrix_pins
import json
from json import JSONDecodeError


# GENERATE INFO.JSON
# TO-DO:
# - make a way of converting the other way around (INFO.JSON -> KEYBOARD)
# DONE detect bounds of default layout and offset every key by a certain amount
# DONE automatically generate a layout_all based on multilayout with maximum amount of keys
# - create functions to easily set certain multilayouts
# - make more generic converter
# - be able to manually set the layout_all
# - create multiple layouts based on a list of multilayout options

def get_multilayout_keys(kbd: Keyboard) -> bool:
    """Returns a list of multilayout keys"""
    keys = []
    for key in kbd.keys:
        if key.labels[3].isnumeric() and key.labels[5].isnumeric():
            keys.append(key)
    return keys

# TO-DO:
# - Need to update this so that it doesn't miss keys that should be part of 
#   the matrix, but aren't part a certain max multilayout.

def get_layout_all(kbd: Keyboard) -> Keyboard:
    """Returns a Keyboard with all maximum multilayouts chosen.
    For each multilayout, choose the layout option with the most amount of keys.
    For any one multilayout, if all layout options have the same number of keys, 
    the 0th option will be defaulted to. Used for things like the info.json."""
    kbd = deepcopy(kbd)
    ml_keys = get_multilayout_keys(kbd)

    # This list will replace kbd.keys later
    # It is a list with only the keys to be included in the info.json
    qmk_keys = [] 
    # Add non-multilayout keys to the list for now
    for key in [k for k in kbd.keys if k not in ml_keys]:
        qmk_keys.append(key)

    # Generate a dict of all multilayouts
    # E.g. Used to test and figure out the multilayout value with the maximum amount of keys
    ml_dict = {}
    for key in [k for k in kbd.keys if k in ml_keys]:
        ml_ndx = int(key.labels[3])
        ml_val = int(key.labels[5])

        # Create dict with multilayout index if it doesn't exist
        if not ml_dict.get(ml_ndx):
            ml_dict[ml_ndx] = {}

        # Create dict with multilayout value if it doesn't exist
        # Also create list of keys if it doesn't exist
        if not ml_dict[ml_ndx].get(ml_val):
            ml_dict[ml_ndx][ml_val] = []

        # Add key to dict if not in already
        if not key in ml_dict[ml_ndx][ml_val]:
            ml_dict[ml_ndx][ml_val].append(key)


    # Iterate over multilayout keys
    for key in [k for k in kbd.keys if k in ml_keys]:
        # Already know they will have these labels which are integers based on the get_multilayout_keys() function
        ml_ndx = int(key.labels[3])
        ml_val = int(key.labels[5])

        # Get current list of amount of keys in all ml options
        ml_val_length_list = [len(ml_dict[ml_ndx][i]) for i in ml_dict[ml_ndx].keys() if isinstance(i, int)]
        
        max_val_len = max(ml_val_length_list) # Maximum amount of keys over all ml_val options
        current_val_len = len(ml_dict[ml_ndx][ml_val]) # Amount of keys for current ml_val
        
        # Whether or not the current ml_val is the max layout
        current_is_max = max_val_len == current_val_len

        # If all multilayout values/options have the same amount of keys
        all_same_length = len(set(ml_val_length_list)) == 1

        # If the current multilayout value/option is the max one
        if not ml_dict[ml_ndx].get("max"):
            if all_same_length:
                ml_dict[ml_ndx]["max"] = 0 # Use the default/0th option
            elif current_is_max:
                ml_dict[ml_ndx]["max"] = ml_val # Set the max to current ml_val
            else:
                continue
        
        # Skip if not the max layout value/option 
        # (can't use current_is_max because of cases where options have the same amount of keys)
        if not ml_dict[ml_ndx]["max"] == ml_val:
            continue

        # OFFSET MULTILAYOUT KEYS APPROPRIATELY #

        # If the current multilayout value/option isn't default/the 0th layout option 
        # (keys will already be in place)
        if ml_val > 0:
            # Add an offsets dict if it doesn't exist
            if not ml_dict[ml_ndx].get("offsets"):
                ml_dict[ml_ndx]["offsets"] = {}

            # Calculate the appropriate offset for this ml_val if it hasn't been calculated yet
            if not ml_dict[ml_ndx]["offsets"].get(ml_val):
                # Calculate and set x and y offsets
                xmin, ymin = min_x_y(ml_dict[ml_ndx][0])
                x, y = min_x_y(ml_dict[ml_ndx][ml_val])

                ml_x_offset = xmin - x
                ml_y_offset = ymin - y

                ml_dict[ml_ndx]["offsets"][ml_val] = (ml_x_offset, ml_y_offset)
            else:
                # Get the offset from ml_dict
                ml_x_offset, ml_y_offset = ml_dict[ml_ndx]["offsets"][ml_val]
            
            # Offset the x and y values
            key.x += ml_x_offset
            key.y += ml_y_offset

            # For rotated keys only
            if key.rotation_angle:
                key.rotation_x -= ml_x_offset
                key.rotation_y -= ml_y_offset

        # Add the key to the final list
        qmk_keys.append(key)

    # Offset all the remaining keys (align against the top left)
    x_offset, y_offset = min_x_y(qmk_keys)
    for key in qmk_keys:
        key.x -= x_offset
        key.y -= y_offset

    # Override kbd.keys with the keys only to be included in the info.json
    kbd.keys = qmk_keys
    sort_keys(kbd.keys) # sort keys (some multilayout keys may not be in the right order)

    # DEBUG: To view what the layout_all will look like (as a KLE)
    import json
    from util import write_file
    test_path = 'test.json'
    write_file(test_path, json.dumps(serialize(kbd), ensure_ascii=False, indent=2))

    return kbd

def kbd_to_qmk_info(kbd: Keyboard, name=None, maintainer=None, url=None, vid=None, pid=None, ver=None, mcu=None, bootloader=None, board=None, pin_dict=None, diode_dir="COL2ROW") -> dict:
    """Converts a Keyboard into a QMK info.json (dict)"""
    # Removes all multilayout options except max layouts.
    kbd = get_layout_all(kbd)

    rows = 0
    cols = 0

    for key in kbd.keys:
        row = int(key.labels[9]) # TO-DO: add errorcase
        col = int(key.labels[11]) # TO-DO: add errorcase

        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1

    # The final list that will actually be used in the info.json
    qmk_layout_all = []

    # Convert keyboard
    for key in kbd.keys:
        # Ignore ghost keys (e.g. blockers)
        if key.decal: 
            continue
        
        # Initialize a key (dict)
        qmk_key = OrderedDict(
            label = "",
            x = key.x,
            y = key.y,
        )

        if key.width != 1:
            qmk_key['w'] = key.width
        if key.height != 1:
            qmk_key['h'] = key.height

        if key.labels[9].isnumeric() and key.labels[11].isnumeric():
            row = key.labels[9]
            col = key.labels[11]
            qmk_key['matrix'] = [int(row), int(col)]

        if key.labels[0]:
            qmk_key['label'] = key.labels[0]
        else:
            del (qmk_key['label'])

        qmk_layout_all.append(qmk_key)

    if not name:
        if kbd.meta.name:
            name = kbd.meta.name
        else:
            name = 'Keyboard'

    if not maintainer:
        maintainer = 'qmk'

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
        'layouts': {
            'LAYOUT': {
                'layout': qmk_layout_all
            }
        }
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

    return keyboard


# CONVERT SIMPLIZED KLE TO VIA JSON
# TO-DO
# - detect if keyboard can be converted first
# - make a way of converting the other way around (VIA KLE/JSON -> SIMPLIFIED KLE)
# - add way to input the index for which label indices to use for rows/cols/multilayout etc
# - change this function to have a more similar structure to the qmk info converter (for multilayouts)

def kbd_to_vial(kbd: Keyboard, vial_uid:str=None, vendor_id:str=None, product_id:str=None, lighting:str=None, name:str=None):
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
        key.color = "#cccccc" # Set to default colour to remove clutter from the KLE
        # key.color = og_key.color
        key.labels = [None] * 12 # Empty labels
        key.textSize = [None] * 12 # Reset text size

        if og_key.labels[4] == "e": # encoder; VIAL ONLY
            key.labels[4] = og_key.labels[4]

        # Matrix coords
        row_lbl = og_key.labels[9]
        col_lbl = og_key.labels[11]

        # Error keys without row and/or column labels
        # # if not (row_lbl and col_lbl): # this line is needed in the case that labels are None (no longer required since I changed the default label values to empty strings instead)
        # #     continue
        if not (row_lbl.isnumeric() and col_lbl.isnumeric()):
            if row_lbl.isnumeric():
                raise Exception(f"Key at ({key.x},{key.y}) has row value ({row_lbl}), but is missing a valid column label.")
            elif col_lbl.isnumeric():
                raise Exception(f"Key at ({key.x},{key.y}) has column value ({col_lbl}), but is missing a valid row label.")
            else:
                raise Exception(f"Key at ({key.x},{key.y}) is missing a valid row and/or column label.")
            #continue

        row = int(og_key.labels[9])
        col = int(og_key.labels[11])

        # Add if unlock key
        if og_key.labels[2] == "u": 
            vial_unlock_rows.append(row)
            vial_unlock_cols.append(col)

        # Update total rows and columns
        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1
            
        key.labels[0] = f"{row},{col}"

        # Multi-layout
        ml_ndx_lbl = og_key.labels[3] # Multilayout index
        ml_val_lbl = og_key.labels[5] # Multilayout value

        # if not (ml_ndx_lbl and ml_val_lbl):
        #     continue
        if not (ml_ndx_lbl.isnumeric() and ml_val_lbl.isnumeric()):
            if ml_ndx_lbl.isnumeric():
                raise Exception(f"Key at ({key.x},{key.y}) has a multilayout index ({ml_ndx_lbl}), but not a mulitlayout value.")
            elif ml_val_lbl.isnumeric():
                raise Exception(f"Key at ({key.x},{key.y}) has a multilayout value ({ml_val_lbl}), but not a multilayout index.")
            else:
                continue

        ml_ndx = int(og_key.labels[3])
        ml_val = int(og_key.labels[5])

        if ml_ndx + 1 > ml_count:
            ml_count = ml_ndx + 1 # sets ml_count to highest ml index

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


# CONVERT VIA JSON TO SIMPLIZED KLE

def via_to_kbd(via_json: str) -> Keyboard:
    pass


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
        row = int(key.labels[9])
        col = int(key.labels[11])

        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1

    # This following code is based off qmk's generation.
    layouts_h_lines = []

    layout_name = "LAYOUT"
    col_num = cols
    row_num = rows

    layout_keys = []
    layout_matrix = [['XXX' for i in range(col_num)] for i in range(row_num)]

    for i, key in enumerate(kbd.keys):
        row = int(key.labels[9])
        col = int(key.labels[11])
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

def generate_keycode_conversion_dict(string:str) -> str:
    """For updating deprecated keycodes that .vil files still uses"""
    conversion_dict = {}
    for line in string.split("\n"):
        split_line = line.split()
        if not split_line:
            continue
        conversion_dict[split_line[0]] = split_line[1]
    return conversion_dict

def keycodes_md_to_keycode_dict(k_md:str) -> dict:
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

def layout_str_to_layout_dict(string:str) -> dict:
    try:
        obj = json.loads(string)
    except JSONDecodeError as e:
        raise Exception(f'Invalid VIAL/VIA layout file input, {e}')
    return obj


def kbd_to_keymap(kbd: Keyboard, layers:int=4, lbl_ndx:int=1, layout_dict:dict=None, keycode_dict:dict=None, conversion_dict:dict=None) -> str:
    """Generates a keymap.c file"""
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
        row = int(key.labels[9])
        col = int(key.labels[11])

        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1

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
                            row = int(key.labels[9])
                            col = int(key.labels[11])
                            kc = vial_layout_dict[i][row][col]
                        except IndexError:
                            raise Exception('Invalid .vil file/layout dictionary provided')

                elif "layers" in layout_dict.keys():  # VIA layout file
                    via_layout_dict = layout_dict["layers"]
                    if i+1 > len(via_layout_dict):
                        kc = 'KC_TRNS'
                    else:
                        try:
                            row = int(key.labels[9])
                            col = int(key.labels[11])
                            kc = via_layout_dict[i][col + row*cols]
                        except IndexError:
                            raise Exception('Invalid VIA layout file provided')

            else: # Default to label
                if i == 0: # First layer
                    kc = key.labels[keycode_label_no] # Keycode
                    if not kc:
                        kc = 'KC_TRNS'
                else:
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

    return "\n".join([x.rstrip() for x in keymap_all.split("\n")])


# GENERATE MAIN CONFIG.H

def kbd_to_main_config(kbd: Keyboard, layers:int=4) -> str:
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
