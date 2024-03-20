import math
from utils import Task
from random import getrandbits
from sys import argv
from database import get_task

def from_geo_to_pixels(lat, long, projection, z):
    rho = math.pow(2, z + 8) / 2
    beta = lat * math.pi / 180
    phi = (1 - projection * math.sin(beta)) / (1 + projection * math.sin(beta))
    theta = math.tan(math.pi / 4 + beta / 2) * math.pow(phi, projection / 2)
    x_p = rho * (1 + long / 180)
    y_p = rho * (1 - math.log(theta) / math.pi)
    return [x_p // 256, y_p // 256]

def check_offline_argv():
    return ("-s" in argv) or ("--p1" in argv and "--p2" in argv)

def get_task_argv():
    if "-s" in argv:
        return get_task(argv[argv.index("-s") + 1])
    else:
        return None

def get_pos1_pos2():
    if "--p1" in argv and "--p2" in argv:
        pos1str = argv[argv.index("--p1") + 1]
        pos2str = argv[argv.index("--p2") + 1]
    else:
        pos1str = input("pos1: ")
        pos2str = input("pos2: ")
    border1 = pos1str.split(",")
    border1[0] = float(border1[0])
    border1[1] = float(border1[1])
    border2 = pos2str.split(",")
    border2[0] = float(border2[0])
    border2[1] = float(border2[1])
    return (border1, border2)

projection = 0.0818191908426
z = 17
max_area = 100

def pos2task(borders):
    border1, border2 = borders
    pixel_coords1 = from_geo_to_pixels(border1[0], border1[1], projection, z)
    pixel_coords2 = from_geo_to_pixels(border2[0], border2[1], projection, z)
    t = Task()
    t.server_id = 0
    t.local_id = getrandbits(32)
    t.min_maxTileX = [int(min(pixel_coords1[0], pixel_coords2[0])), int(max(pixel_coords1[0], pixel_coords2[0]))]
    t.min_maxTileY = [int(min(pixel_coords1[1], pixel_coords2[1])), int(max(pixel_coords1[1], pixel_coords2[1]))]
    t.max_area = max_area
    t.progress = [0, 67108864]
    return t
