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