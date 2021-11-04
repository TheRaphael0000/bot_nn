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
        return int(dx + dy)


def name_to_region(display_name):
    m = re.findall("(\d+)[^\d](\d+)", display_name)
    if len(m) < 1:
        return False
    x, y = m[0]
    x, y = max(0, int(x)), max(0, int(y))
    return Region(x, y, display_name)
