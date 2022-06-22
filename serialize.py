from dataclasses import dataclass
from typing import List
from copy import deepcopy

from util import Key, Keyboard, KeyboardMetadata, UB_LABEL_MAP, sort_keys

@dataclass
class SerializeCluster:
    r: float = 0.
    rx: float = 0.
    ry: float = 0.

class TempKey:
    def __init__(self, align:int):
        self.align = align
        self.labels: list = ["","","","","","","","","","","",""]
        self.textColor: list = ["","","","","","","","","","","",""]
        self.textSize: list = [None ] * UB_LABEL_MAP

class _ReorderLabels:
    def __init__(self):
        # Map from serialized label position to normalized position,
        # depending on the alignment flags.
        self.LABEL_MAP = [
            # 0  1  2  3  4  5  6  7  8  9 10 11      align flags
            [ 0, 6, 2, 8, 9,11, 3, 5, 1, 4, 7,10],  # 0 = no centering              # noqa
            [ 1, 7,-1,-1, 9,11, 4,-1,-1,-1,-1,10],  # 1 = center x                  # noqa
            [ 3,-1, 5,-1, 9,11,-1,-1, 4,-1,-1,10],  # 2 = center y                  # noqa
            [ 4,-1,-1,-1, 9,11,-1,-1,-1,-1,-1,10],  # 3 = center x & y              # noqa
            [ 0, 6, 2, 8,10,-1, 3, 5, 1, 4, 7,-1],  # 4 = center front (default)    # noqa
            [ 1, 7,-1,-1,10,-1, 4,-1,-1,-1,-1,-1],  # 5 = center front & x          # noqa
            [ 3,-1, 5,-1,10,-1,-1,-1, 4,-1,-1,-1],  # 6 = center front & y          # noqa
            [ 4,-1,-1,-1,10,-1,-1,-1,-1,-1,-1,-1],  # 7 = center front & x & y      # noqa
        ]
        self.DISALLOWED_ALIGNMENT_FOR_LABELS = [
            [1,2,3,5,6,7],	#0
            [2,3,6,7],		#1
            [1,2,3,5,6,7],	#2
            [1,3,5,7],		#3
            [],				#4
            [1,3,5,7],		#5
            [1,2,3,5,6,7],	#6
            [2,3,6,7],		#7
            [1,2,3,5,6,7],	#8
            [4,5,6,7],		#9
            [],				#10
            [4,5,6,7]		#11
        ]


    def __call__(self, key: Key, current: Key):
        # Possible alignment flags in order of preference (this is fairly
		# arbitrary, but hoped to reduce raw data size).
        align = [7,5,6,4,3,1,2,0]

        for i in range(0, len(key.labels)):
            if key.labels[i]:
                for _ in self.DISALLOWED_ALIGNMENT_FOR_LABELS[i]:
                    if _ in align:
                        align.remove(_)

        ret = TempKey(align[0])

        for i in range(0, UB_LABEL_MAP):
            if i in self.LABEL_MAP[ret.align]:
                ndx = (self.LABEL_MAP[ret.align]).index(i)
            else:
                ndx = -1
            if ndx >= 0:
                if key.labels[i]:
                    ret.labels[ndx] = key.labels[i]
                if key.textColor[i]:
                    ret.textColor[ndx] = key.textColor[i]
                if key.textSize[i]:
                    ret.textSize[ndx] = key.textSize[i]

        for i in range(0, len(ret.textSize)):
            if not ret.labels[i]:
                ret.textSize[i] = current.textSize
            if not ret.textSize[i] or ret.textSize[i] == key.default.textSize:
                ret.textSize[i] = 0

        return ret

reorder_labels = _ReorderLabels()

def compare_text_sizes(current, key, labels):
    if isinstance(current, int):
        current = [current]
    for i in range(0, UB_LABEL_MAP):
        if labels[i] and (bool(current[i]) != bool(key[i]) or (current[i] and current[i] != key[i])):
            return False
    return True

def is_empty_object(o):
    for prop in o:
        return False
    return True

def serialize_prop(props, nname, val, defval):
    if val != defval:
        props[nname] = val
    return val

