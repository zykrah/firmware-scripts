from functools import cmp_to_key
from dataclasses import dataclass, field as dcf
from typing import Optional, List, Callable
import secrets

UB_LABEL_MAP = 12

@dataclass
class _inner_Key_default:
    textColor: str = "#000000"
    textSize: int = 3

def _default_factory_list_factory(s: int) -> Callable:
    def list_factory() -> List:
        return [None, ] * s
    return list_factory

def _dcf_list() -> List:
    return dcf(default_factory=list)

@dataclass
class Key:
    color: str = "#cccccc"
    labels: List[str] = _dcf_list()
    textColor: List[Optional[str]] = dcf(default_factory=_default_factory_list_factory(UB_LABEL_MAP))
    textSize: List[Optional[int]] = dcf(default_factory=_default_factory_list_factory(UB_LABEL_MAP))
    default: _inner_Key_default = _inner_Key_default()
    x: float = 0.
    y: float = 0.
    width: float = 1.
    height: float = 1.
    x2: float = 0.
    y2: float = 0.
    width2: float = 1.
    height2: float = 1.
    rotation_x: float = 0.
    rotation_y: float = 0.
    rotation_angle: float = 0.
    decal: bool = False
    ghost: bool = False
    stepped: bool = False
    nub: bool = False
    profile: str = ""
    sm: str = ""  # switch mount
    sb: str = ""  # switch brand
    st: str = ""  # switch type

@dataclass
class _inner_KeyboardMetadata_background:
    name: str
    style: str

@dataclass
class KeyboardMetadata:
    author: str = ""
    backcolor: str = "#eeeeee"
    background: Optional[_inner_KeyboardMetadata_background] = None
    name: str = ""
    notes: str = ""
    radii: str = ""
    switchBrand: str = ""
    switchMount: str = ""
    switchType: str = ""

@dataclass
class Keyboard:
    meta: KeyboardMetadata = KeyboardMetadata()
    keys: List[Key] = _dcf_list()


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

def sort_keys(keys:list):
    def func(a, b):
        return ((a.rotation_angle+360)%360 - (a.rotation_angle+360)%360 or 
        (a.rotation_x - b.rotation_x) or
        (a.rotation_y - b.rotation_y) or
        (a.y - b.y) or
        (a.x - b.x))

    keys.sort(key=cmp_to_key(func))

def replace_chars(str:str, start:int, stop:int, new):
    """Replace characters in a string based on the start and stop character indices.
    """
    return str.replace(str[start:stop], new)

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
