import logging
import config
import aiohttp.typedefs
import random
from string import ascii_letters
import struct
import os

no_dir = not(os.path.isdir("temptiles"))

if not(no_dir):
    for i in os.listdir("temptiles"):
        os.remove(f"temptiles/{i}")

class Task:
    server_id: int
    local_id: int
    min_maxTileX: list[int, int]
    min_maxTileY: list[int, int]
    max_area: int
    progress: list[int, int]
    tiles_cache_type = None
    cache_file = None
    iter_n: int = 0
    tiles = None
    ntiles = 0
    def __iter__(self):
        if self.tiles_cache_type is None:
            x_len = self.min_maxTileX[1] - self.min_maxTileX[0] + 1
            y_len = self.min_maxTileY[1] - self.min_maxTileY[0] + 1
            reqs = (x_len * y_len * 3) / self.max_area / 2 # approximate number of requests
            reqs = min(reqs, self.progress[1] - self.progress[0] + 1)
            self.tiles_cache_type = 1 if reqs > 50000 else 0
        if self.tiles_cache_type == 1 and self.cache_file is None: # tiles in file
            x_len = self.min_maxTileX[1] - self.min_maxTileX[0] + 1
            y_len = self.min_maxTileY[1] - self.min_maxTileY[0] + 1
            fname, nrects = partition_rectangle_tofile(self.min_maxTileX[0], self.min_maxTileY[0], x_len, y_len, self.max_area, self.progress[0], self.progress[1])
            self.ntiles = nrects
            self.cache_file = open(fname, "rb")
        if self.tiles_cache_type == 0: # tiles in ram
            self.tiles = self.get_tiles()
            self.ntiles = len(self.tiles)
        return self
    def __next__(self):
        if self.tiles_cache_type == 1:
            d = self.cache_file.read(16)
            if len(d) < 16:
                self.cache_file.close()
                raise StopIteration
            return struct.unpack("iiii", d)
        elif self.tiles_cache_type == 0:
            if len(self.tiles) <= self.iter_n:
                raise StopIteration
            d = self.tiles[self.iter_n]
            self.iter_n += 1
            return d
    def get_tiles(self):
        x_len = self.min_maxTileX[1] - self.min_maxTileX[0] + 1
        y_len = self.min_maxTileY[1] - self.min_maxTileY[0] + 1
        return partition_rectangle(self.min_maxTileX[0], self.min_maxTileY[0], x_len, y_len, self.max_area, self.progress[0], self.progress[1])[1:]

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

def partition_rectangle_tofile(x, y, width, height, max_area, start=0, end=67108864, nrects=None, wfile=None):
    fst = False
    if wfile is None:
        if no_dir:
            os.mkdir("temptiles")
        wfile = open("temptiles/temp_" + "".join(random.choices(ascii_letters, k=10)) + ".tiles", "wb")
        fst = True
    if nrects is None:
        nrects = [0]
    if width * height <= max_area:
        if nrects[0] >= start:
            wfile.write(struct.pack("iiii", x, y, x + width - 1, y + height - 1))
        nrects[0] += 1
        if nrects[0] >= end:
            if fst:
                fname = wfile.name
                wfile.close()
                return (fname, nrects[0]-start)
            else:
                return
    else:
        if width > height:
            half_width = width // 2
            partition_rectangle_tofile(x, y, half_width, height, max_area, start, end, nrects, wfile)
            if nrects[0] >= end:
                if fst:
                    fname = wfile.name
                    wfile.close()
                    return (fname, nrects[0]-start)
                else:
                    return
            partition_rectangle_tofile(x + half_width, y, width - half_width, height, max_area, start, end, nrects, wfile)
        else:
            half_height = height // 2
            partition_rectangle_tofile(x, y, width, half_height, max_area, start, end, nrects, wfile)
            if nrects[0] >= end:
                if fst:
                    fname = wfile.name
                    wfile.close()
                    return (fname, nrects[0]-start)
                else:
                    return
            partition_rectangle_tofile(x, y + half_height, width, height - half_height, max_area, start, end, nrects, wfile)
    if fst:
        fname = wfile.name
        wfile.close()
        return (fname, nrects[0]-start)

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
        raise BaseException("Wrong JSON library config")

def clear_html_symb(st):
    return st.replace("&nbsp;", " ").replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").replace("&quot;", "\"").replace("&#34;", "\"").replace("&#39;", "'").replace("&#160;", " ").replace("&apos;", "'").replace("&#38;", "&")