def serialize(kbd: Keyboard) -> list:
    keys = kbd.keys
    rows: List(list) = []
    row: List(Key) = []
    current = deepcopy(Key())
    current.textColor = current.default.textColor
    current.align = 4
    cluster = SerializeCluster()

    meta: dict = {}
    for property in vars(kbd.meta).keys():
        if getattr(kbd.meta, property) != vars(KeyboardMetadata)[property]:
            meta[property] = getattr(kbd.meta, property)
    if meta:
        rows.append(meta)

    new_row = True
    current.y -= 1 # will be incremented on first row

    sort_keys(keys)
    for key in kbd.keys:
        props: dict = {}
        ordered: TempKey = reorder_labels(key, current)

        cluster_changed = key.rotation_angle != cluster.r or key.rotation_x != cluster.rx or key.rotation_y != cluster.ry
        row_changed = key.y != current.y
        if len(row) > 0 and (cluster_changed or row_changed):
            rows.append(row)
            row: List(Key) = []
            new_row = True

        if new_row:
            current.y += 1

            if key.rotation_y != cluster.ry or key.rotation_x != cluster.rx:
                current.y = key.rotation_y
            current.x = key.rotation_x # always reset x to rx (defaults to 0)

            cluster.r = key.rotation_angle
            cluster.rx = key.rotation_x
            cluster.ry = key.rotation_y

            new_row = False

        current.rotation_angle = serialize_prop(props, "r", key.rotation_angle, current.rotation_angle)
        current.rotation_x = serialize_prop(props, "rx", key.rotation_x, current.rotation_x)
        current.rotation_y = serialize_prop(props, "ry", key.rotation_y, current.rotation_y)
        current.y += serialize_prop(props, "y", key.y-current.y, 0.)
        current.x += serialize_prop(props, "x", key.x-current.x, 0.) + key.width
        current.color = serialize_prop(props, "c", key.color, current.color)
        if not ordered.textColor[0]:
            ordered.textColor[0] = key.default.textColor
        else:
            for i in range(2, UB_LABEL_MAP):
                if not ordered.textColor[i] and ordered.textColor[i] != ordered.textColor[0]:
                    ordered.textColor[i] != key.default.textColor
        current.textColor = serialize_prop(props, "t", "\n".join(ordered.textColor).rstrip(), current.textColor)
        current.ghost = serialize_prop(props, "g", key.ghost, current.ghost)
        current.profile = serialize_prop(props, "p", key.profile, current.profile)
        current.sm = serialize_prop(props, "sm", key.sm, current.sm)
        current.sb = serialize_prop(props, "sb", key.sb, current.sb)
        current.st = serialize_prop(props, "st", key.st, current.st)
        current.align = serialize_prop(props, "a", ordered.align, current.align)
        current.default.textSize = serialize_prop(props, "f", key.default.textSize, current.default.textSize)

        if props.get('f'):
            current.textSize = [None] * UB_LABEL_MAP

        if not compare_text_sizes(current.textSize, ordered.textSize, ordered.labels):
            if len(ordered.textSize) == 0:
                serialize_prop(props, "f", key.default.textSize, -1)
            else:
                optimizeF2 = not ordered.textSize[0]
                for i in range(2, len(ordered.textSize) and optimizeF2):
                    optimizeF2 = ordered.textSize[i] == ordered.textSize[1]
                if optimizeF2:
                    f2 = ordered.textSize[1]
                    current.f2 = serialize_prop(props, "f2", f2, -1)
                    current.textSize = [0,f2,f2,f2,f2,f2,f2,f2,f2,f2,f2,f2]
                else:
                    current.f2 = None
                    current.textSize = serialize_prop(props, "fa", ordered.textSize, [])

        serialize_prop(props, "w", key.width, 1.)
        serialize_prop(props, "h", key.height, 1.)
        serialize_prop(props, "w2", key.width2, key.width)
        serialize_prop(props, "h2", key.height2, key.height)
        serialize_prop(props, "x2", key.x2, 0.)
        serialize_prop(props, "y2", key.y2, 0.)
        serialize_prop(props, "n", key.nub or False, False)
        serialize_prop(props, "l", key.stepped or False, False)
        serialize_prop(props, "d", key.decal or False, False)
        if not is_empty_object(props):
            row.append(props)
        current.labels = ordered.labels
        row.append('\n'.join(ordered.labels).rstrip())
    if len(row) > 0:
        rows.append(row)    
    return rows
