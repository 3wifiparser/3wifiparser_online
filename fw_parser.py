from utils import json_lib as json
from utils import clear_html_symb
import logging

def parse_map(data):
    stdata = data.find("{\"error\":")
    if stdata == -1:
        logging.error("Didn't find \"{\"error\":\" in data")
        return {"ok": False, "rescan": True, "desc": "Didn't find data"}
    data = data[stdata:-2]
    try:
        data = json.loads(data)["data"]["features"]
    except Exception:
        logging.error("JSON parse exception")
        return {"ok": False, "rescan": True, "desc": "JSON parse error."}
    nets = []
    if len(data) == 0:
        return {"ok": True, "result": nets}
    for point in data:
        if point["type"] != "Feature" and point["type"] != "Cluster":
            continue
        properties = point.get("properties")
        if properties == None:
            continue
        hintContent = properties.get("hintContent")
        if hintContent == None:
            continue
        if len(hintContent) == 0:
            continue
        hintContent = hintContent.split("<hr>")
        coords = point["geometry"]["coordinates"]
        for i in hintContent:
            data = i.split("<br>")[0:2]
            net = [
                clear_html_symb(data[1]),
                data[0],
                coords[0],
                coords[1]
            ]
            nets.append(net)
    return {"ok": True, "result": nets}