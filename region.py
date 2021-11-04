#!/usr/bin/env python

import re


class Region:
    def __init__(self, x, y, name):
        self.__x = x
        self.__y = y
        self.__name = name

    def is_empty(self):
        return self.__x is None or self.__y is None

    def get_coords(self):
        return self.__x, self.__y

    def get_name(self):
        return self.__name

    def get_distance(self, other):
        if self.is_empty() or other.is_empty():
            return float("inf")

        sx, sy = self.get_coords()
        ox, oy = other.get_coords()
        dx = abs(sx - ox)
        dy = abs(sy - oy)
        return float(dx + dy)


def name_to_region(display_name):
    coords = re.findall(r"(\d+)[^\d](\d+)(.*)", display_name)
    x, y, name = None, None, None
    if len(coords) > 0:
        _x, _y, _name = coords[0]
        _x, _y = int(x), int(y)
        if _x > -1 and _y > -1:
            _x, _y = "00" + str(_x), "00" + str(_y)
            _x, _y = _x[-3:], _y[-3:]
            _name = _name.strip()
            x, y, name = _x, _y, _name
    return Region(x, y, name)
