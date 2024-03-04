import logging
import config
import aiohttp.typedefs

class Task:
    server_id: int
    local_id: int
    min_maxTileX: list[int, int]
    min_maxTileY: list[int, int]
    max_area: int
    progress: list[int, int]
    def get_tiles(self):
        x_len = self.min_maxTileX[1] - self.min_maxTileX[0] + 1
        y_len = self.min_maxTileY[1] - self.min_maxTileY[0] + 1
        return partition_rectangle(self.min_maxTileX[0], self.min_maxTileY[0], x_len, y_len, self.max_area, self.progress[0], self.progress[1])[1:]
    def get_tiles_cnt(self):
        x_len = self.min_maxTileX[1] - self.min_maxTileX[0] + 1
        y_len = self.min_maxTileY[1] - self.min_maxTileY[0] + 1
        return partition_rectangle_cnt(self.min_maxTileX[0], self.min_maxTileY[0], x_len, y_len, self.max_area)

def partition_rectangle(x, y, width, height, max_area, start=0, end=67108864, rects=None):
    #rects[0] is counter
    if rects is None:
        rects = [0]
    if width * height <= max_area:
        if rects[0] >= start:
            rects.append((x, y, x + width - 1, y + height - 1))
        rects[0] += 1
        if rects[0] >= end:
            return rects
    else:
        if width > height:
            half_width = width // 2
            partition_rectangle(x, y, half_width, height, max_area, start, end, rects=rects)
            if rects[0] >= end:
                return rects
            partition_rectangle(x + half_width, y, width - half_width, height, max_area, start, end, rects=rects)
        else:
            half_height = height // 2
            partition_rectangle(x, y, width, half_height, max_area, start, end, rects=rects)
            if rects[0] >= end:
                return rects
            partition_rectangle(x, y + half_height, width, height - half_height, max_area, start, end, rects=rects)
    return rects

def partition_rectangle_cnt(x, y, width, height, max_area):
    number = 0
    if width * height <= max_area:
        number += 1
    else:
        if width > height:
            half_width = width // 2
            number += partition_rectangle_cnt(x, y, half_width, height, max_area)
            number += partition_rectangle_cnt(x + half_width, y, width - half_width, height, max_area)
        else:
            half_height = height // 2
            number += partition_rectangle_cnt(x, y, width, half_height, max_area)
            number += partition_rectangle_cnt(x, y + half_height, width, height - half_height, max_area)
    return number

class TqdmLoggingHandler(logging.Handler):
    pgb = None
    formatter = None
    level = logging.INFO
    def __init__(self, _pgb):
        self.pgb = _pgb
    def handle(self, record):
        try:
            msg = self.format(record)
            self.pgb.write(msg)
        except RecursionError:
            raise
        except Exception:
            pass

def set_tqdm_log(_pgb):
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=[TqdmLoggingHandler(_pgb)], format="")

def set_log():
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()], format="")

import enum
class jsonlib(enum.Enum):
    standart = 1
    ujson = 2
    orjson = 3

json_lib = None
def init_json_lib():
    global json_lib
    if config.json_lib == "ujson":
        import ujson
        json_lib = ujson
        aiohttp.typedefs.DEFAULT_JSON_DECODER = json_lib.loads
        aiohttp.typedefs.DEFAULT_JSON_ENCODER = json_lib.dumps
    elif config.json_lib == "orjson":
        import orjson
        json_lib = orjson
        aiohttp.typedefs.DEFAULT_JSON_DECODER = json_lib.loads
        aiohttp.typedefs.DEFAULT_JSON_ENCODER = json_lib.dumps
    elif config.json_lib == "standart":
        import json
        json_lib = json
    else:
        raise Exception("Wrong JSON library config")