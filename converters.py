from copy import deepcopy
from serialize import serialize
from deserialize import deserialize
from collections import OrderedDict

from util import Key, Keyboard, KeyboardMetadata, gen_uid


# GENERATE INFO.JSON
# TO-DO:
# - make a way of converting the other way around (INFO.JSON -> KEYBOARD)
# DONE detect bounds of default layout and offset every key by a certain amount
# - automatically generate a layout_all based on multilayout with maximum amount of keys
# - create multiple layouts based on a list of multilayout options

# class MultilayoutKey(Key):
#     def __init__(self, key, ml_label_index=8, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         for k in key.__dict__.keys():
#             setattr(self, k, getattr(key, k))
#         # self.__dict__.update(key.__dict__)
#         self.ml_index, self.ml_val = map(int, key.labels[ml_label_index].split(','))

def check_multilayout_keys(kbd: Keyboard) -> bool:
    keys = []
    for key in kbd.keys:
        if key.labels[3].isnumeric() and key.labels[5].isnumeric():
            keys.append(key)
    return keys

def max_x_y(keys: list) -> float:
    max_x: float = -1
    max_y: float = -1

    for key in keys:
        if key.x > max_x:
            max_x = key.x
        if key.y > max_y:
            max_y = key.y

    return max_x, max_y

def min_x_y(keys: list) -> float:
    min_x, min_y = max_x_y(keys)

    for key in keys:
        if key.x < min_x:
            min_x = key.x
        if key.y < min_y:
            min_y = key.y

    return min_x, min_y
        
def kbd_to_qmk_info(kbd: Keyboard) -> dict:
    ml_label_index = 8
    ml_keys = check_multilayout_keys(kbd)
    # default_keys = [k for k in kbd.keys if k not in ml_keys or int(k.labels[ml_label_index].split(',')[1]) == 0]
    default_keys = []
    ml_dict = {}

    for k in kbd.keys:
        if k not in ml_keys:
            default_keys.append(k)
        else:
            # ml_index, ml_val = map(int, k.labels[ml_label_index].split(','))
            ml_index = int(k.labels[3])
            ml_val = int(k.labels[5])
            # if ml_val == 0:
            #     default_keys.append(k)

            if not ml_ndx in ml_dict.keys():
                ml_dict[ml_ndx] = {}
            if not ml_val in ml_dict[ml_ndx].keys():
                ml_dict[ml_ndx][ml_val] = []
            if not [int(key.labels[9]), int(key.labels[11])] in ml_dict[ml_ndx][ml_val]:
                ml_dict[ml_ndx][ml_val].append([int(key.labels[9]), int(key.labels[11])])

            ml_keys.append(key)

    # ml_list = []
    # for k in kbd.keys:
    #     if k in ml_keys:
    #         ml_index, ml_val = map(int, k.labels[ml_label_index].split(','))
    #         ml_list.append([k, ml_index, ml_val])

    # max_layout_keys = []
    # for k in kbd.keys:
    #     if k not in ml_keys:
    #         max_layout_keys.append(k)
    # for ml in ml_list:
    #     ml_index, ml_val = map(int, ml[0].labels[ml_label_index].split(','))
    #     # if ml_val == 0:
    #     #     default_keys.append(k)

    for key in ml_keys:
        ml_index = int(k.labels[3])
        ml_val = int(k.labels[5])
        ml_dict[ml_ndx][ml_val]
        if max([len(i) for i in ml_dict[ml_ndx]) == len(ml_dict[ml_ndx][ml_val]):
            
            default_keys.add(key)

    qmk_layout = []
    x_offset, y_offset = min_x_y(default_keys)

    for key in kbd.keys:
        if key.decal:
            continue

        qmk_key = OrderedDict(
            label = "",
            x = key.x - x_offset,
            y = key.y - y_offset,
        )

        if key.width != 1:
            qmk_key['w'] = key.width
        if key.height != 1:
            qmk_key['h'] = key.height

        if key.labels[9] and key.labels[11]:
            if key.labels[9].isnumeric() and key.labels[11].isnumeric():

                if not key in default_keys:
                    continue

            row = key.labels[9]
            col = key.labels[11]
            qmk_key['matrix'] = [int(row), int(col)]

        # if key.labels[0]:
        #     if re.search(r"\-{0,1}\d*,\-{0,1}", key.labels[0]):
        #         row, col = map(int, key.labels[0].split(','))
        #         qmk_key['matrix'] = [int(row), int(col)]
        if key.labels[0]:
            qmk_key['label'] = key.labels[0]
        else:
            del (qmk_key['label'])

        qmk_layout.append(qmk_key)

    keyboard = {
        'keyboard_name': kbd.meta.name,
        'url': '',
        'maintainer': 'qmk',
        'layouts': {
            'LAYOUT_all': {
                'layout': qmk_layout
            }
        }
    }

    return keyboard

# CONVERT KLE (with simple matrix coords) TO PROPER VIA KLE
# TO-DO
# - detect if keyboard can be converted
# - make a way of converting the other way around (VIA KLE -> KEYBOARD)
# - add way to input the index for which label indices to use for rows/cols/multilayout etc

def kbd_to_via(kbd: Keyboard, product_id:str=None, vendor_id:str=None, lighting:str=None, name:str=None) -> dict:
    if not product_id:
        product_id = '0x0000'
    if not vendor_id:
        vendor_id = '0x0000'
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

        # if not (ml_ndx_lbl and ml_val_lbl):
        #     continue
        if not (ml_ndx_lbl.isnumeric() and ml_val_lbl.isnumeric()):
            continue

        ml_ndx = int(og_key.labels[3])
        ml_val = int(og_key.labels[5])

        if ml_ndx + 1 > ml_count:
            ml_count = ml_ndx + 1

        key.labels[7] = og_key.labels[7] # Name of multilayout
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
        if len(ml_dict[ml_ndx]) > 2 and ml_name:
            if not via_ml[ml_ndx]:
                via_ml[ml_ndx] = [""] * len(ml_dict[ml_ndx])
            via_ml[ml_ndx][ml_val] = ml_name 
    
    if None in via_ml:
        raise Exception # there is multilayout option which is missing at least one name/tag

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

def kbd_to_vial(kbd: Keyboard, vial_uid:str=None, product_id:str=None, vendor_id:str=None, lighting:str=None, name:str=None) -> dict:
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
        if len(ml_dict[ml_ndx]) > 2 and ml_name:
            if not vial_ml[ml_ndx]:
                vial_ml[ml_ndx] = [""] * len(ml_dict[ml_ndx])
            vial_ml[ml_ndx][ml_val] = ml_name 
    
    if None in vial_ml:
        raise Exception # there is multilayout option which is missing at least one name/tag

    keymap_all = serialize(vial_kbd)

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

    config_h = "/* SPDX-License-Identifier: GPL-2.0-or-later */\n\n#pragma once"
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
