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
        return partition_rectangle(self.min_maxTileX[0], self.min_maxTileY[0], x_len, y_len, self.max_area)[self.progress[0]:self.progress[1]]

def partition_rectangle(x, y, width, height, max_area, rects=None):
    if rects is None:
        rects = []
    if width * height <= max_area:
        rects.append((x, y, x + width, y + height))
    else:
        if width > height:
            half_width = width // 2
            partition_rectangle(x, y, half_width, height, max_area, rects)
            partition_rectangle(x + half_width, y, width - half_width, height, max_area, rects)
        else:
            half_height = height // 2
            partition_rectangle(x, y, width, half_height, max_area, rects)
            partition_rectangle(x, y + half_height, width, height - half_height, max_area, rects)
    return rects