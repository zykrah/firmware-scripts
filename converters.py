from copy import deepcopy
from serialize import serialize, sort_keys
from deserialize import deserialize
from collections import OrderedDict

from util import Keyboard, KeyboardMetadata, gen_uid, max_x_y, min_x_y, write_file, replace_chars
import json


# GENERATE INFO.JSON
# TO-DO:
# - make a way of converting the other way around (INFO.JSON -> KEYBOARD)
# DONE detect bounds of default layout and offset every key by a certain amount
# DONE automatically generate a layout_all based on multilayout with maximum amount of keys
# - create functions to easily set certain multilayouts
# - make more generic converter
# - be able to manually set the layout_all
# - create multiple layouts based on a list of multilayout options

def check_multilayout_keys(kbd: Keyboard) -> bool:
    keys = []
    for key in kbd.keys:
        if key.labels[3].isnumeric() and key.labels[5].isnumeric():
            keys.append(key)
    return keys
        
def kbd_to_qmk_info(kbd: Keyboard, name=None, maintainer=None, url=None, vid=None, pid=None, ver=None, mcu=None, bootloader=None) -> dict:
    kbd = deepcopy(kbd)
    ml_keys = check_multilayout_keys(kbd)

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
        if not ml_ndx in ml_dict.keys():
            ml_dict[ml_ndx] = {}

        # Create dict with multilayout value if it doesn't exist
        # Also create list of keys if it doesn't exist
        if not ml_val in ml_dict[ml_ndx].keys():
            ml_dict[ml_ndx][ml_val] = []

        # Add key to dict if not in already
        if not key in ml_dict[ml_ndx][ml_val]:
            ml_dict[ml_ndx][ml_val].append(key)


    # Iterate over multilayout keys
    for key in [k for k in kbd.keys if k in ml_keys]:
        ml_ndx = int(key.labels[3])
        ml_val = int(key.labels[5])

        # list of all amount of keys over all val options
        ml_val_length_list = [len(ml_dict[ml_ndx][i]) for i in ml_dict[ml_ndx].keys() if isinstance(i, int)]
        max_val_len = max(ml_val_length_list) # maximum amount of keys over all val options
        current_val_len = len(ml_dict[ml_ndx][ml_val]) # amount of keys in current val
        current_is_max = max_val_len == current_val_len

        # If all multilayout values/options have the same amount of keys
        all_same_length = len(set(ml_val_length_list)) == 1

        # If the current multilayout value/option is the max one
        if not "max" in ml_dict[ml_ndx].keys():
            if all_same_length:
                ml_dict[ml_ndx]["max"] = 0 # Use the default
            elif current_is_max:
                ml_dict[ml_ndx]["max"] = ml_val
            else:
                continue
        
        # Skip if not the max layout value/option 
        # (can't use current_is_max because of cases where options have the same amount of keys)
        if not ml_dict[ml_ndx]["max"] == ml_val:
            continue

        # If the current multilayout value/option isn't default,
        if ml_val > 0:
            # Check if there is an offsets dict
            if not "offsets" in ml_dict[ml_ndx].keys():
                ml_dict[ml_ndx]["offsets"] = {}

            # Check if the offset for this multilayout value has been calculated yet.
            if not ml_val in ml_dict[ml_ndx]["offsets"].keys():
                # If not, calculate and set the offset
                xmin, ymin = min_x_y(ml_dict[ml_ndx][0])
                x, y = min_x_y(ml_dict[ml_ndx][ml_val])

                ml_x_offset = xmin - x
                ml_y_offset = ymin - y

                ml_dict[ml_ndx]["offsets"][ml_val] = (ml_x_offset, ml_y_offset)
            else:
                # If so, just get the offset from ml_dict
                ml_x_offset, ml_y_offset = ml_dict[ml_ndx]["offsets"][ml_val]
            
            # Offset the x and y values
            key.x += ml_x_offset
            key.y += ml_y_offset

            if key.rotation_angle:
                key.rotation_x -= x_offset
                key.rotation_y -= y_offset

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


    # The final list that will actually be used in the info.json
    qmk_layout_all = []

    # Finally convert keyboard  into 
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
            'LAYOUT_all': {
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

    if url:
        keyboard["url"] = url

    if usb:
        keyboard["usb"] = usb

    return keyboard

# CONVERT SIMPLIZED KLE TO VIA JSON
# TO-DO
# - detect if keyboard can be converted first
# - make a way of converting the other way around (VIA KLE/JSON -> SIMPLIFIED KLE)
# - add way to input the index for which label indices to use for rows/cols/multilayout etc
# - change this function to have a more similar structure to the qmk info converter (for multilayouts)

def kbd_to_via(kbd: Keyboard, vendor_id:str=None, product_id:str=None, lighting:str=None, name:str=None) -> dict:
    if not vendor_id:
        vendor_id = '0xFEED'
    if not product_id:
        product_id = '0x0000'
    if not lighting:
        lighting = 'none'
    if not name:
        name = kbd.meta.name
        if name is None:
            raise Exception("Name required for VIA jsons") # need a name for VIA

    rows = 0
    cols = 0
    ml_keys = [] # list of multilayout keys
    ml_dict = {}
    ml_count = 0 # amount of multilayouts

    via_kbd = deepcopy(kbd)
    
    for key in via_kbd.keys:
        og_key = deepcopy(key)
        key.color = "#cccccc"
        key.labels = [None] * 12 # Empty labels

        if og_key.labels[4] == "e": # encoder; VIAL ONLY
            continue

        row_lbl = og_key.labels[9]
        col_lbl = og_key.labels[11]

        # Matrix coords
        # Skip key without row and column labels
        # # if not (row_lbl and col_lbl): # this line is needed in the case that labels are None (changed to default to empty string when empty instead)
        # #     continue
        if not (row_lbl.isnumeric() and col_lbl.isnumeric()):
            continue

        row = int(og_key.labels[9])
        col = int(og_key.labels[11])

        # Update total rows and columns
        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1
            
        key.labels[0] = f"{row},{col}"

        # Multi-layout
        ml_ndx_lbl = og_key.labels[3] # Multilayout index
        ml_val_lbl = og_key.labels[5] # Multilayout value

        if not (ml_ndx_lbl.isnumeric() and ml_val_lbl.isnumeric()):
            continue

        ml_ndx = int(og_key.labels[3])
        ml_val = int(og_key.labels[5])

        if ml_ndx + 1 > ml_count:
            ml_count = ml_ndx + 1

        key.labels[7] = og_key.labels[7] # Name of multilayout
        key.labels[6] = og_key.labels[6] # Name of multi-multilayout
        key.labels[8] = f"{ml_ndx},{ml_val}"

        if not ml_ndx in ml_dict.keys():
            ml_dict[ml_ndx] = {}
        ml_dict[ml_ndx][ml_val] = True
        ml_keys.append(key)

    via_ml = [None] * ml_count # final list used in via json file
    for key in ml_keys:
        ml_ndx, ml_val = map(int, key.labels[8].split(','))
        ml_name = key.labels[7]
        key.labels[7] = ''

        # Update multilayouts
        if len(ml_dict[ml_ndx]) == 2 and ml_name and not via_ml[ml_ndx]:
            via_ml[ml_ndx] = ml_name
        if len(ml_dict[ml_ndx]) > 2 and (ml_name or key.labels[6]): # More than 2 multilayouts
            if not via_ml[ml_ndx]:
                via_ml[ml_ndx] = [""] * (len(ml_dict[ml_ndx]) + 1)
            if not via_ml[ml_ndx][0]: # multilayout name
                via_ml[ml_ndx][0] = ml_name
            via_ml[ml_ndx][ml_val+1] = key.labels[6]

    if None in via_ml:
        raise Exception("There is at least one multilayout option that is missing a primary/seconday multilayout label.") # there is multilayout option which is missing at least one name/tag

    # Remove metadata
    via_kbd.meta = KeyboardMetadata()

    keymap_all = serialize(via_kbd)

    via_dict = {
        "name": name,
        "vendorId": vendor_id,
        "productId": product_id,
        "lighting": lighting,
        "matrix": {
            "rows": rows,
            "cols": cols
        },
        "layouts": {
            "labels": via_ml,
            "keymap": keymap_all
        }
    }

    return via_dict

def kbd_to_vial(kbd: Keyboard, vial_uid:str=None, vendor_id:str=None, product_id:str=None, lighting:str=None, name:str=None) -> dict:
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
        key.labels[7] = ''

        # Update multilayouts
        if len(ml_dict[ml_ndx]) == 2 and ml_name and not vial_ml[ml_ndx]:
            vial_ml[ml_ndx] = ml_name
        if len(ml_dict[ml_ndx]) > 2 and (ml_name or key.labels[6]): # More than 2 multilayouts
            if not vial_ml[ml_ndx]:
                vial_ml[ml_ndx] = [""] * (len(ml_dict[ml_ndx]) + 1)
            if not vial_ml[ml_ndx][0]: # multilayout name
                vial_ml[ml_ndx][0] = ml_name
            vial_ml[ml_ndx][ml_val+1] = key.labels[6]
    
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

    # if None in vial_ml:
    #     raise Exception("There is at least one multilayout option that is missing a primary/seconday multilayout label.") # there is multilayout option which is missing at least one name/tag

    # Remove metadata
    vial_kbd.meta = KeyboardMetadata()

    keymap_all = serialize(vial_kbd)
    
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
# - need to clean up these functions by creating new util functions

COL_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijilmnopqrstuvwxyz'
ROW_LETTERS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop'

def kbd_to_layout_macro(kbd: Keyboard) -> str:
    kbd = deepcopy(kbd)
    ml_keys = check_multilayout_keys(kbd)

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
        if not ml_ndx in ml_dict.keys():
            ml_dict[ml_ndx] = {}

        # Create dict with multilayout value if it doesn't exist
        # Also create list of keys if it doesn't exist
        if not ml_val in ml_dict[ml_ndx].keys():
            ml_dict[ml_ndx][ml_val] = []

        # Add key to dict if not in already
        if not key in ml_dict[ml_ndx][ml_val]:
            ml_dict[ml_ndx][ml_val].append(key)

    # Iterate over multilayout keys
    for key in [k for k in kbd.keys if k in ml_keys]:
        ml_ndx = int(key.labels[3])
        ml_val = int(key.labels[5])

        # list of all amount of keys over all val options
        ml_val_length_list = [len(ml_dict[ml_ndx][i]) for i in ml_dict[ml_ndx].keys() if isinstance(i, int)]
        max_val_len = max(ml_val_length_list) # maximum amount of keys over all val options
        current_val_len = len(ml_dict[ml_ndx][ml_val]) # amount of keys in current val
        current_is_max = max_val_len == current_val_len

        # If all multilayout values/options have the same amount of keys
        all_same_length = len(set(ml_val_length_list)) == 1

        # If the current multilayout value/option is the max one
        if not "max" in ml_dict[ml_ndx].keys():
            if all_same_length:
                ml_dict[ml_ndx]["max"] = 0 # Use the default
            elif current_is_max:
                ml_dict[ml_ndx]["max"] = ml_val
            else:
                continue
        
        # Skip if not the max layout value/option 
        # (can't use current_is_max because of cases where options have the same amount of keys)
        if not ml_dict[ml_ndx]["max"] == ml_val:
            continue

        # If the current multilayout value/option isn't default,
        if ml_val > 0:
            # Check if there is an offsets dict
            if not "offsets" in ml_dict[ml_ndx].keys():
                ml_dict[ml_ndx]["offsets"] = {}

            # Check if the offset for this multilayout value has been calculated yet.
            if not ml_val in ml_dict[ml_ndx]["offsets"].keys():
                # If not, calculate and set the offset
                xmin, ymin = min_x_y(ml_dict[ml_ndx][0])
                x, y = min_x_y(ml_dict[ml_ndx][ml_val])

                ml_x_offset = xmin - x
                ml_y_offset = ymin - y

                ml_dict[ml_ndx]["offsets"][ml_val] = (ml_x_offset, ml_y_offset)
            else:
                # If so, just get the offset from ml_dict
                ml_x_offset, ml_y_offset = ml_dict[ml_ndx]["offsets"][ml_val]
            
            # Offset the x and y values
            key.x += ml_x_offset
            key.y += ml_y_offset

            if key.rotation_angle:
                key.rotation_x -= x_offset
                key.rotation_y -= y_offset

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

    # # DEBUG: To view what the layout_all will look like (as a KLE)
    # import json
    # from util import write_file
    # test_path = 'test.json'
    # write_file(test_path, json.dumps(serialize(kbd), ensure_ascii=False, indent=2))

    rows = 0
    cols = 0

    for key in kbd.keys:
        row = int(key.labels[9])
        col = int(key.labels[11])

        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1

    # This following code is based off qmk's generation.
    layouts_h_lines = []

    layout_name = "LAYOUT_all"
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

def kbd_to_keymap(kbd: Keyboard, layers:int=4) -> str:
    keycode_label_no = 1

    kbd = deepcopy(kbd)
    ml_keys = check_multilayout_keys(kbd)

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
        if not ml_ndx in ml_dict.keys():
            ml_dict[ml_ndx] = {}

        # Create dict with multilayout value if it doesn't exist
        # Also create list of keys if it doesn't exist
        if not ml_val in ml_dict[ml_ndx].keys():
            ml_dict[ml_ndx][ml_val] = []

        # Add key to dict if not in already
        if not key in ml_dict[ml_ndx][ml_val]:
            ml_dict[ml_ndx][ml_val].append(key)

    # Iterate over multilayout keys
    for key in [k for k in kbd.keys if k in ml_keys]:
        ml_ndx = int(key.labels[3])
        ml_val = int(key.labels[5])

        # list of all amount of keys over all val options
        ml_val_length_list = [len(ml_dict[ml_ndx][i]) for i in ml_dict[ml_ndx].keys() if isinstance(i, int)]
        max_val_len = max(ml_val_length_list) # maximum amount of keys over all val options
        current_val_len = len(ml_dict[ml_ndx][ml_val]) # amount of keys in current val
        current_is_max = max_val_len == current_val_len

        # If all multilayout values/options have the same amount of keys
        all_same_length = len(set(ml_val_length_list)) == 1

        # If the current multilayout value/option is the max one
        if not "max" in ml_dict[ml_ndx].keys():
            if all_same_length:
                ml_dict[ml_ndx]["max"] = 0 # Use the default
            elif current_is_max:
                ml_dict[ml_ndx]["max"] = ml_val
            else:
                continue
        
        # Skip if not the max layout value/option 
        # (can't use current_is_max because of cases where options have the same amount of keys)
        if not ml_dict[ml_ndx]["max"] == ml_val:
            continue

        # If the current multilayout value/option isn't default,
        if ml_val > 0:
            # Check if there is an offsets dict
            if not "offsets" in ml_dict[ml_ndx].keys():
                ml_dict[ml_ndx]["offsets"] = {}

            # Check if the offset for this multilayout value has been calculated yet.
            if not ml_val in ml_dict[ml_ndx]["offsets"].keys():
                # If not, calculate and set the offset
                xmin, ymin = min_x_y(ml_dict[ml_ndx][0])
                x, y = min_x_y(ml_dict[ml_ndx][ml_val])

                ml_x_offset = xmin - x
                ml_y_offset = ymin - y

                ml_dict[ml_ndx]["offsets"][ml_val] = (ml_x_offset, ml_y_offset)
            else:
                # If so, just get the offset from ml_dict
                ml_x_offset, ml_y_offset = ml_dict[ml_ndx]["offsets"][ml_val]
            
            # Offset the x and y values
            key.x += ml_x_offset
            key.y += ml_y_offset

            if key.rotation_angle:
                key.rotation_x -= x_offset
                key.rotation_y -= y_offset

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

    # # DEBUG: To view what the layout_all will look like (as a KLE)
    # import json
    # from util import write_file
    # test_path = 'test.json'
    # write_file(test_path, json.dumps(serialize(kbd), ensure_ascii=False, indent=2))

    # This following code is based off qmk's generation.
    keymap_lines = []

    layout_name = "LAYOUT_all"

    keymap_keys = [[] for i in range(layers)]
    
    for i, layer_keys in enumerate(keymap_keys):

        current_y = 0
        
        for key in kbd.keys:
            if i == 0: # First layer
                kc = key.labels[keycode_label_no] # Keycode
                if not kc:
                    kc = 'KC_TRNS'
            else:
                kc = 'KC_TRNS'

            if key.y != current_y:
                current_y = key.y
                layer_keys.append(f'\n\t\t{kc}')
            else:        
                layer_keys.append(kc)

        #keymap_lines.append(f'#define ')
        keymap_lines.append('\t[%s] = %s(\n\t\t%s\n\t),\n\n' % (i, layout_name, ', '.join(layer_keys)))

    keymap_lines.append('};\n')

    keymap_all = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#include QMK_KEYBOARD_H\n\nconst uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n\n"
    for line in keymap_lines:
        keymap_all += line

    return keymap_all

# GENERATE MAIN CONFIG.H

def kbd_to_main_config(kbd: Keyboard) -> str:
    rows = 0
    cols = 0

    for key in kbd.keys:
        row = int(key.labels[9]) # TO-DO: add errorcase
        col = int(key.labels[11]) # TO-DO: add errorcase

        if row + 1 > rows:
            rows = row + 1
        if col + 1 > cols:
            cols = col + 1
        
    config_lines = []

    config_lines.append('/* key matrix size */')
    config_lines.append('\n')
    config_lines.append('#define MATRIX_ROWS %s' % (rows))
    config_lines.append('\n')
    config_lines.append('#define MATRIX_COLS %s' % (cols))
    config_lines.append('\n\n')

    config_lines.append('#define MATRIX_ROW_PINS {%s}' % (','.join(['X'] * rows)) )
    config_lines.append('\n')
    config_lines.append('#define MATRIX_COL_PINS {%s}' % (','.join(['X'] * cols)) )
    config_lines.append('\n\n')

    config_lines.append('/* COL2ROW or ROW2COL */')
    config_lines.append('\n')
    config_lines.append('#define DIODE_DIRECTION %s' % ('COL2ROW'))
    config_lines.append('\n')

    config_all = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#pragma once\n\n#include \"config_common.h\"\n\n"
    for line in config_lines:
        config_all += line

    return config_all