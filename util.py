from functools import cmp_to_key
from dataclasses import dataclass, field as dcf
from typing import Optional, List, Callable
import secrets

# Unused currently
def replace_chars(str:str, start:int, stop:int, new):
    """Replace characters in a string based on the start and stop character indices.
    """
    return str.replace(str[start:stop], new)

# Gets the bottom right coordinate of bounding box of a cluster of keys
def max_x_y(keys: list) -> float:
    max_x: float = -1
    max_y: float = -1

    for key in keys:
        if (key.x + key.width) > max_x:
            max_x = key.x + key.width
        if (key.y + key.height) > max_y:
            max_y = key.y + key.height

    return max_x, max_y

# Gets the top left coordinate of bounding box of a cluster of keys
def min_x_y(keys: list) -> float:
    min_x, min_y = max_x_y(keys)

    for key in keys:
        if key.x < min_x:
            min_x = key.x
        if key.y < min_y:
            min_y = key.y

    return min_x, min_y

def read_file(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(path: str, content:str):
    with open(path, 'w', encoding='utf-8') as file:
        return file.write(content)

def gen_uid(): # from vial-qmk/util/vial_generate_keyboard_uid.py
    return "#define VIAL_KEYBOARD_UID {{{}}}".format(
        ", ".join(["0x{:02X}".format(x) for x in secrets.token_bytes(8)])
    )
