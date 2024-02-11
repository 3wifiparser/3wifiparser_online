
import json

def parse_map(data):
    stdata = data.find("{\"error\":")
    if stdata == -1:
        with open("log.txt", "w", encoding="utf-8") as f:
            f.write("Didn't find \"{\"error\":\" in data\ndata:\n" + data)
        return {"ok": False, "rescan": True, "desc": "Didn't find data. (read log.txt)"}
    data = data[stdata:-2]
    try:
        data = json.loads(data)["data"]["features"]
    except Exception as e:
        with open("log.txt", "w", encoding="utf-8") as f:
            f.write("JSON parse error\ndata:\n" + data)
        return {"ok": False, "rescan": True, "desc": "JSON parse error. (read log.txt)"}
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
                data[1].replace("&nbsp;", " ").replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<"),
                data[0],
                coords[0],
                coords[1]
            ]
            nets.append(net)
    return {"ok": True, "result": nets}