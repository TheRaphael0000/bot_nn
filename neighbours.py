#!/usr/bin/env python

from region import name_to_region

DEFAULT_DISTANCE = 10

MSG_NO_COORDS = "Écris ta région dans ton pseudo. Exemple : _[018:006] TheRaphael0000_"
MSG_NO_NEIGHBOUR = "Tu n'as pas encore de voisins sur ce serveur .-."
MSG_SUCCESS = "Position\tDistance\tPseudo"


def execute(mutex, all_regions, display_name, args):
    answer = []

    max_distance = DEFAULT_DISTANCE
    if len(args) > 0:
        try:
            distance = int(args[0])
            if distance > 0:
                max_distance = min(distance, 100)
        except ValueError:
            pass

    my_region = name_to_region(display_name)
    if my_region.is_empty():
        answer = [MSG_NO_COORDS]
    else:
        neighbours = []
        mutex.acquire()
        for region in all_regions:
            distance = my_region.get_distance(region)
            if 0 < distance <= max_distance:
                neighbours.append((region, distance))
        mutex.release()

        neighbours = sorted(neighbours, key=lambda n: n[-1])
        answer = [MSG_NO_NEIGHBOUR]

        if len(neighbours) > 0:
            answer = [MSG_SUCCESS]
            for (region, distance) in neighbours:
                x, y = region.get_coords()
                name = region.get_name()
                answer.append(f"[{x}:{y}]\t{distance}\t{name}")

    return answer
