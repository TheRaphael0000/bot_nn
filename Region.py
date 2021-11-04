#!/usr/bin/env python

import re

REG = re.compile(r"[(\[\{]?(\d{1,3})[^\d](\d{1,3})(?!\d)[)\]\}]?")


class Region:
    def __init__(self, display_name):
        x_str, y_str, x_int, y_int, name = name_to_region(display_name)
        self.__x_str = x_str
        self.__y_str = y_str
        self.__x_int = x_int
        self.__y_int = y_int
        self.__name = name

    def is_empty(self):
        return self.__x_int is None or self.__y_int is None

    def get_coords_int(self):
        return self.__x_int, self.__y_int

    def get_coords_str(self):
        return f"[{self.__x_str}:{self.__y_str}]"

    def get_name(self):
        return self.__name

    def get_distance(self, other):
        if self.is_empty() or other.is_empty():
            return -1

        sx, sy = self.get_coords_int()
        ox, oy = other.get_coords_int()
        dx = abs(sx - ox)
        dy = abs(sy - oy)
        return dx + dy


def name_to_region(display_name):
    x_str, y_str, x_int, y_int, name = None, None, None, None, None

    coords = REG.findall(display_name)
    # if there is only one match
    if len(coords) == 1:
        x_str, y_str = coords[0]
        x_int, y_int = int(x_str), int(y_str)
        # add as many zeros as needed
        x_str, y_str = "00" + x_str, "00" + y_str
        x_str, y_str = x_str[-3:], y_str[-3:]
        # remove the coordinates from the pseudo
        name = REG.sub(" ", display_name).strip()

    return x_str, y_str, x_int, y_int, name
