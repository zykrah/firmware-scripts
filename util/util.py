from functools import cmp_to_key
from dataclasses import dataclass, field as dcf
from typing import Tuple, Optional, Dict, List, Callable
import secrets
import re

from util.serial import Key

MCU_PRESETS = ['None', 'RP2040', '32U4', 'STM32']

MCU_DICT = {
    'None' : {
        'mcu' : None,
        'board': None,
        'bootloader': None,
        'output_pin_pref': None,
        'schem_pin_pref': None
    },
    'RP2040': {
        'mcu' : 'RP2040',
        'board': None,
        'bootloader': 'rp2040',
        'output_pin_pref': 'GP',
        'schem_pin_pref': 'GPIO'
    },
    '32U4': {
        'mcu' : 'atmega32u4',
        'board': None,
        'bootloader': 'atmel-dfu',
        'output_pin_pref': '',
        'schem_pin_pref': 'P'
    },
    'STM32': {
        'mcu' : 'STM32FXXX',
        'board': 'GENERIC_STM_FXXX',
        'bootloader': 'stm32-dfu',
        'output_pin_pref': '',
        'schem_pin_pref': 'P'
    }
}

# Unused currently
def replace_chars(str:str, start:int, stop:int, new):
    """Replace characters in a string based on the start and stop character indices.
    """
    return str.replace(str[start:stop], new)

# Gets the bottom right coordinate of bounding box of a cluster of keys
def max_x_y(keys: List[Key]) -> Tuple[float, float]:
    max_x: float = -1
    max_y: float = -1

    for key in keys:
        if (key.x + key.width) > max_x:
            max_x = key.x + key.width
        if (key.y + key.height) > max_y:
            max_y = key.y + key.height

    return max_x, max_y

# Gets the top left coordinate of bounding box of a cluster of keys
def min_x_y(keys: List[Key]) -> Tuple[float, float]:
    min_x, min_y = max_x_y(keys)

    for key in keys:
        if key.x < min_x:
            min_x = key.x
        if key.y < min_y:
            min_y = key.y

    return min_x, min_y

def read_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(path: str, content:str):
    with open(path, 'w', encoding='utf-8') as file:
        return file.write(content)

def gen_uid() -> str: # from vial-qmk/util/vial_generate_keyboard_uid.py
    return "#define VIAL_KEYBOARD_UID {{{}}}".format(
        ", ".join(["0x{:02X}".format(x) for x in secrets.token_bytes(8)])
    )

# Code for interpreting KiCAD netlist file
def make_tree(data:str):
    items = re.findall(r"\(|\)|(?<=\").*?(?=\")|(?<=\()\w+", data)

    def req(index):
        result = []
        item = items[index]
        while item != ")":
            if item == "(":
                subtree, index = req(index + 1)
                result.append(subtree)
            else:
                result.append(item)
            index += 1
            item = items[index]
        return result, index

    return req(1)[0]

def extract_matrix_pins(netlist: str,
                        mcu: str = "RP2040",
                        output_pin_prefix: str = "GP",
                        schem_pin_prefix: str = "GPIO"
                        ) -> Dict[str, List[str | int]]:
    """Takes a KiCAD netlist file as a string (`netlist`) and spits out a dict with column and row pins in order.
    `mcu` is used to search for the MCU component, based on component values.
    `output_pin_prefix` is what the output pins should start with (e.g. `"GP"` for RP2040, and empty (`""`) for 32U4).
    `schem_pin_prefix` is what the pins on the MCU symbol should start with (e.g. `"GPIO"` for RP2040 symbol from Sleep-Lib,
    `"P"` for the KiCAD default 32u4 symbol)
    """
    tree = make_tree(netlist)
    matrix_pins = {'cols': [], 'rows': []}
    mcu_comp = '' # MCU Component
    mcu_ref = '' # Component reference e.g. U2

    for comp in tree[3]:
        for prop in comp:
            if mcu.lower().startswith("stm32"):
                testcase = "stm32f"
            else:
                testcase = mcu.lower()
            if prop[0] == "value" and prop[1].lower().startswith(testcase):
                mcu_comp = comp

    if not mcu_comp:
        raise Exception(f"{mcu} MCU not found in netlist!")

    for prop in mcu_comp:
        if prop[0] == "ref":
            mcu_ref = prop[1]

    if not mcu_ref:
        raise Exception(f"MCU Reference (eg. U2) not found in netlist!")

    for net in tree[6]:
        for prop in net:
            if prop[0] == "name" and prop[1].lower().startswith("col"):
                for subprop in net:
                    if subprop[0] == "node" and subprop[1][1] == mcu_ref:
                        # print(subprop[3][1])
                        # print(re.findall(r"(?<="+"P"+r")\w+", subprop[3][1])[0])
                        pin = '%s%s' % (output_pin_prefix, re.findall(r"(?<="+schem_pin_prefix+r")\d+", subprop[3][1])[0])
                        matrix_pins["cols"].append(pin)
            elif prop[0] == "name" and prop[1].lower().startswith("row"):
                for subprop in net:
                    if subprop[0] == "node" and subprop[1][1] == mcu_ref:
                        pin = '%s%s' % (output_pin_prefix, re.findall(r"(?<="+schem_pin_prefix+r")\d+", subprop[3][1])[0])
                        matrix_pins["rows"].append(pin)

    return matrix_pins
