#!/usr/bin/env python

from tabulate import tabulate

from Command import Command
from Region import Region

DEFAULT_DISTANCE = 10

DESCRIPTION = f"""
* /voisins     : obtenir la liste de vos voisins à moins de {DEFAULT_DISTANCE} cases
* /voisins [X] : obtenir la liste de vos voisins à moins de X case (X <= 100)
"""

MSG_NO_COORDS = [
    "Écris ta région dans ton pseudo.",
    "Convention : [XXX:YYY] Pseudo"
]
MSG_NO_NEIGHBOUR = "Tu n'as pas encore de voisins sur ce serveur .-."
MSG_HEADER = ["Position", "Distance", "Pseudo"]


def execute_fn(mutex, all_regions, display_name, args):
    answer = []

    max_distance = DEFAULT_DISTANCE
    if len(args) > 0:
        try:
            distance = int(args[0])
            if distance > 0:
                max_distance = min(distance, 100)
        except ValueError:
            pass

    my_region = Region(display_name)
    if my_region.is_empty():
        answer = MSG_NO_COORDS
    else:
        neighbours = []
        mutex.acquire()
        for region in all_regions:
            distance = my_region.get_distance(region)
            if 0 < distance <= max_distance:
                neighbours.append((region, distance))
        mutex.release()

        neighbours = sorted(neighbours, key=lambda n: n[-1])
        answer = MSG_NO_NEIGHBOUR

        if len(neighbours) > 0:
            rows = []
            for (region, distance) in neighbours:
                coords = region.get_coords_str()
                name = region.get_name()
                rows.append([coords, distance, name])
        answer = tabulate(rows, MSG_HEADER, colalign=(
            "center", "center", "left"))

    return answer


Neighbours = Command(DESCRIPTION, execute_fn)
