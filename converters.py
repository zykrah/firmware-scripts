from copy import deepcopy
from serialize import serialize, sort_keys
from deserialize import deserialize
from collections import OrderedDict

from util import Keyboard, KeyboardMetadata, gen_uid, min_x_y, write_file
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
        
def kbd_to_qmk_info(kbd: Keyboard) -> dict:
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

    keyboard = {
        'keyboard_name': kbd.meta.name,
        'url': '',
        'maintainer': 'qmk',
        'layouts': {
            'LAYOUT_all': {
                'layout': qmk_layout_all
            }
        }
    }

    return keyboard

# CONVERT SIMPLIZED KLE TO VIA JSON
# TO-DO
# - detect if keyboard can be converted first
# - make a way of converting the other way around (VIA KLE/JSON -> SIMPLIZED KLE)
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
            raise Exception # need a name for VIA

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
        raise Exception # there is multilayout option which is missing at least one name/tag

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
        key.color = "#cccccc"
        key.labels = [None] * 12 # Empty labels

        if og_key.labels[4] == "e": # encoder; VIAL ONLY
            key.labels[4] = og_key.labels[4]

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
    
    if None in vial_ml:
        raise Exception # there is multilayout option which is missing at least one name/tag

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
        config_h += "\n\n#define VIAL_INSECURE"
    config_h += "\n"

    return vial_dict, config_h


# GENERATE KEYBOARD.H (LAYOUT MACRO)
# TO-DO:
# - start this
# - extend to generate keymap.c
