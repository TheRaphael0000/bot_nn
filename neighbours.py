#!/usr/bin/env python

from region import name_to_region

MAX_CHARS = 1300

MSG_NO_COORDS = "Écris ta région dans ton pseudo. Exemple : _[018:006] TheRaphael0000_"
MSG_NO_NEIGHBOUR = "Tu n'as pas encore de voisins sur ce serveur .-."
MSG_SUCCESS = "Position,Distance,Pseudo"


def execute(mutex, all_regions, display_name, args):
    answer = []

    my_region = name_to_region(display_name)
    if not my_region:
        return [MSG_NO_COORDS]

    neighbours = []
    mutex.acquire()
    for region in all_regions:
        distance = my_region.get_distance(region)
        if 0 < distance:
            neighbours.append((region, distance))
    mutex.release()

    neighbours.sort(key=lambda n: n[-1])
    if len(neighbours) <= 0:
        return [MSG_NO_NEIGHBOUR]

    answer = ["```", MSG_SUCCESS]
    for (region, distance) in neighbours:
        x, y = region.get_coords()
        name = region.get_name()
        s = f"[{x}:{y}],{distance},{name}"
        if len("\n".join(answer)) + len(s) > MAX_CHARS - 3: # the last 3 ```
            break
        answer.append(s)

    return [*answer, "```"]
